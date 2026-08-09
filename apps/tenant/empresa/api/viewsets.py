"""
ViewSets y vistas auxiliares para la app empresa.

# WARNING: v2.40: Configuración moderna con Tabulator Factory y lazy loading.

# WARNING: IMPORTANTE: 
- django-tenants maneja automáticamente el aislamiento por esquema
- NO es necesario filtrar manualmente por tenant_id
- Patrón Singleton: Solo una empresa por tenant
- JSON-first: JSONParser (principal) + FormParser (legacy)
- SessionAuthentication + CSRF para workspace
"""
import logging
from functools import cached_property

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from rest_framework import permissions, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import SAFE_METHODS
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.config.api.pagination import StandardResultsSetPagination
from apps.services.maildigester.connection_test import maildigester_test_connection
from apps.services.security.crypto import decrypt_password
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantAdmin, IsTenantAdminOrReadOnly, IsTenantMember
from apps.tenant.api.utils import resolve_tenant_empresa
from apps.tenant.core.services.organizational_context import OrganizationalContextMixin
from apps.tenant.empresa.api.serializers import (
    EmpresaDetailSerializer,
    EmpresaHeaderSerializer,
    EmpresaListSerializer,
    EmpresaUpsertSerializer,
    MailInboxConfigDetailSerializer,
    MailInboxConfigListSerializer,
    MailInboxConfigTestConnectionSerializer,
    SedeListSerializer,
    SedeDetailSerializer,
    SedeUpsertSerializer,
    AreaListSerializer,
    AreaDetailSerializer,
    AreaUpsertSerializer,
)
from apps.tenant.empresa.choices.regimen import get_regimen_choices
from apps.tenant.empresa.choices.responsabilidad_rut import get_responsabilidad_rut_choices
from apps.tenant.empresa.choices.segmento_dian import get_segmento_dian_choices
from apps.tenant.empresa.models import Area, Empresa, MailInboxConfig, Sede
from apps.tenant.empresa.services.business_service import AreaService, SedeService, actualizar_empresa, crear_empresa
from apps.tenant.empresa.services.crud_service import qs_list
from apps.tenant.empresa.services.selectors import AreaSelector, SedeSelector

log = logging.getLogger("empresa.api")
log_mailinbox = logging.getLogger("mailinbox.api")


# ========= ViewSets =========

