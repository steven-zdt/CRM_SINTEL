"""
ViewSets para la app accounts (API-First + Service Layer).

WARNING: IMPORTANTE:
- Los usuarios son globales (SHARED_APPS)
- Solo administradores pueden gestionar usuarios (IsAdminUser)
- Service Layer: Toda la lógica de negocio está en services/user_service.py
- Sin signals: Cero signals, toda la lógica en servicios
- Autenticación: SessionAuthentication para permitir cookies de sesión desde la UI

Referencia: https://www.django-rest-framework.org/api-guide/viewsets/
"""

import logging

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.public.accounts.api.filters import UserFilter
from apps.public.accounts.api.serializers import (
    UserCreateSerializer,
    UserListSerializer,
    UserUpdateSerializer,
)
from apps.public.accounts.api.services.user_service import (
    create_user_service,
    update_user_service,
)
from apps.public.accounts.services.delete_user_service import delete_user_service

User = get_user_model()


class UserAdminViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    CRUD admin de usuarios globales (public).

    WARNING: API-FIRST:
    - Solo staff (IsAdminUser)
    - Service Layer: Delega a user_service para crear/actualizar
    - Serializers separados: List/Create/Update
    - Autenticación: SessionAuthentication (cookies de sesión desde UI)

    Endpoints:
    - GET    /api/admin/v1/accounts/users/ (lista paginada)
    - POST   /api/admin/v1/accounts/users/ (crear)
    - GET    /api/admin/v1/accounts/users/{id}/ (detalle)
    - PATCH  /api/admin/v1/accounts/users/{id}/ (actualizar parcial)
    - DELETE /api/admin/v1/accounts/users/{id}/ (eliminar)
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.only(
        "id", "email", "first_name", "last_name", "is_active", "is_staff", "date_joined", "telefono"
    ).order_by("-date_joined")
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["id", "email", "date_joined"]
    ordering = ["-date_joined"]

    def get_serializer_class(self):
        """Retorna el serializer apropiado según la acción."""
        if self.action == "create":
            return UserCreateSerializer
        if self.action in {"update", "partial_update"}:
            return UserUpdateSerializer
        return UserListSerializer

    def create(self, request, *args, **kwargs):
        """
        Crea un nuevo usuario usando el Service Layer.

        WARNING: SEGURIDAD:
        - password y password2 son write_only, nunca se expone en la respuesta
        - Solo email+password; el resto lo completará el usuario más adelante
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Remover password2 antes de pasar al servicio (no se necesita)
        validated_data = serializer.validated_data.copy()
        validated_data.pop("password2", None)

        try:
            user = create_user_service(**validated_data)
            return Response(UserListSerializer(user).data, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        """
        Actualiza un usuario existente usando el Service Layer.

        WARNING: SEGURIDAD: password es write_only y opcional.
        """
        user = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            user = update_user_service(user=user, **serializer.validated_data)
            return Response(UserListSerializer(user).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get", "put", "patch"], url_path="me")
    def me(self, request):
        """
        Endpoint para obtener/actualizar el perfil del usuario autenticado.

        Endpoints:
        - GET /api/admin/v1/accounts/users/me/ - Obtener perfil
        - PUT /api/admin/v1/accounts/users/me/ - Actualizar perfil completo
        - PATCH /api/admin/v1/accounts/users/me/ - Actualizar perfil parcial
        """
        user = request.user
        if request.method == "GET":
            serializer = UserListSerializer(user)
            return Response(serializer.data)
        elif request.method in ["PUT", "PATCH"]:
            serializer = UserUpdateSerializer(data=request.data, partial=request.method == "PATCH")
            serializer.is_valid(raise_exception=True)
            try:
                user = update_user_service(user=user, **serializer.validated_data)
                return Response(UserListSerializer(user).data)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """
        Elimina un usuario. Usa el `delete_user_service` para limpieza en cascada
        en tablas públicas y perfiles tenant. Como fallback intenta el borrado ORM.
        """
        user = self.get_object()
        logger = logging.getLogger(__name__)
        logger.info("UserAdminViewSet.destroy: requested delete user_id=%s by=%s", user.pk, getattr(request.user, 'pk', None))
        try:
            delete_user_service(user.pk, cascade=True, deleted_by_id=request.user.pk)
            logger.info("UserAdminViewSet.destroy: delete_user_service completed for user_id=%s", user.pk)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception:
            logger.exception("UserAdminViewSet.destroy: delete_user_service failed for user_id=%s, falling back to super().destroy", user.pk)
            try:
                return super().destroy(request, *args, **kwargs)
            except Exception:
                logger.exception("UserAdminViewSet.destroy: fallback ORM destroy also failed for user_id=%s", user.pk)
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Lista de ViewSets para registro automático en el router
VIEWSETS = [
    (r"users", UserAdminViewSet, "admin-user"),
]
