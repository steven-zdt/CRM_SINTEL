import logging

from django.contrib.auth import get_user_model
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

logger = logging.getLogger(__name__)


class PublicUserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Public-facing User endpoints.

    - POST /api/public/v1/users/ -> AllowAny (create)
    - GET/PUT/PATCH/DELETE -> Admin-only (IsAdminUser) except `me` which requires authentication
    """

    authentication_classes = [SessionAuthentication]
    queryset = User.objects.only(
        "id", "email", "username", "first_name", "last_name", "is_active", "date_joined"
    ).order_by("-date_joined")
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["id", "email", "date_joined"]
    ordering = ["-date_joined"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in {"update", "partial_update"}:
            return UserUpdateSerializer
        return UserListSerializer

    def get_permissions(self):
        # Create is public, me requires authentication, management actions require admin
        if self.action == "create":
            return [permissions.AllowAny()]
        if self.action in {"me"}:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    def create(self, request, *args, **kwargs):
        data = request.data.copy() if hasattr(request, 'data') else {}
        # Allow clients to omit password2 by mirroring password when absent
        if 'password' in data and 'password2' not in data:
            data['password2'] = data.get('password')
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data.copy()
        validated_data.pop("password2", None)
        try:
            user = create_user_service(**validated_data)
            return Response(UserListSerializer(user).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        try:
            user = update_user_service(user=user, **serializer.validated_data)
            return Response(UserListSerializer(user).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            user = update_user_service(user=user, **serializer.validated_data)
            return Response(UserListSerializer(user).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """
        Elimina un usuario. Usa `delete_user_service` para limpieza cross-schema
        (TenantProfile via signal) antes del borrado; si falla, intenta el
        borrado ORM directo como fallback (mismo patron que UserAdminViewSet).
        """
        user = self.get_object()
        logger.info("PublicUserViewSet.destroy: requested delete user_id=%s by=%s", user.pk, getattr(request.user, 'pk', None))
        try:
            delete_user_service(user.pk, cascade=True, deleted_by_id=request.user.pk)
            logger.info("PublicUserViewSet.destroy: delete_user_service completed for user_id=%s", user.pk)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception:
            logger.exception("PublicUserViewSet.destroy: delete_user_service failed for user_id=%s, falling back to super().destroy", user.pk)
            try:
                return super().destroy(request, *args, **kwargs)
            except Exception:
                logger.exception("PublicUserViewSet.destroy: fallback ORM destroy also failed for user_id=%s", user.pk)
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get", "put", "patch"], url_path="me")
    def me(self, request):
        user = request.user
        if request.method == "GET":
            serializer = UserListSerializer(user)
            return Response(serializer.data)
        serializer = UserUpdateSerializer(data=request.data, partial=(request.method == "PATCH"))
        serializer.is_valid(raise_exception=True)
        try:
            user = update_user_service(user=user, **serializer.validated_data)
            return Response(UserListSerializer(user).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
