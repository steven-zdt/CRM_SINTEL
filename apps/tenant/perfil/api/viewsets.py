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

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.permissions import IsTenantMember
from .mixins import PerfilServiceMixin
from .permissions import IsTenantProfileAdmin, IsTenantProfileOperadorOrAdmin
from .serializers import TenantProfileSerializer, TenantProfileRolSerializer

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
        from apps.tenant.empresa.models import Empresa
        
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
        """POST /api/v1/perfil/perfiles/ - Crea un usuario + perfil en el tenant.

        Si el email ya existe como User, vincula el perfil.
        Si no existe, crea el User (unusable password) y el perfil.

        [RULE 15] Requiere rol ADMIN en el tenant.
        Double Semantic Verification (anti-IDOR):
        Resuelve el Empresa desde el schema del tenant usando empresa_id del payload.
        """
        # [RULE 15] Guard: solo ADMIN puede crear perfiles
        if not IsTenantProfileAdmin().has_permission(request, self):
            raise PermissionDenied(
                "Se requiere rol ADMIN en este tenant para crear perfiles."
            )

        from apps.tenant.empresa.models import Empresa

        payload_empresa_id = request.data.get("empresa_id")
        if not payload_empresa_id:
            return Response({
                "error": "empresa_requerida",
                "message": "Debes seleccionar una empresa para el perfil.",
                "missing_fields": ["empresa_id"]
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            empresa_id_int = int(payload_empresa_id)
        except (ValueError, TypeError):
            return Response({
                "error": "empresa_id_invalido",
                "message": "El valor de empresa_id debe ser un entero valido.",
                "missing_fields": ["empresa_id"]
            }, status=status.HTTP_400_BAD_REQUEST)

        # DSV: buscar empresa en el schema actual. Si no existe = IDOR o dato invalido.
        try:
            empresa = Empresa.objects.only("id", "razon_social").get(pk=empresa_id_int)
        except Empresa.DoesNotExist:
            return Response({
                "error": "empresa_no_encontrada",
                "message": "La empresa seleccionada no existe en este tenant.",
                "missing_fields": ["empresa_id"]
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            profile = self.perfil_service.create_profile_for_user(
                empresa=empresa,
                data=request.data
            )
            serializer = self.get_serializer(profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            from django.core.exceptions import ValidationError
            logger.error("[perfil:create] Error creando perfil: %s", str(e))
            
            error_msg = str(e)
            if isinstance(e, ValidationError) and hasattr(e, 'messages'):
                error_msg = e.messages[0] if e.messages else str(e)
                
            missing = []
            if "email" in error_msg.lower() or "username" in error_msg.lower():
                missing.append("email")
            if "ya existe" in error_msg.lower() or "already" in error_msg.lower():
                return Response({
                    "error": "perfil_duplicado",
                    "message": error_msg,
                    "missing_fields": []
                }, status=status.HTTP_409_CONFLICT)
            return Response({
                "error": "error_creacion",
                "message": error_msg,
                "missing_fields": missing
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
        from apps.tenant.empresa.models import Empresa

        empresas = Empresa.objects.only(
            'id', 'razon_social', 'nit'
        ).order_by('razon_social')

        from apps.tenant.perfil.models import RolTenant
        context = {
            'empresas': empresas,
            'rol_choices': RolTenant.choices,
        }
        return Response(
            context,
            template_name='tenant/perfil/offcanvas_crear_perfil.html'
        )

    def retrieve(self, request, pk=None):
        """GET /api/v1/perfil/perfiles/<id>/ - Detalles de un perfil."""
        from apps.tenant.empresa.models import Empresa
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

        from apps.tenant.empresa.models import Empresa
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
        """
        # [RULE 15] Guard: solo ADMIN puede eliminar perfiles
        if not IsTenantProfileAdmin().has_permission(request, self):
            raise PermissionDenied(
                "Se requiere rol ADMIN en este tenant para eliminar perfiles."
            )

        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.only("id").first()
        if not empresa:
            return Response({"error": "No se encontraron datos de Empresa en el tenant actual."}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

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
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.only("id", "razon_social", "nit").first()
        if not empresa:
            return Response({"error": "No empresa"}, status=400)
            
        try:
            from apps.tenant.perfil.models import RolTenant
            profile = self.perfil_service.get_profile(pk, empresa)
            requester_profile = getattr(request.user, 'tenant_profile', None)
            is_admin = bool(
                requester_profile and requester_profile.rol == RolTenant.ADMIN
            )
            context = {
                'profile': profile,
                'empresa': empresa,
                'is_admin': is_admin,
                'rol_choices': RolTenant.choices,
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
        from apps.tenant.empresa.models import Empresa
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
        from apps.tenant.empresa.models import Empresa
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
        from apps.tenant.empresa.models import Empresa
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
            from django.core.exceptions import ValidationError as DjangoValidationError
            logger.error("[perfil:assign_rol] pk=%s error=%s", pk, str(exc))
            if isinstance(exc, DjangoValidationError) and hasattr(exc, 'messages'):
                detail = exc.messages[0] if exc.messages else str(exc)
            else:
                detail = str(exc)
            return Response({"error": detail}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(updated_profile)
        return Response(serializer.data, status=status.HTTP_200_OK)
