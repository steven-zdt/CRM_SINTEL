"""ViewSets para la app de perfil.

Implementacion simplificada: el ViewSet es un enrutador puro que delega
completamente en PerfilServiceMixin (Service Layer). Expone:
- GET  /api/v1/perfil/perfiles/                              -> list
- POST /api/v1/perfil/perfiles/                              -> create (ADMIN)
- GET  /api/v1/perfil/perfiles/me/                           -> perfil del usuario actual
- PATCH /api/v1/perfil/perfiles/me/                          -> actualizar perfil propio (OPERADOR+)
- PATCH /api/v1/perfil/perfiles/<id>/assign-rol/             -> asignar rol (ADMIN)
- GET  /api/v1/perfil/perfiles/render-offcanvas/crear/       -> offcanvas HTML (HTMX)

[RULE 15] Permisos por accion:
  - list / retrieve       : IsAuthenticated
  - create                : IsAuthenticated + IsTenantProfileAdmin
  - update (by admin)     : IsAuthenticated + IsTenantProfileAdmin
  - destroy               : IsAuthenticated + IsTenantProfileAdmin
  - me (GET/PATCH)        : IsAuthenticated (cualquier rol, propio perfil)
  - assign_rol            : IsAuthenticated + IsTenantProfileAdmin
"""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantAdminOrReadOnly, IsTenantMember
from apps.tenant.empresa.models import Area, Empresa, Sede
from apps.tenant.perfil.models import Departamento, RolTenant
from apps.tenant.perfil.services.business_service import PerfilBusinessService
from apps.tenant.perfil.services.selectors import DEPARTAMENTO_LIST_FIELDS
from .mixins import PerfilServiceMixin
from .permissions import IsTenantProfileAdmin, IsTenantProfileOperadorOrAdmin
from .serializers import (
    DepartamentoDetailSerializer,
    DepartamentoListSerializer,
    TenantProfileSerializer,
    TenantProfileRolSerializer,
)

logger = logging.getLogger(__name__)