class EmpresaViewSet(OrganizationalContextMixin, viewsets.ModelViewSet):
    """
    ViewSet para Empresa (Singleton por tenant).
    
    # WARNING: v2.40: Configuración moderna con Tabulator Factory.
    # WARNING: ENFORCED MODE: POST/PATCH/PUT solo para STAFF/ADMIN; no-staff recibe 405.
    
    # WARNING: PATRÓN SINGLETON:
    - Solo existe una empresa por tenant
    - POST retorna 409 si ya existe
    - GET list devuelve paginado (DRF) con 0 o 1 elemento
    
    # WARNING: JSON-ONLY (con fallback form-urlencoded legacy):
    - JSONParser (principal) + FormParser (fallback para compatibilidad)
    - Solo JSONRenderer (no BrowsableAPIRenderer)
    - Todas las respuestas son JSON
    
    # WARNING: SESSION AUTH + CSRF:
    - SessionAuthentication para workspace (cookies)
    - CSRF requerido en mutaciones (manejado por DRF)
    
    # WARNING: ENFORCED MODE (v2.40):
    - POST/PATCH/PUT/DELETE: Solo STAFF/ADMIN (IsTenantAdmin)
    - No-staff: 405 Method Not Allowed (mensaje JSON claro)
    - Flag DEV: ALLOW_EMPRESA_POST_DIRECT (solo desarrollo)
    - UI debe usar SOLO PATCH /api/v1/core/empresa/ (Core Orchestrator)
    
    # WARNING: Tabulator Factory v2.40:
    - Endpoint: GET /api/v1/empresas/ con StandardResultsSetPagination
    - Soporte ?search= para búsqueda en tiempo real
    """
    # [Fase 9, OCF] OrganizationalContextMixin agregado como capacidad opt-in
    # (expone self.get_organizational_context()) - get_queryset() NO fue
    # migrado a context.filter(): esta app resuelve `empresa` via
    # resolve_tenant_empresa() (apps/tenant/api/utils.py), que cae al
    # singleton Empresa.objects.first() SIN exigir TenantProfile, mientras
    # OrganizationalContext.resolve() SI lo exige - no son equivalentes para
    # un usuario sin perfil, y forzar el cambio romperia ese caso real. Ver
    # documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md Fase 9 (empresa).
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser, MultiPartParser]  # FormParser legacy
    renderer_classes = [JSONRenderer]
    pagination_class = StandardResultsSetPagination

    def _check_enforced_mode(self, request):
        """
        Verifica si el usuario tiene permisos para mutaciones (ENFORCED MODE).
        
        # WARNING: ENFORCED: Solo STAFF/ADMIN pueden crear/editar/eliminar.
        No-staff recibe 405 Method Not Allowed.
        
        Flag DEV: Si ALLOW_EMPRESA_POST_DIRECT=True, permite POST en desarrollo.
        """
        # Métodos seguros siempre permitidos
        if request.method in SAFE_METHODS:
            return True
        
        # Flag DEV: Permitir POST directo en desarrollo si está habilitado
        allow_dev_post = getattr(settings, 'ALLOW_EMPRESA_POST_DIRECT', False)
        if allow_dev_post and request.method == 'POST':
            return True
        
        # Verificar si es STAFF/ADMIN
        user = getattr(request, 'user', None)
        if not (user and user.is_authenticated):
            return False
        
        # Usar IsTenantAdmin para verificar permisos
        res = IsTenantAdmin().has_permission(request, self)
        return res
    
    def get_serializer_class(self):
        """Selecciona el serializer según la acción."""
        if self.action == 'list':
            return EmpresaListSerializer
        elif self.action == 'retrieve':
            return EmpresaDetailSerializer
        else:
            return EmpresaUpsertSerializer
    
    def get_serializer_context(self):
        """Asegura que el request esté disponible en el contexto del serializer."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def get_queryset(self):
        """
        # WARNING: v2.60: QuerySet optimizado con Zero Trust explícito (Tabulator v2.40).
        
        # WARNING: Zero Trust: django-tenants maneja el aislamiento por esquema, pero aplicamos validación explícita.
        # WARNING: SINGLETON: Para empresa, siempre retornamos el queryset completo (0 o 1 elemento).
        # WARNING: v2.40: Soporta filtrado por ?search= para Tabulator.
        # WARNING: PERFORMANCE BIBLE: Usa .only() para optimizar queries.
        """
        # Obtener parámetro de búsqueda
        search = self.request.query_params.get('search', None)
        
        if self.action == 'list':
            return qs_list(search=search)
        else:
            # # WARNING: Zero Trust: Para retrieve/update, usar queryset optimizado
            return Empresa.objects.only('id', 'razon_social', 'nit', 'dv', 'direccion', 'telefono', 
                                       'email_contacto', 'regimen_tributario', 'logo', 'website', 'moneda')
    
    def list(self, request: Request, *args, **kwargs) -> Response:
        """
        Lista la empresa del tenant (singleton, paginado).
        
        Endpoint: GET /api/v1/empresas/
        
        # WARNING: Retorna objeto paginado DRF: {count, results, next, previous}
        - count: 0 o 1
        - results: [] o [empresa]
        
        # WARNING: SIEMPRE retorna formato paginado para consistencia con el frontend.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Aplicar filtros explícitos soportados por la API (activa, ciudad)
        activa = request.query_params.get('activa')
        if activa is not None:
            activa_bool = str(activa).lower() in ('1', 'true', 'yes')
            queryset = queryset.filter(activa=activa_bool)

        ciudad = request.query_params.get('ciudad')
        if ciudad:
            queryset = queryset.filter(ciudad__iexact=ciudad)
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            # Caso normal: paginación activa
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # Caso fallback: paginación deshabilitada, pero forzamos formato paginado
        # Esto puede pasar si page_size es muy grande o si la paginación está deshabilitada
        serializer = self.get_serializer(queryset, many=True)
        # Retornar formato paginado manualmente para consistencia
        return Response({
            'count': queryset.count(),
            'results': serializer.data,
            'next': None,
            'previous': None
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='activas')
    def activas(self, request: Request) -> Response:
        """
        Endpoint: GET /api/v1/empresas/activas/

        Retorna solo empresas activas del tenant (paginado).
        """
        queryset = self.filter_queryset(self.get_queryset()).filter(activa=True)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data,
            'next': None,
            'previous': None
        }, status=status.HTTP_200_OK)
    
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        """
        Obtiene la empresa del tenant (singleton).
        Endpoint: GET /api/v1/empresas/{id}/
        Double Semantic Verification: valida que el usuario pertenece a la empresa.
        """
        try:
            empresa = self.get_object()
        except Exception:
            return Response(
                {'detail': 'No existe una empresa configurada para este tenant.'},
                status=status.HTTP_404_NOT_FOUND
            )
        user_empresa = getattr(getattr(request.user, 'perfil', None), 'empresa', None)
        if user_empresa and empresa.empresa_id != user_empresa.id:
            return Response({'detail': 'No autorizado para consultar esta empresa.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(empresa, context=self.get_serializer_context())
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    # # WARNING: DEPRECATED v2.40: Método datatables() eliminado - usar GET /api/v1/empresas/ con StandardResultsSetPagination
    
    @action(detail=False, methods=['get'], url_path='mi-empresa', url_name='mi-empresa')
    def mi_empresa(self, request: Request) -> Response:
        """
        Acción singleton para obtener la empresa del tenant sin ID.
        
        Endpoint: GET /api/v1/empresas/mi-empresa/
        
        # WARNING: Retorna 200 con objeto si existe, 204 si no existe (JSON-only).
        """
        empresa = self.get_queryset().first()
        
        if not empresa:
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        serializer = EmpresaDetailSerializer(empresa, context=self.get_serializer_context())
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='current-header', url_name='current-header')
    def current_header(self, request: Request) -> Response:
        """
        Acción para obtener datos básicos de la empresa para el encabezado del Editor de Cotizaciones v2.60.
        
        Endpoint: GET /api/v1/empresas/current-header/
        
        # WARNING: v2.60: Retorna solo campos esenciales: id, razon_social, nit, logo (URL absoluta).
        # WARNING: Retorna 200 con objeto si existe, 404 si no existe (JSON-only).
        # WARNING: Propósito: Exponer datos básicos de la empresa emisora para el encabezado del Editor de Cotizaciones.
        
        Response (ejemplo):
        {
            "id": 1,
            "razon_social": "Mi Empresa SAS",
            "nit": "900123456",
            "logo": "http://example.com/media/logos/logo.png"
        }
        """
        empresa = self.get_queryset().first()
        
        if not empresa:
            return Response(
                {'detail': 'No existe una empresa configurada para este tenant.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = EmpresaHeaderSerializer(empresa, context=self.get_serializer_context())
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @transaction.atomic
    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        Crea la empresa del tenant (singleton).
        
        Endpoint: POST /api/v1/empresas/
        
        # WARNING: ENFORCED MODE: Solo STAFF/ADMIN pueden crear. No-staff recibe 405.
        # WARNING: SINGLETON: Retorna 409 si ya existe una empresa.
        # WARNING: UI: La UI debe usar SOLO PATCH /api/v1/core/empresa/ (Core Orchestrator).
        """
        # # WARNING: ENFORCED: Verificar permisos antes de procesar
        if not self._check_enforced_mode(request):
            return Response(
                {
                    "error": "method_not_allowed",
                    "detail": "POST /api/v1/empresas/ solo está permitido para usuarios ADMIN/STAFF. Use PATCH /api/v1/core/empresa/ desde la UI."
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        # Solo considerar violación de singleton si existe una instancia con singleton_key=1
        # (SSoT raíz). Permitir crear otras instancias de prueba con singleton_key != 1.
        if Empresa.objects.filter(singleton_key=1).exists():
            return Response(
                {
                    "error": "singleton_violation",
                    "detail": "Ya existe una empresa con singleton_key=1 en este tenant."
                },
                status=status.HTTP_409_CONFLICT
            )
        
        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        
        # # WARNING: IMPORTANTE: singleton_key se establece automáticamente con default=1 (PositiveSmallIntegerField)
        # NO intentar establecerlo manualmente, Django lo maneja automáticamente
        instance = serializer.save()
        
        return Response(
            EmpresaDetailSerializer(instance, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request: Request) -> Response:
        """
        # WARNING: v2.60: Devuelve el HTML del formulario de empresa para HTMX Offcanvas.
        
        Endpoint: GET /api/v1/empresas/gestor-offcanvas/
        
        Query params:
        - id: ID de la empresa (opcional - si no se proporciona, es modo creación)
        
        Returns:
            Template HTML renderizado con contexto de la empresa
        """
        # # WARNING: Zero Trust: Obtener empresa del tenant actual (singleton)
        empresa = None
        id_instancia = request.query_params.get('id')
        # Blindaje: Solo intentar buscar si id_instancia es un número entero positivo
        if id_instancia and str(id_instancia).isdigit():
            try:
                empresa = get_object_or_404(
                    Empresa.objects.only('id', 'razon_social', 'nit', 'dv', 'direccion',
                                       'telefono', 'email_contacto', 'regimen_tributario',
                                       'logo', 'website', 'moneda'),
                    id=int(id_instancia)
                )
            except Empresa.DoesNotExist:
                empresa = None
        # Si id_instancia es 'undefined', '', None o no numérico, ignora y deja empresa=None
        context = {
            'empresa': empresa,
        }
        return Response(context, template_name='tenant/empresa/offcanvas_form.html')
    
    @transaction.atomic
    def update(self, request: Request, *args, **kwargs) -> Response:
        """
        # WARNING: v2.60: Actualiza la empresa del tenant (singleton, full update) usando Service Layer.
        
        Endpoint: PUT /api/v1/empresas/{id}/
        
        # WARNING: ENFORCED MODE: Solo STAFF/ADMIN pueden actualizar. No-staff recibe 405.
        # WARNING: Service Layer: Usa services.actualizar_empresa() para lógica de negocio.
        # WARNING: UI: La UI debe usar SOLO PATCH /api/v1/core/empresa/ (Core Orchestrator).
        """
        # # WARNING: ENFORCED: Verificar permisos antes de procesar
        if not self._check_enforced_mode(request):
            return Response(
                {
                    "error": "method_not_allowed",
                    "detail": "PUT /api/v1/empresas/{id}/ solo está permitido para usuarios ADMIN/STAFF. Use PATCH /api/v1/core/empresa/ desde la UI."
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        # # WARNING: Zero Trust: Intentar obtener la empresa por ID; si no existe, permitir crear
        try:
            empresa = self.get_object()
        except Exception:
            empresa = None
        
        # Validar datos con serializer
        serializer = self.get_serializer(
            empresa,
            data=request.data,
            partial=False,
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        
        # # WARNING: Service Layer: Usar servicio para actualizar o crear
        if empresa:
            empresa_result = actualizar_empresa(serializer.validated_data)
        else:
            empresa_result = crear_empresa(serializer.validated_data)
        
        return Response(
            EmpresaDetailSerializer(empresa_result, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK if empresa else status.HTTP_201_CREATED
        )
    
    @transaction.atomic
    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        """
        [ARCHITECTURE v2.61.4] Actualiza parcialmente la empresa del tenant (singleton) usando Service Layer.
        
        # WARNING: Esta implementación maneja tanto el caso con ID como el caso singleton (sin ID).
        # WARNING: UI: La UI usa SOLO PATCH /api/v1/core/empresa/ (Orquestador Core).
        """
        # 1. Seguridad: Verificar permisos ADMIN/STAFF
        if not self._check_enforced_mode(request):
            return Response(
                {
                    "error": "method_not_allowed",
                    "detail": "PATCH solo está permitido para usuarios ADMIN/STAFF."
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        # 2. Obtener instancia singleton o por PK
        try:
            # Si hay PK en kwargs, usar get_object standard
            if 'pk' in kwargs:
                empresa = self.get_object()
            else:
                # Caso singleton: obtener el primero del tenant
                empresa = self.get_queryset().first()
        except Exception:
            empresa = None
        
        # 3. Validar con Serializer
        serializer = self.get_serializer(
            empresa,
            data=request.data,
            partial=True,
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        
        # 4. Inyectar Lógica de Negocio vía Service Layer
        
        try:
            if empresa:
                # Actualizar existente
                empresa_result = actualizar_empresa(serializer.validated_data)
                return Response(
                    EmpresaDetailSerializer(empresa_result, context=self.get_serializer_context()).data,
                    status=status.HTTP_200_OK
                )
            else:
                # Crear primer registro (bootstrap)
                empresa_result = crear_empresa(serializer.validated_data)
                return Response(
                    EmpresaDetailSerializer(empresa_result, context=self.get_serializer_context()).data,
                    status=status.HTTP_201_CREATED
                )
        except Exception as e:
            log.error(f"[EmpresaViewSet.partial_update] Error: {str(e)}")
            return Response(
                {'detail': f'Error al procesar la solicitud empresarial: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """
        Elimina la empresa del tenant.
        
        Endpoint: DELETE /api/v1/empresas/{id}/
        
        # WARNING: ENFORCED MODE: Solo STAFF/ADMIN pueden eliminar. No-staff recibe 405.
        # WARNING: ADVERTENCIA: Eliminar la empresa puede afectar otras funcionalidades.
        """
        # # WARNING: ENFORCED: Verificar permisos antes de procesar
        if not self._check_enforced_mode(request):
            return Response(
                {
                    "error": "method_not_allowed",
                    "detail": "DELETE /api/v1/empresas/{id}/ solo está permitido para usuarios ADMIN/STAFF."
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        try:
            empresa = self.get_object()
        except Exception:
            return Response(
                {'detail': 'No existe una empresa para eliminar.'},
                status=status.HTTP_404_NOT_FOUND
            )

        empresa.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MailInboxConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet para configuraciones de buzones de correo (SSoT).
    
    # WARNING: v2.40: Configuración moderna con Tabulator Factory y lazy loading.
    # WARNING: SSoT: Toda gestión de cuentas de correo se hace aquí.
    # WARNING: API-First: JSON-first (JSONParser principal + FormParser legacy).
    # WARNING: SEGURIDAD: Passwords nunca expuestos, cifrado automático.
    # WARNING: PERMISOS: IsTenantAdminOrReadOnly (lectura para autenticados, escritura para ADMIN/STAFF).
    """
    queryset = MailInboxConfig.objects.none()  # DRF requiere queryset de clase, .none() suficiente
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser]  # FormParser legacy
    renderer_classes = [JSONRenderer]
    pagination_class = StandardResultsSetPagination
    
    # # WARNING: CRÍTICO: Asegurar que los métodos HTTP estén permitidos explícitamente
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace']
    
    def get_serializer_class(self):
        """
        Selecciona el serializer según la acción.
        
        # WARNING: v2.37: Alineado con norma de exposición de datos.
        - list: MailInboxConfigListSerializer (campos mínimos)
        - retrieve/create/update: MailInboxConfigDetailSerializer (campos extendidos, sin secretos)
        """
        if self.action == 'list':
            return MailInboxConfigListSerializer
        return MailInboxConfigDetailSerializer
    
    @action(detail=False, methods=["post"], url_path="deprecated-create")
    def deprecated_create(self, request: Request, *args, **kwargs) -> Response:
        """
        # WARNING: DEPRECATED v2.40: Esta ruta está deprecada.
        
        Usa PATCH /api/v1/core/empresa/ con mail_inbox_config en el payload.
        
        Returns:
            405 Method Not Allowed con mensaje claro
        """
        return Response(
            {
                "error": "deprecated_route",
                "detail": "Esta ruta está deprecada. Usa PATCH /api/v1/core/empresa/ con 'mail_inbox_config' en el payload para crear/actualizar configuraciones de buzón."
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def get_queryset(self):
        """
        QuerySet optimizado con .only() para mínima exposición (Tabulator v2.40).

        # WARNING: v2.40: Alineado con Service Layer Pattern.
        # WARNING: v2.40: Soporta filtrado por ?search= para Tabulator.

        # SEC-FIX [2026-08-05]: django-tenants SOLO aisla por esquema (tenant),
        # NO por empresa. MailInboxConfig hereda `empresa` (FK obligatoria) de
        # SintelTenantBaseModel -- sin filtrar por empresa_id aqui, cualquier
        # usuario autenticado del tenant podia listar/ver/editar/eliminar la
        # configuracion de buzon de correo (host IMAP, puerto, usuario) de
        # OTRAS empresas dentro del mismo tenant (solo el password quedaba
        # deferred, sin control de acceso real). Corregido filtrando por
        # empresa_id en las 3 ramas, igual que el resto de selectors de este
        # proyecto (AGENTS.md: "empresa_id en cada query").
        """
        empresa = resolve_tenant_empresa(self.request, self)
        if not empresa:
            return MailInboxConfig.objects.none()

        # WARNING: AISLAMIENTO: filtro explicito por empresa_id (ver SEC-FIX arriba)
        base_qs = MailInboxConfig.objects.filter(empresa_id=empresa.id).defer('imap_password')

        # Obtener parámetro de búsqueda
        search = self.request.query_params.get('search', None)

        if self.action == 'list':
            qs = base_qs.only(
                'id', 'empresa_id', 'nombre', 'email_address', 'provider', 'protocol',
                'imap_host', 'imap_port', 'imap_ssl', 'is_active',
                'created_at', 'updated_at'
            )

            # Aplicar filtro de búsqueda si se proporciona
            if search:
                qs = qs.filter(
                    Q(nombre__icontains=search) |
                    Q(email_address__icontains=search) |
                    Q(imap_host__icontains=search) |
                    Q(provider__icontains=search)
                )

            return qs
        elif self.action == 'retrieve':
            # # WARNING: ZERO WASTE: Solo cargar campos necesarios para detalle
            return base_qs.only(
                'id', 'empresa_id', 'nombre', 'email_address', 'provider', 'protocol', 'is_active',
                'imap_host', 'imap_port', 'imap_username', 'imap_ssl', 'imap_starttls',
                'imap_mailbox', 'imap_mark_as_seen', 'imap_max_attachment_mb', 'imap_move_processed_to',
                'created_at', 'updated_at'
            )
        else:
            # # WARNING: Para otras acciones (create, update, delete, render_offcanvas, etc.), retornar QuerySet completo
            return base_qs
    
    def list(self, request: Request, *args, **kwargs) -> Response:
        """
        Lista configuraciones de buzones (paginado, campos mínimos, Tabulator v2.40).
        
        Endpoint: GET /api/v1/empresas/mail-inbox-config/
        
        # WARNING: NORMA DE EXPOSICIÓN: Solo campos operativos, sin secretos.
        # WARNING: v2.40: SIEMPRE retorna formato paginado para consistencia con Tabulator Factory.
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Filtros opcionales
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        provider = request.query_params.get('provider')
        if provider:
            queryset = queryset.filter(provider=provider)
        
        # # WARNING: v2.40: SIEMPRE usar paginación para consistencia con Tabulator Factory
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            # Caso normal: paginación activa
            serializer = self.get_serializer(page, many=True)
            log_mailinbox.info(f"[MailInboxConfigViewSet.list] Retornando {len(serializer.data)} configuraciones (paginado)")
            return self.get_paginated_response(serializer.data)
        
        # Caso fallback: paginación deshabilitada, pero forzamos formato paginado
        # Esto puede pasar si page_size es muy grande o si la paginación está deshabilitada
        serializer = self.get_serializer(queryset, many=True)
        # Retornar formato paginado manualmente para consistencia con Tabulator Factory
        log_mailinbox.info(f"[MailInboxConfigViewSet.list] Retornando {len(serializer.data)} configuraciones (formato paginado manual)")
        return Response({
            'count': queryset.count(),
            'results': serializer.data,
            'next': None,
            'previous': None
        }, status=status.HTTP_200_OK)
    
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        """
        Obtiene una configuración de buzón de correo específica.
        
        Endpoint: GET /api/v1/empresas/mail-inbox-config/{id}/
        
        # WARNING: v2.40: Alineado con arquitectura API-First.
        # WARNING: SEGURIDAD: Passwords nunca expuestos (serializer write_only).
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            log_mailinbox.info(f"[MailInboxConfigViewSet.retrieve] Configuración obtenida: {instance.id}")
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            # Manejar cualquier excepción (DoesNotExist, Http404, etc.)
            log_mailinbox.warning(f"[MailInboxConfigViewSet.retrieve] Error: {str(e)}")
            return Response(
                {'detail': 'Configuración de buzón de correo no encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def _check_enforced_mode(self, request):
        """
        Verifica si el usuario tiene permisos para mutaciones (ENFORCED MODE).
        
        # WARNING: ENFORCED: Solo STAFF/ADMIN pueden crear/editar/eliminar.
        No-staff recibe 405 Method Not Allowed.
        
        Returns:
            tuple: (ok: bool, reason: str | None)
        """
        user = request.user
        if not (user and user.is_authenticated):
            return False, "Usuario no autenticado."
        
        if request.method in SAFE_METHODS:
            return True, None  # Lectura siempre permitida
        
        # Para mutaciones (POST, PUT, PATCH, DELETE)
        if IsTenantAdmin().has_permission(request, self):
            return True, None  # ADMIN/STAFF tienen permiso
        
        return False, "Solo usuarios ADMIN/STAFF del tenant pueden crear/editar/eliminar configuraciones de correo."
    
    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        Crea una nueva configuración de buzón de correo.
        
        Endpoint: POST /api/v1/empresas/mail-inbox-config/
        
        # WARNING: v2.60: HABILITADO - Permite creación directa de configuraciones de buzón.
        # WARNING: v2.40: ENFORCED MODE - Solo STAFF/ADMIN.
        # WARNING: v2.40: Alineado con arquitectura API-First.
        """
        # # WARNING: v2.60: Verificar permisos de escritura (ENFORCED MODE)
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            log_mailinbox.warning(f"[MailInboxConfigViewSet.create] 405: {reason}")
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Usar el serializer para crear la configuración
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        log_mailinbox.info(f"[MailInboxConfigViewSet.create] Configuración creada: {serializer.instance.id}")
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request: Request, *args, **kwargs) -> Response:
        """
        Actualiza una configuración de buzón de correo (actualización completa).
        
        Endpoint: PUT /api/v1/empresas/mail-inbox-config/{id}/
        
        # WARNING: v2.40: ENFORCED MODE - Solo STAFF/ADMIN.
        # WARNING: v2.40: Alineado con arquitectura API-First.
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            log_mailinbox.warning(f"[MailInboxConfigViewSet.update] 405: {reason}")
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        log_mailinbox.info(f"[MailInboxConfigViewSet.update] Configuración actualizada: {instance.id}")
        return Response(serializer.data)
    
    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        """
        Actualiza parcialmente una configuración de buzón de correo.
        
        Endpoint: PATCH /api/v1/empresas/mail-inbox-config/{id}/
        
        # WARNING: v2.40: ENFORCED MODE - Solo STAFF/ADMIN.
        # WARNING: v2.40: Alineado con arquitectura API-First.
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            log_mailinbox.warning(f"[MailInboxConfigViewSet.partial_update] 405: {reason}")
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """
        Elimina una configuración de buzón de correo.
        
        Endpoint: DELETE /api/v1/empresas/mail-inbox-config/{id}/
        
        # WARNING: v2.40: ENFORCED MODE - Solo STAFF/ADMIN.
        # WARNING: v2.40: Alineado con arquitectura API-First.
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            log_mailinbox.warning(f"[MailInboxConfigViewSet.destroy] 405: {reason}")
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        instance = self.get_object()
        self.perform_destroy(instance)
        log_mailinbox.info(f"[MailInboxConfigViewSet.destroy] Configuración eliminada: {instance.id}")
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    # # WARNING: DEPRECATED v2.40: Método datatables() eliminado - usar GET /api/v1/empresas/mail-inbox-config/ con StandardResultsSetPagination
    
    @action(detail=False, methods=['get'], url_path='render-offcanvas', url_name='render-offcanvas')
    def render_offcanvas(self, request: Request, *args, **kwargs) -> Response:
        """
        Renderiza el offcanvas para crear/editar configuración de buzón (HTMX).
        
        Endpoint: GET /api/v1/empresas/mail-inbox-config/render-offcanvas/?id={id}
        
        # WARNING: v2.60: HTMX-Driven - Retorna HTML partial para cargar en offcanvas.
        - Si se proporciona ?id={id}, carga datos existentes (edición)
        - Si no se proporciona id, muestra formulario vacío (creación)
        
        # WARNING: AISLAMIENTO: django-tenants maneja automáticamente el aislamiento por esquema.
        # WARNING: ZERO WASTE: Solo carga campos necesarios para el formulario.
        # WARNING: MANEJO DE ERRORES: Retorna HTML con error_handler.html incluido para mostrar errores.
        """
        config_id = request.query_params.get('id')
        instance = None
        error_message = None
        
        # # WARNING: AISLAMIENTO: get_queryset() ya aplica el filtro automático de django-tenants
        # No es necesario filtrar manualmente por tenant, django-tenants lo maneja por esquema
        if config_id:
            try:
                # # WARNING: AISLAMIENTO: Usar QuerySet base directamente (django-tenants ya filtra por esquema)
                # # WARNING: ZERO WASTE: Solo cargar campos necesarios para el formulario
                # # WARNING: IMPORTANTE: No usar self.get_queryset() aquí porque puede no estar configurado para render_offcanvas
                instance = MailInboxConfig.objects.only(
                    'id', 'nombre', 'email_address', 'provider', 'is_active',
                    'imap_host', 'imap_port', 'imap_username', 'imap_ssl', 'imap_starttls',
                    'imap_mailbox', 'imap_mark_as_seen', 'imap_max_attachment_mb', 'imap_move_processed_to'
                ).get(id=config_id)
                logger.debug(f"[render_offcanvas] Configuración {config_id} cargada exitosamente")
            except MailInboxConfig.DoesNotExist:
                # # WARNING: MANEJO GRACIAL: Si no existe, simplemente no cargar datos (modo creación)
                logger.warning(f"[render_offcanvas] Configuración con ID {config_id} no encontrada para este tenant")
                error_message = f"La configuración con ID {config_id} no existe o no pertenece a este tenant."
            except Exception as e:
                # # WARNING: MANEJO DE ERRORES: Capturar cualquier error inesperado
                logger.error(f"[render_offcanvas] Error al obtener configuración: {str(e)}", exc_info=True)
                error_message = f"Error al cargar la configuración: {str(e)}"
        
        context = {
            'config': instance,
            'is_edit': instance is not None,
            'error_message': error_message,  # # WARNING: Pasar error al template para mostrar en error_handler.html
        }
        
        try:
            template_name = (
                'tenant/empresa/offcanvas_editar_mailinboxconfig.html'
                if instance else
                'tenant/empresa/offcanvas_crear_mailinboxconfig.html'
            )
            logger.debug(f"[render_offcanvas] template={template_name}, config={instance is not None}, error={error_message}")
            html = render_to_string(
                template_name,
                context,
                request=request
            )
            logger.debug(f"[render_offcanvas] Template renderizado exitosamente, tamaño: {len(html)} caracteres")
            # # WARNING: IMPORTANTE: Retornar HTML directamente sin TemplateHTMLRenderer
            # TemplateHTMLRenderer requiere template_name en la respuesta, pero nosotros ya renderizamos el HTML
            return HttpResponse(html, content_type='text/html')
        except TemplateDoesNotExist as e:
            # # WARNING: ERROR DE TEMPLATE: Si el template no existe, retornar error estructurado con error_handler
            logger.error(f"[render_offcanvas] Template no encontrado: {str(e)}")
            try:
                # Intentar renderizar error_handler.html desde el template base
                error_context = {
                    'error_message': f"Error: Template no encontrado. Verifique la ruta del template. ({str(e)})"
                }
                error_handler_html = render_to_string(
                    'tenant/core/partials/error_handler.html',
                    error_context,
                    request=request
                )
            except:
                error_handler_html = '<div id="error-container" class="mt-3"><div class="alert alert-danger"><i class="bi bi-exclamation-triangle"></i> Error: Template no encontrado.</div></div>'
            
            error_html = f"""
            <div class="offcanvas offcanvas-end" tabindex="-1" id="offcanvas-mailinbox" aria-labelledby="offcanvas-mailinbox-label">
                <div class="offcanvas-header border-bottom">
                    <h5 class="offcanvas-title" id="offcanvas-mailinbox-label">Error</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="offcanvas" aria-label="Cerrar"></button>
                </div>
                <div class="offcanvas-body">
                    {error_handler_html}
                </div>
            </div>
            """
            return HttpResponse(error_html, content_type='text/html', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            # # WARNING: ERROR GENERAL: Capturar cualquier error inesperado en el renderizado
            logger.error(f"[render_offcanvas] Error inesperado al renderizar template: {str(e)}", exc_info=True)
            try:
                # Intentar renderizar error_handler.html desde el template base
                error_context = {
                    'error_message': f"Error inesperado: {str(e)}"
                }
                error_handler_html = render_to_string(
                    'tenant/core/partials/error_handler.html',
                    error_context,
                    request=request
                )
            except:
                error_handler_html = f'<div id="error-container" class="mt-3"><div class="alert alert-danger"><i class="bi bi-exclamation-triangle"></i> Error inesperado: {str(e)}</div></div>'
            
            error_html = f"""
            <div class="offcanvas offcanvas-end" tabindex="-1" id="offcanvas-mailinbox" aria-labelledby="offcanvas-mailinbox-label">
                <div class="offcanvas-header border-bottom">
                    <h5 class="offcanvas-title" id="offcanvas-mailinbox-label">Error</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="offcanvas" aria-label="Cerrar"></button>
                </div>
                <div class="offcanvas-body">
                    {error_handler_html}
                </div>
            </div>
            """
            return HttpResponse(error_html, content_type='text/html', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='test-connection', url_name='test-connection')
    def test_connection(self, request: Request) -> Response:
        """
        Prueba conexión a buzón de correo sin persistir datos.
        
        Endpoint: POST /api/v1/empresas/mail-inbox-config/test-connection/
        
        # WARNING: v2.40: Alineado con arquitectura Service Layer y SSoT.
        - Usa servicio desacoplado maildigester_test_connection()
        - No persiste credenciales, solo prueba conexión
        - Password nunca se expone en respuesta ni logs
        
        Request body (ejemplo):
        {
            "host": "imap.gmail.com",
            "port": 993,
            "protocol": "imap",
            "username": "user@gmail.com",
            "password": "app_password",
            "use_ssl": true,
            "use_starttls": false
        }
        
        Returns:
            {
                "ok": bool,
                "message": str
            }
        """
        # Validar datos con serializer dedicado
        serializer = MailInboxConfigTestConnectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validated_data = serializer.validated_data
        
        # Preparar configuración para el servicio (sin exponer password en logs)
        config = {
            'host': validated_data['host'],
            'port': validated_data['port'],
            'protocol': validated_data['protocol'],
            'username': validated_data['username'],
            'password': validated_data['password'],
            'use_ssl': validated_data['use_ssl'],
            'use_starttls': validated_data.get('use_starttls', False),
        }
        
        # Llamar al servicio desacoplado
        try:
            ok, message = maildigester_test_connection(config)
            
            if ok:
                log_mailinbox.info(f"[MailInboxConfigViewSet.test_connection] Test connection OK: {config['username']}@{config['host']}:{config['port']}")
                return Response(
                    {'ok': True, 'message': message},
                    status=status.HTTP_200_OK
                )
            else:
                log_mailinbox.warning(f"[MailInboxConfigViewSet.test_connection] Test connection FAILED: {config['username']}@{config['host']}:{config['port']} - {message}")
                return Response(
                    {'ok': False, 'message': message},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            log_mailinbox.error(f"[MailInboxConfigViewSet.test_connection] Error inesperado: {e}", exc_info=True)
            return Response(
                {'ok': False, 'message': f'Error inesperado al probar conexión: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='test-connection', url_name='test-connection-detail')
    def test_connection_saved(self, request: Request, pk=None) -> Response:
        """
        Prueba conexión a un buzón de correo ya guardado.
        
        Endpoint: POST /api/v1/empresas/mail-inbox-config/{id}/test-connection/
        """
        instance = self.get_object()
        
        # Desencriptar password real
        try:
            raw_pass = instance.imap_password or instance.password
            if not raw_pass:
                return Response({'ok': False, 'message': 'La configuración no tiene una contraseña guardada.'}, status=status.HTTP_400_BAD_REQUEST)
            password = decrypt_password(raw_pass)
        except Exception as e:
            log_mailinbox.warning(f"[MailInboxConfigViewSet.test_connection_detail] Error desencriptando password (posible clave rotada o texto plano): {e}")
            # # WARNING: GRACEFUL DEGRADATION: En desarrollo, si falla el descifrado, intentar usar el valor crudo (posible texto plano)
            password = raw_pass
            
        config = {
            'host': instance.imap_host or instance.host,
            'port': instance.imap_port or instance.port,
            'protocol': "imap",
            'username': instance.imap_username or instance.username or instance.email_address,
            'password': password,
            'use_ssl': bool(instance.imap_ssl if instance.imap_ssl is not None else instance.ssl),
            'use_starttls': bool(instance.imap_starttls),
            'mailbox': instance.imap_mailbox or instance.mailbox or "INBOX",
        }
        
        try:
            ok, message = maildigester_test_connection(config)
            
            if ok:
                log_mailinbox.info(f"[MailInboxConfigViewSet.test_connection_detail] Test connection OK: {config['username']}@{config['host']}:{config['port']}")
                return Response({'ok': True, 'message': message}, status=status.HTTP_200_OK)
            else:
                log_mailinbox.warning(f"[MailInboxConfigViewSet.test_connection_detail] Test connection FAILED: {config['username']}@{config['host']}:{config['port']} - {message}")
                return Response({'ok': False, 'message': message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            log_mailinbox.error(f"[MailInboxConfigViewSet.test_connection_detail] Error inesperado: {e}", exc_info=True)
            return Response({'ok': False, 'message': f'Error inesperado al probar conexión: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ========= Vistas auxiliares (funciones) =========

@api_view(['GET'])
@authentication_classes([JWTAuthentication, SessionAuthentication])
@permission_classes([permissions.IsAuthenticated, IsTenantMember])
def form_metadata(request):
    """
    Endpoint para obtener metadata del formulario de empresa.
    
    Endpoint: GET /api/v1/empresa/form-metadata/
    
    Retorna todas las opciones necesarias para poblar selects del frontend:
    - Tipos de contribuyente (clases y segmentos)
    - Regímenes de renta
    - Responsabilidades RUT
    
    # WARNING: AUTONOMÍA: Usa choices locales desde apps/tenant/empresa/choices/
    """
    try:
        # Construir metadata desde choices locales
        regimenes = [{"codigo": codigo, "nombre": nombre} for codigo, nombre in get_regimen_choices()]
        segmentos = [{"value": codigo, "label": nombre} for codigo, nombre in get_segmento_dian_choices()]
        responsabilidades = [{"codigo": codigo, "nombre": nombre} for codigo, nombre in get_responsabilidad_rut_choices()]
        
        metadata = {
            "tipo_contribuyente": {
                "clases": [
                    {"codigo": "PN", "nombre": "Persona Natural"},
                    {"codigo": "PJ", "nombre": "Persona Jurídica"},
                ]
            },
            "segmentos_dian": segmentos,
            "regimenes_renta": regimenes,
            "responsabilidades_rut": responsabilidades,
        }
        
        return Response(metadata, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'detail': f'Error al obtener metadata: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([JWTAuthentication, SessionAuthentication])
@permission_classes([permissions.IsAuthenticated, IsTenantMember])
def actividades_lookup(request):
    """
    Endpoint para búsqueda de actividades económicas (CIIU).
    
    Endpoint: GET /api/v1/empresa/actividades-lookup/?q=&limit=
    
    Parámetros:
        - q: Query de búsqueda (código)
        - limit: Límite de resultados (default: 10)
    
    # WARNING: AUTONOMÍA: CIIU es texto libre. Este endpoint retorna lista vacía.
    El frontend puede usar el campo como texto libre o implementar su propia búsqueda.
    """
    try:
        q = request.GET.get('q', '').strip()
        limit = int(request.GET.get('limit', 10))
        
        # Como CIIU es texto libre en esta app autónoma, retornar lista vacía
        # El frontend puede usar el campo como texto libre
        return Response([], status=status.HTTP_200_OK)
    except ValueError:
        return Response(
            {'detail': 'El parámetro limit debe ser un número entero'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'detail': f'Error en búsqueda: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Alias para compatibilidad con el nombre solicitado
ciiu_lookup = actividades_lookup


class SedeViewSet(OrganizationalContextMixin, BaseTenantViewSet):
    """
    ViewSet para Sedes (Sucursales).
    Aislamiento tenant-isolated y lookup por UUID heredado de BaseTenantViewSet.
    """
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser]
    renderer_classes = [JSONRenderer]
    pagination_class = StandardResultsSetPagination

    @cached_property
    def tenant_empresa(self):
        return resolve_tenant_empresa(self.request, self)

    def get_empresa(self):
        return self.tenant_empresa

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['empresa_id'] = self.get_empresa().id
        return context

    def get_serializer_class(self):
        if self.action == 'list':
            return SedeListSerializer
        elif self.action == 'retrieve':
            return SedeDetailSerializer
        return SedeUpsertSerializer

    def get_queryset(self):
        empresa_id = self.get_empresa().id
        search = self.request.query_params.get('search', None)

        if self.action == 'list':
            return SedeSelector.get_list(empresa_id, search=search)
        else:
            return Sede.objects.filter(empresa_id=empresa_id)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        empresa_id = self.get_empresa().id
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            sede = SedeService.crear_sede(empresa_id, serializer.validated_data)
            return Response(
                SedeDetailSerializer(sede, context=self.get_serializer_context()).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        empresa_id = self.get_empresa().id
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            sede = SedeService.actualizar_sede(empresa_id, instance.uuid, serializer.validated_data)
            return Response(
                SedeDetailSerializer(sede, context=self.get_serializer_context()).data,
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        empresa_id = self.get_empresa().id
        instance = self.get_object()

        try:
            SedeService.eliminar_sede(empresa_id, instance.uuid)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='render-offcanvas', url_name='render-offcanvas')
    def render_offcanvas(self, request: Request, *args, **kwargs) -> Response:
        sede_uuid = request.query_params.get('uuid')
        empresa_id = self.get_empresa().id
        instance = None
        if sede_uuid:
            try:
                instance = Sede.objects.only(
                    'id', 'uuid', 'nombre', 'direccion', 'telefono', 'encargado_nombre'
                ).get(empresa_id=empresa_id, uuid=sede_uuid)
            except Sede.DoesNotExist:
                pass

        context = {
            'sede': instance,
            'is_edit': instance is not None,
        }

        template = (
            'tenant/empresa/offcanvas_editar_sede.html'
            if instance else
            'tenant/empresa/offcanvas_crear_sede.html'
        )
        html = render_to_string(template, context, request=request)
        return HttpResponse(html, content_type='text/html')


class AreaViewSet(OrganizationalContextMixin, BaseTenantViewSet):
    """
    ViewSet para Areas (Departamentos).
    Aislamiento tenant-isolated y lookup por UUID heredado de BaseTenantViewSet.
    """
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser]
    renderer_classes = [JSONRenderer]
    pagination_class = StandardResultsSetPagination

    @cached_property
    def tenant_empresa(self):
        return resolve_tenant_empresa(self.request, self)

    def get_empresa(self):
        return self.tenant_empresa

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['empresa_id'] = self.get_empresa().id
        return context

    def get_serializer_class(self):
        if self.action == 'list':
            return AreaListSerializer
        elif self.action == 'retrieve':
            return AreaDetailSerializer
        return AreaUpsertSerializer

    def get_queryset(self):
        empresa_id = self.get_empresa().id
        sede_uuid = self.request.query_params.get('sede_uuid', None)
        search = self.request.query_params.get('search', None)

        if self.action == 'list':
            return AreaSelector.get_list(empresa_id, search=search)
        else:
            return Area.objects.filter(sede__empresa_id=empresa_id)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        empresa_id = self.get_empresa().id
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            sede_id = serializer.validated_data['sede'].id
            data = {
                'sede': sede_id,
                'nombre': serializer.validated_data['nombre'],
                'codigo_funcionamiento': serializer.validated_data['codigo_funcionamiento'],
            }
            area = AreaService.crear_area(empresa_id, data)
            return Response(
                AreaDetailSerializer(area, context=self.get_serializer_context()).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        empresa_id = self.get_empresa().id
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            sede_id = serializer.validated_data['sede'].id
            data = {
                'sede': sede_id,
                'nombre': serializer.validated_data['nombre'],
                'codigo_funcionamiento': serializer.validated_data['codigo_funcionamiento'],
            }
            area = AreaService.actualizar_area(empresa_id, instance.uuid, data)
            return Response(
                AreaDetailSerializer(area, context=self.get_serializer_context()).data,
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        empresa_id = self.get_empresa().id
        instance = self.get_object()

        try:
            AreaService.eliminar_area(empresa_id, instance.uuid)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='render-offcanvas', url_name='render-offcanvas')
    def render_offcanvas(self, request: Request, *args, **kwargs) -> Response:
        area_uuid = request.query_params.get('uuid')
        empresa_id = self.get_empresa().id
        instance = None
        if area_uuid:
            try:
                instance = Area.objects.only(
                    'id', 'uuid', 'sede_id', 'nombre', 'codigo_funcionamiento'
                ).get(sede__empresa_id=empresa_id, uuid=area_uuid)
            except Area.DoesNotExist:
                pass

        sedes = SedeSelector.get_list(empresa_id)

        context = {
            'area': instance,
            'is_edit': instance is not None,
            'sedes': sedes,
        }

        template = (
            'tenant/empresa/offcanvas_editar_area.html'
            if instance else
            'tenant/empresa/offcanvas_crear_area.html'
        )
        html = render_to_string(template, context, request=request)
        return HttpResponse(html, content_type='text/html')
