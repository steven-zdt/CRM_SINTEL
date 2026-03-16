"""
ViewSets y vistas auxiliares para la app empresa.

⚠️ v2.40: Configuración moderna con Tabulator Factory y lazy loading.

⚠️ IMPORTANTE: 
- django-tenants maneja automáticamente el aislamiento por esquema
- NO es necesario filtrar manualmente por tenant_id
- Patrón Singleton: Solo una empresa por tenant
- JSON-first: JSONParser (principal) + FormParser (legacy)
- SessionAuthentication + CSRF para workspace
"""
import logging
from django.db import transaction
from django.db.models import Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from apps.tenant.empresa.models import Empresa, MailInboxConfig
from apps.tenant.empresa.api.serializers import (
    EmpresaListSerializer,
    EmpresaDetailSerializer,
    EmpresaHeaderSerializer,
    EmpresaUpsertSerializer,
    MailInboxConfigListSerializer,
    MailInboxConfigDetailSerializer,
    MailInboxConfigTestConnectionSerializer,
)
from apps.tenant.empresa.permissions import IsTenantAdmin
from apps.tenant.api.permissions import IsTenantMember, IsTenantAdminOrReadOnly
from apps.config.api.pagination import StandardResultsSetPagination

log = logging.getLogger("empresa.api")
log_mailinbox = logging.getLogger("mailinbox.api")


# ========= ViewSets =========

class EmpresaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Empresa (Singleton por tenant).
    
    ⚠️ v2.40: Configuración moderna con Tabulator Factory.
    ⚠️ ENFORCED MODE: POST/PATCH/PUT solo para STAFF/ADMIN; no-staff recibe 405.
    
    ⚠️ PATRÓN SINGLETON:
    - Solo existe una empresa por tenant
    - POST retorna 409 si ya existe
    - GET list devuelve paginado (DRF) con 0 o 1 elemento
    
    ⚠️ JSON-ONLY (con fallback form-urlencoded legacy):
    - JSONParser (principal) + FormParser (fallback para compatibilidad)
    - Solo JSONRenderer (no BrowsableAPIRenderer)
    - Todas las respuestas son JSON
    
    ⚠️ SESSION AUTH + CSRF:
    - SessionAuthentication para workspace (cookies)
    - CSRF requerido en mutaciones (manejado por DRF)
    
    ⚠️ ENFORCED MODE (v2.40):
    - POST/PATCH/PUT/DELETE: Solo STAFF/ADMIN (IsTenantAdmin)
    - No-staff: 405 Method Not Allowed (mensaje JSON claro)
    - Flag DEV: ALLOW_EMPRESA_POST_DIRECT (solo desarrollo)
    - UI debe usar SOLO PATCH /api/v1/core/empresa/ (Core Orchestrator)
    
    ⚠️ Tabulator Factory v2.40:
    - Endpoint: GET /api/v1/empresas/ con StandardResultsSetPagination
    - Soporte ?search= para búsqueda en tiempo real
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser, MultiPartParser]  # FormParser legacy
    renderer_classes = [JSONRenderer]
    pagination_class = StandardResultsSetPagination
    
    def _check_enforced_mode(self, request):
        """
        Verifica si el usuario tiene permisos para mutaciones (ENFORCED MODE).
        
        ⚠️ ENFORCED: Solo STAFF/ADMIN pueden crear/editar/eliminar.
        No-staff recibe 405 Method Not Allowed.
        
        Flag DEV: Si ALLOW_EMPRESA_POST_DIRECT=True, permite POST en desarrollo.
        """
        from django.conf import settings
        from rest_framework.permissions import SAFE_METHODS
        
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
        return IsTenantAdmin().has_permission(request, self)
    
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
        ⚠️ v2.60: QuerySet optimizado con Zero Trust explícito (Tabulator v2.40).
        
        ⚠️ Zero Trust: django-tenants maneja el aislamiento por esquema, pero aplicamos validación explícita.
        ⚠️ SINGLETON: Para empresa, siempre retornamos el queryset completo (0 o 1 elemento).
        ⚠️ v2.40: Soporta filtrado por ?search= para Tabulator.
        ⚠️ PERFORMANCE BIBLE: Usa .only() para optimizar queries.
        """
        from apps.tenant.empresa.services import qs_list
        
        # Obtener parámetro de búsqueda
        search = self.request.query_params.get('search', None)
        
        if self.action == 'list':
            return qs_list(search=search)
        else:
            # ⚠️ Zero Trust: Para retrieve/update, usar queryset optimizado
            return Empresa.objects.only('id', 'razon_social', 'nit', 'dv', 'direccion', 'telefono', 
                                       'email_contacto', 'regimen_tributario', 'logo', 'website', 'moneda')
    
    def list(self, request: Request, *args, **kwargs) -> Response:
        """
        Lista la empresa del tenant (singleton, paginado).
        
        Endpoint: GET /api/v1/empresas/
        
        ⚠️ Retorna objeto paginado DRF: {count, results, next, previous}
        - count: 0 o 1
        - results: [] o [empresa]
        
        ⚠️ SIEMPRE retorna formato paginado para consistencia con el frontend.
        """
        queryset = self.filter_queryset(self.get_queryset())
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
    
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        """
        Obtiene la empresa del tenant (singleton).
        
        Endpoint: GET /api/v1/empresas/{id}/
        """
        empresa = self.get_queryset().first()
        
        if not empresa:
            return Response(
                {'detail': 'No existe una empresa configurada para este tenant.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(empresa, context=self.get_serializer_context())
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    # ⚠️ DEPRECATED v2.40: Método datatables() eliminado - usar GET /api/v1/empresas/ con StandardResultsSetPagination
    
    @action(detail=False, methods=['get'], url_path='mi-empresa', url_name='mi-empresa')
    def mi_empresa(self, request: Request) -> Response:
        """
        Acción singleton para obtener la empresa del tenant sin ID.
        
        Endpoint: GET /api/v1/empresas/mi-empresa/
        
        ⚠️ Retorna 200 con objeto si existe, 204 si no existe (JSON-only).
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
        
        ⚠️ v2.60: Retorna solo campos esenciales: id, razon_social, nit, logo (URL absoluta).
        ⚠️ Retorna 200 con objeto si existe, 404 si no existe (JSON-only).
        ⚠️ Propósito: Exponer datos básicos de la empresa emisora para el encabezado del Editor de Cotizaciones.
        
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
        
        ⚠️ ENFORCED MODE: Solo STAFF/ADMIN pueden crear. No-staff recibe 405.
        ⚠️ SINGLETON: Retorna 409 si ya existe una empresa.
        ⚠️ UI: La UI debe usar SOLO PATCH /api/v1/core/empresa/ (Core Orchestrator).
        """
        # ⚠️ ENFORCED: Verificar permisos antes de procesar
        if not self._check_enforced_mode(request):
            return Response(
                {
                    "error": "method_not_allowed",
                    "detail": "POST /api/v1/empresas/ solo está permitido para usuarios ADMIN/STAFF. Use PATCH /api/v1/core/empresa/ desde la UI."
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        if Empresa.objects.exists():
            return Response(
                {
                    "error": "singleton_violation",
                    "detail": "Ya existe una empresa en este tenant."
                },
                status=status.HTTP_409_CONFLICT
            )
        
        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        
        # ⚠️ IMPORTANTE: singleton_key se establece automáticamente con default=1 (PositiveSmallIntegerField)
        # NO intentar establecerlo manualmente, Django lo maneja automáticamente
        instance = serializer.save()
        
        return Response(
            EmpresaDetailSerializer(instance, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request: Request) -> Response:
        """
        ⚠️ v2.60: Devuelve el HTML del formulario de empresa para HTMX Offcanvas.
        
        Endpoint: GET /api/v1/empresas/gestor-offcanvas/
        
        Query params:
        - id: ID de la empresa (opcional - si no se proporciona, es modo creación)
        
        Returns:
            Template HTML renderizado con contexto de la empresa
        """
        from django.shortcuts import get_object_or_404
        
        # ⚠️ Zero Trust: Obtener empresa del tenant actual (singleton)
        empresa = None
        id_instancia = request.query_params.get('id')
        
        if id_instancia:
            try:
                empresa = get_object_or_404(
                    Empresa.objects.only('id', 'razon_social', 'nit', 'dv', 'direccion', 
                                       'telefono', 'email_contacto', 'regimen_tributario', 
                                       'logo', 'website', 'moneda'),
                    id=id_instancia
                )
            except Empresa.DoesNotExist:
                empresa = None
        
        context = {
            'empresa': empresa,
        }
        
        return Response(context, template_name='tenant/core/partials/empresa/offcanvas_form.html')
    
    @transaction.atomic
    def update(self, request: Request, *args, **kwargs) -> Response:
        """
        ⚠️ v2.60: Actualiza la empresa del tenant (singleton, full update) usando Service Layer.
        
        Endpoint: PUT /api/v1/empresas/{id}/
        
        ⚠️ ENFORCED MODE: Solo STAFF/ADMIN pueden actualizar. No-staff recibe 405.
        ⚠️ Service Layer: Usa services.actualizar_empresa() para lógica de negocio.
        ⚠️ UI: La UI debe usar SOLO PATCH /api/v1/core/empresa/ (Core Orchestrator).
        """
        # ⚠️ ENFORCED: Verificar permisos antes de procesar
        if not self._check_enforced_mode(request):
            return Response(
                {
                    "error": "method_not_allowed",
                    "detail": "PUT /api/v1/empresas/{id}/ solo está permitido para usuarios ADMIN/STAFF. Use PATCH /api/v1/core/empresa/ desde la UI."
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        # ⚠️ Zero Trust: Validar que existe empresa en el tenant
        empresa = self.get_queryset().first()
        
        # Validar datos con serializer
        serializer = self.get_serializer(
            empresa,
            data=request.data,
            partial=False,
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        
        # ⚠️ Service Layer: Usar servicio para actualizar o crear
        from apps.tenant.empresa.services import actualizar_empresa, crear_empresa
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
        ⚠️ v2.60: Actualiza parcialmente la empresa del tenant (singleton) usando Service Layer.
        
        Endpoint: PATCH /api/v1/empresas/{id}/
        
        ⚠️ ENFORCED MODE: Solo STAFF/ADMIN pueden actualizar. No-staff recibe 405.
        ⚠️ Service Layer: Usa services.actualizar_empresa() para lógica de negocio.
        ⚠️ UI: La UI debe usar SOLO PATCH /api/v1/core/empresa/ (Core Orchestrator).
        """
        # ⚠️ ENFORCED: Verificar permisos antes de procesar
        if not self._check_enforced_mode(request):
            return Response(
                {
                    "error": "method_not_allowed",
                    "detail": "PATCH solo está permitido para usuarios ADMIN/STAFF."
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        # ⚠️ Zero Trust: Validar si existe la empresa
        empresa = self.get_queryset().first()
        
        # Validar datos con serializer
        serializer = self.get_serializer(
            empresa,
            data=request.data,
            partial=True,
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        
        from apps.tenant.empresa.services import actualizar_empresa, crear_empresa
        
        try:
            if empresa:
                empresa_result = actualizar_empresa(serializer.validated_data)
                return Response(EmpresaDetailSerializer(empresa_result, context=self.get_serializer_context()).data)
            else:
                empresa_result = crear_empresa(serializer.validated_data)
                return Response(EmpresaDetailSerializer(empresa_result, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'detail': f'Error al procesar la solicitud: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # ⚠️ Zero Trust: Validar que existe empresa en el tenant
        empresa = self.get_queryset().first()
        
        if not empresa:
            return Response(
                {'detail': 'No existe empresa para actualizar.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validar datos con serializer
        serializer = self.get_serializer(
            empresa,
            data=request.data,
            partial=True,
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        
        # ⚠️ Service Layer: Usar servicio para actualizar o crear
        from apps.tenant.empresa.services import actualizar_empresa
        empresa_actualizada = actualizar_empresa(serializer.validated_data)
        
        return Response(
            EmpresaDetailSerializer(empresa_actualizada, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK
        )
    
    @transaction.atomic
    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        """
        ⚠️ v2.60: Actualiza parcialmente la empresa del tenant (singleton) usando Service Layer.
        
        Endpoint: PATCH /api/v1/empresas/{id}/
        
        ⚠️ ENFORCED MODE: Solo STAFF/ADMIN pueden actualizar. No-staff recibe 405.
        ⚠️ Service Layer: Usa services.actualizar_empresa() para lógica de negocio.
        ⚠️ UI: La UI debe usar SOLO PATCH /api/v1/core/empresa/ (Core Orchestrator).
        """
        # ⚠️ ENFORCED: Verificar permisos antes de procesar
        if not self._check_enforced_mode(request):
            return Response(
                {
                    "error": "method_not_allowed",
                    "detail": "PATCH solo está permitido para usuarios ADMIN/STAFF."
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        # ⚠️ Zero Trust: Validar si existe la empresa
        empresa = self.get_queryset().first()
        
        # Validar datos con serializer
        serializer = self.get_serializer(
            empresa,
            data=request.data,
            partial=True,
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        
        from apps.tenant.empresa.services import actualizar_empresa, crear_empresa
        
        try:
            if empresa:
                empresa_result = actualizar_empresa(serializer.validated_data)
                return Response(EmpresaDetailSerializer(empresa_result, context=self.get_serializer_context()).data)
            else:
                empresa_result = crear_empresa(serializer.validated_data)
                return Response(EmpresaDetailSerializer(empresa_result, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'detail': f'Error al procesar la solicitud: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # ⚠️ Zero Trust: Validar que existe empresa en el tenant
        empresa = self.get_queryset().first()
        
        # Validar datos con serializer
        serializer = self.get_serializer(
            empresa,
            data=request.data,
            partial=True,
            context=self.get_serializer_context()
        )
        if not serializer.is_valid():
            log.error(f"[EmpresaViewSet.partial_update] Errores de validación: {serializer.errors}")
            raise serializers.ValidationError(serializer.errors)
        
        serializer.is_valid(raise_exception=True)
        
        # ⚠️ Service Layer: Usar servicio para actualizar
        from apps.tenant.empresa.services import actualizar_empresa
        empresa_actualizada = actualizar_empresa(serializer.validated_data)
        
        return Response(
            EmpresaDetailSerializer(empresa_actualizada, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK
        )
    
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """
        Elimina la empresa del tenant.
        
        Endpoint: DELETE /api/v1/empresas/{id}/
        
        ⚠️ ENFORCED MODE: Solo STAFF/ADMIN pueden eliminar. No-staff recibe 405.
        ⚠️ ADVERTENCIA: Eliminar la empresa puede afectar otras funcionalidades.
        """
        # ⚠️ ENFORCED: Verificar permisos antes de procesar
        if not self._check_enforced_mode(request):
            return Response(
                {
                    "error": "method_not_allowed",
                    "detail": "DELETE /api/v1/empresas/{id}/ solo está permitido para usuarios ADMIN/STAFF."
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        empresa = self.get_queryset().first()
        
        if not empresa:
            return Response(
                {'detail': 'No existe una empresa para eliminar.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        empresa.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MailInboxConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet para configuraciones de buzones de correo (SSoT).
    
    ⚠️ v2.40: Configuración moderna con Tabulator Factory y lazy loading.
    ⚠️ SSoT: Toda gestión de cuentas de correo se hace aquí.
    ⚠️ API-First: JSON-first (JSONParser principal + FormParser legacy).
    ⚠️ SEGURIDAD: Passwords nunca expuestos, cifrado automático.
    ⚠️ PERMISOS: IsTenantAdminOrReadOnly (lectura para autenticados, escritura para ADMIN/STAFF).
    """
    queryset = MailInboxConfig.objects.all()  # ⚠️ CRÍTICO: DRF requiere queryset de clase
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser]  # FormParser legacy
    renderer_classes = [JSONRenderer]
    pagination_class = StandardResultsSetPagination
    
    # ⚠️ CRÍTICO: Asegurar que los métodos HTTP estén permitidos explícitamente
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace']
    
    def get_serializer_class(self):
        """
        Selecciona el serializer según la acción.
        
        ⚠️ v2.37: Alineado con norma de exposición de datos.
        - list: MailInboxConfigListSerializer (campos mínimos)
        - retrieve/create/update: MailInboxConfigDetailSerializer (campos extendidos, sin secretos)
        """
        if self.action == 'list':
            return MailInboxConfigListSerializer
        return MailInboxConfigDetailSerializer
    
    @action(detail=False, methods=["post"], url_path="deprecated-create")
    def deprecated_create(self, request: Request, *args, **kwargs) -> Response:
        """
        ⚠️ DEPRECATED v2.40: Esta ruta está deprecada.
        
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
        
        ⚠️ v2.40: Alineado con Service Layer Pattern.
        ⚠️ v2.40: Soporta filtrado por ?search= para Tabulator.
        ⚠️ AISLAMIENTO: django-tenants maneja automáticamente el aislamiento por esquema.
        No es necesario filtrar manualmente por tenant, el QuerySet base ya está filtrado.
        """
        from django.db.models import Q
        
        # ⚠️ AISLAMIENTO: MailInboxConfig.objects ya está filtrado por tenant automáticamente
        # django-tenants aplica el filtro por esquema en el QuerySet base
        base_qs = MailInboxConfig.objects.all()
        
        # Obtener parámetro de búsqueda
        search = self.request.query_params.get('search', None)
        
        if self.action == 'list':
            qs = base_qs.only(
                'id', 'nombre', 'email_address', 'provider', 'protocol',
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
            # ⚠️ ZERO WASTE: Solo cargar campos necesarios para detalle
            # ⚠️ AISLAMIENTO: django-tenants ya aplica el filtro por esquema automáticamente
            return base_qs.only(
                'id', 'nombre', 'email_address', 'provider', 'protocol', 'is_active',
                'imap_host', 'imap_port', 'imap_username', 'imap_ssl', 'imap_starttls',
                'imap_mailbox', 'imap_mark_as_seen', 'imap_max_attachment_mb', 'imap_move_processed_to',
                'created_at', 'updated_at'
            )
        else:
            # ⚠️ Para otras acciones (create, update, delete, render_offcanvas, etc.), retornar QuerySet completo
            # ⚠️ AISLAMIENTO: django-tenants ya aplica el filtro por esquema automáticamente
            return base_qs
    
    def list(self, request: Request, *args, **kwargs) -> Response:
        """
        Lista configuraciones de buzones (paginado, campos mínimos, Tabulator v2.40).
        
        Endpoint: GET /api/v1/empresas/mail-inbox-config/
        
        ⚠️ NORMA DE EXPOSICIÓN: Solo campos operativos, sin secretos.
        ⚠️ v2.40: SIEMPRE retorna formato paginado para consistencia con Tabulator Factory.
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Filtros opcionales
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        provider = request.query_params.get('provider')
        if provider:
            queryset = queryset.filter(provider=provider)
        
        # ⚠️ v2.40: SIEMPRE usar paginación para consistencia con Tabulator Factory
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
        
        ⚠️ v2.40: Alineado con arquitectura API-First.
        ⚠️ SEGURIDAD: Passwords nunca expuestos (serializer write_only).
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
        
        ⚠️ ENFORCED: Solo STAFF/ADMIN pueden crear/editar/eliminar.
        No-staff recibe 405 Method Not Allowed.
        
        Returns:
            tuple: (ok: bool, reason: str | None)
        """
        from rest_framework.permissions import SAFE_METHODS
        from apps.tenant.empresa.permissions import IsTenantAdmin
        
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
        
        ⚠️ v2.60: HABILITADO - Permite creación directa de configuraciones de buzón.
        ⚠️ v2.40: ENFORCED MODE - Solo STAFF/ADMIN.
        ⚠️ v2.40: Alineado con arquitectura API-First.
        """
        # ⚠️ v2.60: Verificar permisos de escritura (ENFORCED MODE)
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
        
        ⚠️ v2.40: ENFORCED MODE - Solo STAFF/ADMIN.
        ⚠️ v2.40: Alineado con arquitectura API-First.
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
        
        ⚠️ v2.40: ENFORCED MODE - Solo STAFF/ADMIN.
        ⚠️ v2.40: Alineado con arquitectura API-First.
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
        
        ⚠️ v2.40: ENFORCED MODE - Solo STAFF/ADMIN.
        ⚠️ v2.40: Alineado con arquitectura API-First.
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            log_mailinbox.warning(f"[MailInboxConfigViewSet.destroy] 405: {reason}")
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        instance = self.get_object()
        self.perform_destroy(instance)
        log_mailinbox.info(f"[MailInboxConfigViewSet.destroy] Configuración eliminada: {instance.id}")
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    # ⚠️ DEPRECATED v2.40: Método datatables() eliminado - usar GET /api/v1/empresas/mail-inbox-config/ con StandardResultsSetPagination
    
    @action(detail=False, methods=['get'], url_path='render-offcanvas', url_name='render-offcanvas')
    def render_offcanvas(self, request: Request, *args, **kwargs) -> Response:
        """
        Renderiza el offcanvas para crear/editar configuración de buzón (HTMX).
        
        Endpoint: GET /api/v1/empresas/mail-inbox-config/render-offcanvas/?id={id}
        
        ⚠️ v2.60: HTMX-Driven - Retorna HTML partial para cargar en offcanvas.
        - Si se proporciona ?id={id}, carga datos existentes (edición)
        - Si no se proporciona id, muestra formulario vacío (creación)
        
        ⚠️ AISLAMIENTO: django-tenants maneja automáticamente el aislamiento por esquema.
        ⚠️ ZERO WASTE: Solo carga campos necesarios para el formulario.
        ⚠️ MANEJO DE ERRORES: Retorna HTML con error_handler.html incluido para mostrar errores.
        """
        import logging
        from django.template.loader import render_to_string
        from django.template.exceptions import TemplateDoesNotExist
        
        logger = logging.getLogger(__name__)
        
        config_id = request.query_params.get('id')
        instance = None
        error_message = None
        
        # ⚠️ AISLAMIENTO: get_queryset() ya aplica el filtro automático de django-tenants
        # No es necesario filtrar manualmente por tenant, django-tenants lo maneja por esquema
        if config_id:
            try:
                # ⚠️ AISLAMIENTO: Usar QuerySet base directamente (django-tenants ya filtra por esquema)
                # ⚠️ ZERO WASTE: Solo cargar campos necesarios para el formulario
                # ⚠️ IMPORTANTE: No usar self.get_queryset() aquí porque puede no estar configurado para render_offcanvas
                base_qs = MailInboxConfig.objects.all()
                instance = base_qs.only(
                    'id', 'nombre', 'email_address', 'provider', 'is_active',
                    'imap_host', 'imap_port', 'imap_username', 'imap_ssl', 'imap_starttls',
                    'imap_mailbox', 'imap_mark_as_seen', 'imap_max_attachment_mb', 'imap_move_processed_to'
                ).get(id=config_id)
                logger.debug(f"[render_offcanvas] Configuración {config_id} cargada exitosamente")
            except MailInboxConfig.DoesNotExist:
                # ⚠️ MANEJO GRACIAL: Si no existe, simplemente no cargar datos (modo creación)
                logger.warning(f"[render_offcanvas] Configuración con ID {config_id} no encontrada para este tenant")
                error_message = f"La configuración con ID {config_id} no existe o no pertenece a este tenant."
            except Exception as e:
                # ⚠️ MANEJO DE ERRORES: Capturar cualquier error inesperado
                logger.error(f"[render_offcanvas] Error al obtener configuración: {str(e)}", exc_info=True)
                error_message = f"Error al cargar la configuración: {str(e)}"
        
        context = {
            'config': instance,
            'is_edit': instance is not None,
            'error_message': error_message,  # ⚠️ Pasar error al template para mostrar en error_handler.html
        }
        
        try:
            # ⚠️ RUTA CORRECTA: Verificar que el template esté en la ruta correcta
            logger.debug(f"[render_offcanvas] Renderizando template con contexto: config={instance is not None if instance else False}, error_message={error_message}")
            html = render_to_string(
                'tenant/core/empresa/offcanvas_mailinbox.html',
                context,
                request=request
            )
            logger.debug(f"[render_offcanvas] Template renderizado exitosamente, tamaño: {len(html)} caracteres")
            # ⚠️ IMPORTANTE: Retornar HTML directamente sin TemplateHTMLRenderer
            # TemplateHTMLRenderer requiere template_name en la respuesta, pero nosotros ya renderizamos el HTML
            from django.http import HttpResponse
            return HttpResponse(html, content_type='text/html')
        except TemplateDoesNotExist as e:
            # ⚠️ ERROR DE TEMPLATE: Si el template no existe, retornar error estructurado con error_handler
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
            from django.http import HttpResponse
            return HttpResponse(error_html, content_type='text/html', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            # ⚠️ ERROR GENERAL: Capturar cualquier error inesperado en el renderizado
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
            from django.http import HttpResponse
            return HttpResponse(error_html, content_type='text/html', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='test-connection', url_name='test-connection')
    def test_connection(self, request: Request) -> Response:
        """
        Prueba conexión a buzón de correo sin persistir datos.
        
        Endpoint: POST /api/v1/empresas/mail-inbox-config/test-connection/
        
        ⚠️ v2.40: Alineado con arquitectura Service Layer y SSoT.
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
            from apps.services.maildigester.connection_test import maildigester_test_connection
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


# ========= Vistas auxiliares (funciones) =========

@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([permissions.IsAuthenticated, IsTenantMember])
def form_metadata(request):
    """
    Endpoint para obtener metadata del formulario de empresa.
    
    Endpoint: GET /api/v1/empresa/form-metadata/
    
    Retorna todas las opciones necesarias para poblar selects del frontend:
    - Tipos de contribuyente (clases y segmentos)
    - Regímenes de renta
    - Responsabilidades RUT
    
    ⚠️ AUTONOMÍA: Usa choices locales desde apps/tenant/empresa/choices/
    """
    try:
        from apps.tenant.empresa.choices.regimen import get_regimen_choices
        from apps.tenant.empresa.choices.segmento_dian import get_segmento_dian_choices
        from apps.tenant.empresa.choices.responsabilidad_rut import get_responsabilidad_rut_choices
        
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
@authentication_classes([SessionAuthentication])
@permission_classes([permissions.IsAuthenticated, IsTenantMember])
def actividades_lookup(request):
    """
    Endpoint para búsqueda de actividades económicas (CIIU).
    
    Endpoint: GET /api/v1/empresa/actividades-lookup/?q=&limit=
    
    Parámetros:
        - q: Query de búsqueda (código)
        - limit: Límite de resultados (default: 10)
    
    ⚠️ AUTONOMÍA: CIIU es texto libre. Este endpoint retorna lista vacía.
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