class PerfilViewSet(PerfilServiceMixin, viewsets.GenericViewSet):
    """Router puro: delega la logica al Service Layer (PerfilServiceMixin)."""
    permission_classes = [IsTenantMember]
    serializer_class = TenantProfileSerializer
    pagination_class = StandardResultsSetPagination

    def list(self, request):
        """GET /api/v1/perfil/perfiles/ - Lista todos los perfiles del tenant.

        Retorna respuesta paginada compatible con TabulatorFactory:
        {count, next, previous, results: [...]}
        """
        # Django-tenants: request.tenant is the Client object, not the Empresa object.
        # We need to get the Empresa singleton from the current schema.
        empresa = Empresa.objects.only("id").first()
        if not empresa:
            return Response({
                "empresa": "No se encontraron datos de Empresa en el tenant actual.",
                "detail_code": "invalid"
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        queryset = self.perfil_service.list_profiles(empresa)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        """POST /api/v1/perfil/perfiles/ - Crea o invita a un usuario al tenant.

        [RULE 15] Requiere rol ADMIN en el tenant.
        Delega validacion, creacion de User y sync M2M a PerfilBusinessService.create_profile_for_user.
        """
        # [RULE 15] Guard: solo ADMIN puede crear perfiles
        if not IsTenantProfileAdmin().has_permission(request, self):
            raise PermissionDenied(
                "Se requiere rol ADMIN en este tenant para crear perfiles."
            )

        empresa = Empresa.objects.only("id").first()
        if not empresa:
            return Response({
                "error": "empresa_no_encontrada",
                "message": "No se encontraron datos de Empresa en el tenant actual."
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # [RULE 5.2] El ViewSet actua SOLO como enrutador: pasa el payload crudo al
        # business service que realiza validacion semantica completa (DSV + idempotencia).
        # No usar PerfilCreateSerializer aqui ya que los campos de User (email, first_name)
        # no pertenecen al modelo TenantProfile y son manejados internamente por el service.
        data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)

        # Normalizar listas M2M: pueden venir como lista JSON o como multiples valores form
        for field in ('sedes_uuids', 'areas_uuids'):
            raw = request.data.getlist(field) if hasattr(request.data, 'getlist') else data.get(field)
            if raw is not None:
                data[field] = raw if isinstance(raw, list) else [raw]

        try:
            profile = self.perfil_service.create_profile_for_user(
                empresa=empresa,
                data=data,
            )
            response_serializer = self.get_serializer(profile)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error("[perfil:create] Error creando colaborador: %s", str(e))
            error_msg = str(e)
            if isinstance(e, DjangoValidationError) and hasattr(e, 'messages'):
                error_msg = e.messages[0] if e.messages else str(e)
            return Response({
                "error": "error_creacion",
                "message": error_msg
            }, status=status.HTTP_400_BAD_REQUEST)



    @action(
        detail=False,
        methods=['get'],
        renderer_classes=[TemplateHTMLRenderer],
        url_path='render-offcanvas/crear'
    )
    def render_offcanvas_crear(self, request):
        """GET - Renderiza el offcanvas de creacion de perfil (HTMX).

        Inyecta la lista de empresas del tenant en el contexto para poblar
        el selector de empresa con datos reales (Zero Waste).
        """
        empresas = Empresa.objects.only(
            'id', 'razon_social', 'nit'
        ).order_by('razon_social')

        departamentos = (
            Departamento.objects.filter(activo=True)
            .order_by('nombre')
            .only('uuid', 'nombre', 'empresa_id')
        )

        # Zero Waste queries
        sedes = Sede.objects.only('uuid', 'nombre', 'empresa_id').order_by('nombre')
        areas = Area.objects.select_related('sede').only('uuid', 'nombre', 'sede__uuid', 'sede__nombre', 'empresa_id').order_by('nombre')

        context = {
            'empresas': empresas,
            'rol_choices': RolTenant.choices,
            'departamentos': departamentos,
            'sedes': sedes,
            'areas': areas,
        }
        return Response(
            context,
            template_name='tenant/perfil/offcanvas_crear_perfil.html'
        )

    def retrieve(self, request, pk=None):
        """GET /api/v1/perfil/perfiles/<id>/ - Detalles de un perfil."""
        empresa = Empresa.objects.only("id").first()
        if not empresa:
            return Response({"error": "No se encontraron datos de Empresa en el tenant actual."}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        try:
            profile = self.perfil_service.get_profile(pk, empresa)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, pk=None):
        """PUT /api/v1/perfil/perfiles/<id>/ - Actualiza un perfil."""
        return self._update_profile(request, pk, partial=False)

    def partial_update(self, request, pk=None):
        """PATCH /api/v1/perfil/perfiles/<id>/ - Actualiza parcialmente un perfil."""
        return self._update_profile(request, pk, partial=True)

    def _update_profile(self, request, pk, partial=False):
        # [SEG-2] Guard: solo ADMIN puede editar perfiles de otros usuarios
        if not IsTenantProfileAdmin().has_permission(request, self):
            raise PermissionDenied(
                "Se requiere rol ADMIN en este tenant para editar perfiles."
            )

        empresa = Empresa.objects.only("id").first()
        if not empresa:
            return Response({"error": "No se encontraron datos de Empresa en el tenant actual."}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        try:
            # Primero validamos payload con el serializer
            profile = self.perfil_service.get_profile(pk, empresa)
            serializer = self.get_serializer(profile, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            
            # Pasamos validated data a business layer
            updated = self.perfil_service.update_profile_by_id(pk, empresa, serializer.validated_data)
            result = self.get_serializer(updated)
            return Response(result.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """DELETE /api/v1/perfil/perfiles/<id>/ - Elimina un perfil.

        [RULE 15] Requiere rol ADMIN en el tenant.
        [SEG-5] Prohibe auto-eliminacion y eliminacion del admin primario.
        """
        # [RULE 15] Guard: solo ADMIN puede eliminar perfiles
        if not IsTenantProfileAdmin().has_permission(request, self):
            raise PermissionDenied(
                "Se requiere rol ADMIN en este tenant para eliminar perfiles."
            )

        empresa = Empresa.objects.only("id").first()
        if not empresa:
            return Response({"error": "No se encontraron datos de Empresa en el tenant actual."}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # [SEG-5] Resolver el perfil destino antes de borrarlo para aplicar guards
        try:
            target_profile = self.perfil_service.get_profile(pk, empresa)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        # Guard 1: prohibir auto-eliminacion (admin no puede borrarse a si mismo)
        if target_profile.user_id == request.user.id:
            return Response(
                {"error": "No puedes eliminar tu propio perfil de usuario."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Guard 2: prohibir eliminar al administrador primario del tenant
        if self.perfil_service._is_tenant_primary_admin(target_profile.user):
            return Response(
                {"error": "No se puede eliminar al administrador primario del tenant."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            self.perfil_service.delete_profile(pk, empresa)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=['get'],
        renderer_classes=[TemplateHTMLRenderer],
        url_path='render-offcanvas/editar'
    )
    def render_offcanvas_editar(self, request, pk=None):
        empresa = Empresa.objects.only("id", "razon_social", "nit").first()
        if not empresa:
            return Response({"error": "No empresa"}, status=400)

        try:
            departamentos = (
                Departamento.objects.filter(empresa=empresa, activo=True)
                .order_by('nombre')
                .only('uuid', 'nombre')
            )
            profile = self.perfil_service.get_profile(pk, empresa)
            requester_profile = getattr(request.user, 'tenant_profile', None)
            is_admin = bool(
                requester_profile and requester_profile.rol == RolTenant.ADMIN
            )

            # Zero Waste queries
            sedes = Sede.objects.filter(empresa=empresa).order_by('nombre').only('uuid', 'nombre')
            areas = Area.objects.filter(empresa=empresa).select_related('sede').order_by('nombre').only('uuid', 'nombre', 'sede__uuid', 'sede__nombre')

            assigned_sedes_uuids = [str(u) for u in profile.sedes_asignadas.values_list('uuid', flat=True)]
            assigned_areas_uuids = [str(u) for u in profile.areas_asignadas.values_list('uuid', flat=True)]

            context = {
                'profile': profile,
                'empresa': empresa,
                'is_admin': is_admin,
                'rol_choices': RolTenant.choices,
                'departamentos': departamentos,
                'sedes': sedes,
                'areas': areas,
                'assigned_sedes_uuids': assigned_sedes_uuids,
                'assigned_areas_uuids': assigned_areas_uuids,
            }
            return Response(context, template_name='tenant/perfil/offcanvas_editar_perfil.html')
        except Exception as e:
            return Response({"error": str(e)}, status=404)

    @action(
        detail=True,
        methods=['get'],
        renderer_classes=[TemplateHTMLRenderer],
        url_path='render-offcanvas/detalle'
    )
    def render_offcanvas_detalle(self, request, pk=None):
        empresa = Empresa.objects.only("id").first()
        try:
            profile = self.perfil_service.get_profile(pk, empresa)
            context = {'profile': profile}
            return Response(context, template_name='tenant/perfil/offcanvas_detalle_perfil.html')
        except Exception as e:
            return Response({"error": str(e)}, status=404)

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        """GET/PATCH /api/v1/perfil/perfiles/me/ - Perfil del usuario actual."""
        empresa = Empresa.objects.only("id").first()
        if not empresa:
            return Response({
                "empresa": "No se encontraron datos de Empresa en el tenant actual.",
                "detail_code": "invalid"
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        if request.method == 'GET':
            profile = self.perfil_service.get_or_initialize_profile(request.user, empresa)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)

        if request.method == 'PATCH':
            serializer = self.get_serializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            updated_profile = self.perfil_service.update_user_profile(
                request.user, empresa, serializer.validated_data
            )
            result_serializer = self.get_serializer(updated_profile)
            return Response(result_serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['patch'],
        url_path='assign-rol',
        url_name='assign-rol',
    )
    def assign_rol(self, request, pk=None):
        """PATCH /api/v1/perfil/perfiles/<id>/assign-rol/ - Asigna un rol al perfil.

        [RULE 15] Exclusivo para rol ADMIN del tenant activo.
        [RULE 13] DSV: el perfil debe pertenecer a la empresa del tenant actual.

        Body: { "rol": "ADMIN" | "OPERADOR" | "VISOR" }

        Returns: TenantProfile serializado con el nuevo rol y available_actions
        actualizados reflejando los permisos del solicitante (el ADMIN).
        """
        # [RULE 15] Guard
        if not IsTenantProfileAdmin().has_permission(request, self):
            raise PermissionDenied(
                "Se requiere rol ADMIN en este tenant para asignar roles."
            )

        # Validar payload via serializer dedicado
        rol_serializer = TenantProfileRolSerializer(data=request.data)
        rol_serializer.is_valid(raise_exception=True)
        new_rol = rol_serializer.validated_data['rol']

        # Resolver empresa del tenant activo
        empresa = Empresa.objects.only("id").first()
        if not empresa:
            return Response(
                {"error": "No se encontraron datos de Empresa en el tenant actual."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        try:
            updated_profile = self.perfil_service.assign_rol(
                profile_id=pk,
                empresa=empresa,
                new_rol=new_rol,
            )
        except Exception as exc:
            logger.error("[perfil:assign_rol] pk=%s error=%s", pk, str(exc))
            if isinstance(exc, DjangoValidationError) and hasattr(exc, 'messages'):
                detail = exc.messages[0] if exc.messages else str(exc)
            else:
                detail = str(exc)
            return Response({"error": detail}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(updated_profile)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DepartamentoViewSet(BaseTenantViewSet):
    """
    ViewSet para Departamento.
    """
    permission_classes = [IsTenantAdminOrReadOnly]
    queryset = Departamento.objects.none()

    def get_serializer_class(self):
        if self.action in ['retrieve', 'update', 'partial_update']:
            return DepartamentoDetailSerializer
        return DepartamentoListSerializer

    def get_queryset(self):
        empresa = Empresa.objects.only("id").first()
        if not empresa:
            return Departamento.objects.none()
        return Departamento.objects.filter(empresa=empresa).only(*DEPARTAMENTO_LIST_FIELDS)

    def perform_create(self, serializer):
        empresa = Empresa.objects.only("id").first()
        if not empresa:
            raise DjangoValidationError("No se encontró la empresa del tenant.")
        perfil_service = PerfilBusinessService()
        try:
            instance = perfil_service.create_departamento(empresa, serializer.validated_data)
            serializer.instance = instance
        except Exception as e:
            if isinstance(e, DjangoValidationError):
                raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)
            raise e

    def perform_update(self, serializer):
        empresa = Empresa.objects.only("id").first()
        if not empresa:
            raise DjangoValidationError("No se encontró la empresa del tenant.")
        perfil_service = PerfilBusinessService()
        try:
            instance = perfil_service.update_departamento(self.get_object().uuid, empresa, serializer.validated_data)
            serializer.instance = instance
        except Exception as e:
            if isinstance(e, DjangoValidationError):
                raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)
            raise e

    def perform_destroy(self, instance):
        empresa = Empresa.objects.only("id").first()
        if not empresa:
            raise DjangoValidationError("No se encontró la empresa del tenant.")
        perfil_service = PerfilBusinessService()
        try:
            perfil_service.delete_departamento(instance.uuid, empresa)
        except Exception as e:
            if isinstance(e, DjangoValidationError):
                raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)
            raise e
