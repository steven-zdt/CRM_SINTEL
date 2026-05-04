"""
ViewSet para Clientes v2.61.4 - Tabulator Implementation + HTMX Offcanvas

# WARNING: API-First: Endpoints RESTful para consumo desde Tabulator (Vanilla JS)
# WARNING: SSoT: Empresa se inyecta automáticamente desde el tenant
# WARNING: v2.61.4: Renderizado robusto con render_template_safe() para HTMX
# WARNING: v2.61.4: Caching de empresa con cached_property para optimización
"""
import logging
from django.db.utils import ProgrammingError
from django.db.models import Prefetch
from django.utils.functional import cached_property
from rest_framework import status, serializers, filters
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from django_filters.rest_framework import DjangoFilterBackend

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantMember, IsTenantAdminOrReadOnly
from apps.tenant.api.utils import render_template_safe, resolve_tenant_empresa
from .mixins import ClienteServiceMixin, ContactoClienteServiceMixin
from apps.tenant.clientes.api.serializers import (
    ClienteDetailSerializer,
    ClienteListSerializer,
    ContactoClienteSerializer,
)
from apps.tenant.clientes.models import Cliente, ContactoCliente
from apps.tenant.clientes.services.selectors import ClienteSelector, ContactoSelector
from apps.tenant.clientes.services.crud_service import ClienteCRUDService, ContactoCRUDService
from apps.tenant.clientes.services.business_service import ClienteBusinessService
from apps.tenant.empresa.models import Empresa

logger = logging.getLogger(__name__)





class StandardResultsSetPagination(PageNumberPagination):
    """
    # WARNING: v2.40: Paginación estándar para Tabulator.
    Tabulator espera: {count, next, previous, results: [...]}
    """
    page_size = 10  # Default: 10 (estándar SaaS)
    page_size_query_param = 'page_size'
    max_page_size = 100


class ClienteViewSet(ClienteServiceMixin, ContactoClienteServiceMixin, BaseTenantViewSet):
    """
    # WARNING: v2.60: ViewSet para Clientes con soporte Tabulator y HTMX Offcanvas.
    
    Endpoints:
    - GET /api/v1/clientes/ - Lista paginada (Tabulator)
    - GET /api/v1/clientes/{id}/ - Detalle
    - POST /api/v1/clientes/ - Crear
    - PUT /api/v1/clientes/{id}/ - Actualizar completo
    - PATCH /api/v1/clientes/{id}/ - Actualizar parcial
    - DELETE /api/v1/clientes/{id}/ - Eliminar
    - GET /api/v1/clientes/offcanvas/ - Renderizar HTML del Offcanvas (HTMX)
    """
    # # WARNING: CRÍTICO: DRF necesita un queryset definido para generar las rutas del router
    # Usamos .none() como base porque el filtrado real se hace en get_queryset() o en los métodos
    queryset = Cliente.objects.none()
    serializer_class = ClienteDetailSerializer  # # WARNING: CRITICO: DRF necesita serializer_class para generar rutas
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activo']
    search_fields = ['razon_social', 'numero_documento', 'email']
    ordering_fields = ['razon_social', 'created_at']

    def get_object(self):
        """
        # [SSoT] Double Semantic Verification (DSV)
        Validates that the object exists AND belongs to the tenant.
        """
        pk = self.kwargs.get(self.lookup_url_kwarg)
        empresa = self.get_empresa()
        if not empresa:
            raise NotFound("Empresa no detectada en el contexto del tenant.")
            
        obj = Cliente.objects.filter(pk=pk, empresa_id=empresa.id).first()
        if not obj:
            logger.warning(f"[clientes:DSV] IDOR Intent or Missing Record: ID {pk} for Empresa {empresa.id}")
            raise NotFound(f"Cliente con ID {pk} no encontrado en su organizacion.")
        return obj

    def get_queryset(self):
        empresa = self.get_empresa()
        if not empresa:
            return Cliente.objects.none()

        contactos_qs = ContactoCliente.objects.filter(is_principal=True).only('id', 'cliente_id', 'nombre_completo', 'email')
        prefetch = Prefetch('contactos', queryset=contactos_qs, to_attr='contactos_prefetched')

        return Cliente.objects.filter(empresa_id=empresa.id).only(
            'id',
            'empresa_id',
            'tipo_persona',
            'tipo_documento',
            'numero_documento',
            'razon_social',
            'nombre_comercial',
            'regimen_tributario',
            'email',
            'telefono',
            'direccion',
            'ciudad',
            'activo',
            'observaciones'
        ).prefetch_related(prefetch)

    @cached_property
    def tenant_empresa(self):
        """Cached tenant empresa resolved once per request lifecycle."""
        request = getattr(self, 'request', None)
        if request is None:
            return None
        return resolve_tenant_empresa(request, self)

    def get_empresa(self):
        """
        # WARNING: v2.61.4: Obtiene empresa con fallback robusto.

        Orden de resolución:
        1) BaseTenantViewSet.tenant_empresa (si está disponible)
        2) request.tenant.empresa (inyectado por middleware)
        3) request.tenant_empresa (compatibilidad)
        4) Empresa singleton del esquema tenant
        """
        return self.tenant_empresa

    def list(self, request):
        """
        Endpoint para Tabulator (GET /api/v1/clientes/).
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response({'count': 0, 'results': []})
            
        search = request.query_params.get('search', '').strip()
        queryset = self.cliente_selector.get_cliente_list(empresa.id, search if search else None)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = ClienteListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ClienteListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def get_serializer_context(self):
        """
        # WARNING: v2.61.4: Agregar empresa_id al contexto del serializer.
        
        Esto permite que los serializers accedan a empresa_id en sus validaciones.
        Usado por ClienteDetailSerializer para validar uniqueness de documento.
        """
        context = super().get_serializer_context()
        try:
            empresa = self.get_empresa()
            if empresa:
                context['empresa_id'] = empresa.id
        except Exception:
            # Si hay error obteniendo empresa, ignorar (será capturado después)
            pass
        return context

    # _sync_contactos removed. Logic moved to business_service.py

    def create(self, request, *args, **kwargs):
        empresa = self.get_empresa()
        if not empresa:
            return Response({'detail': 'Configure la empresa antes de crear clientes.'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ClienteDetailSerializer(data=request.data, context=self.get_serializer_context())
        if serializer.is_valid():
            contactos_raw = request.data.get('contactos')
            try:
                cliente = self.cliente_service.registrar_cliente_completo(
                    empresa_id=empresa.id, 
                    data=serializer.validated_data, 
                    contactos_raw=contactos_raw
                )
                data = ClienteDetailSerializer(cliente, context=self.get_serializer_context()).data
                data['redirect'] = '/workspace/#clientes'
                return Response(data, status=status.HTTP_201_CREATED)
            except serializers.ValidationError as e:
                return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        cliente = self.get_object() # DSV applied here
        serializer = ClienteDetailSerializer(
            cliente, 
            data=request.data, 
            partial=False,
            context=self.get_serializer_context()
        )
        if serializer.is_valid():
            try:
                contactos_raw = request.data.get('contactos')
                cliente = self.cliente_service.registrar_cliente_completo(
                    empresa_id=cliente.empresa_id,
                    data=serializer.validated_data,
                    contactos_raw=contactos_raw,
                    cliente_instance=cliente
                )
            except serializers.ValidationError as e:
                return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
            data = ClienteDetailSerializer(cliente, context=self.get_serializer_context()).data
            data['redirect'] = '/workspace/#clientes'
            return Response(data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        cliente = self.get_object() # DSV
        serializer = ClienteDetailSerializer(
            cliente, 
            data=request.data, 
            partial=True,
            context=self.get_serializer_context()
        )
        
        if serializer.is_valid():
            try:
                contactos_raw = request.data.get('contactos')
                cliente = self.cliente_service.registrar_cliente_completo(
                    empresa_id=cliente.empresa_id,
                    data=serializer.validated_data,
                    contactos_raw=contactos_raw,
                    cliente_instance=cliente
                )
            except serializers.ValidationError as e:
                return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
            data = ClienteDetailSerializer(cliente, context=self.get_serializer_context()).data
            data['redirect'] = '/workspace/#clientes'
            return Response(data)
        
        logger.error(f'[ClienteViewSet.partial_update] Errores de validación: {serializer.errors}')
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """
        [Zero Trust] DSV via get_object and delegation to CRUD service.
        """
        cliente = self.get_object()
        try:
            self.cliente_crud.delete_cliente(cliente)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False, 
        methods=['get'], 
        renderer_classes=[TemplateHTMLRenderer, JSONRenderer],
        url_path='offcanvas'
    )
    def offcanvas(self, request):
        """
        # WARNING: v2.61.4: Devuelve el HTML del Offcanvas para crear o editar un cliente (vía HTMX).
        
        Renderizado robusto con render_template_safe() para manejar:
        - Template no encontrado
        - Errores de filesystem (OSError, PermissionError)
        
        Query params:
        - id: ID del cliente para edición (opcional)
        
        Returns:
            Template HTML renderizado con contexto del cliente (si existe) y sus contactos
            O JSON con error amigable si falla
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response(
                {'error': 'empresa_not_found', 'message': 'Empresa no configurada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        context = {
            'empresa': empresa,
            'cliente': None,
            'contactos': [],
            'modo': 'crear'
        }
        template_name = 'tenant/clientes/offcanvas_crear_cliente.html'
        
        cliente_id = request.query_params.get('id')
        
        if cliente_id:
            try:
                cliente = self.get_object()
                context['cliente'] = cliente
                context['modo'] = 'editar'
                
                contactos = self.contacto_selector.get_contacto_list(empresa_id=empresa.id, cliente_id=cliente.id)
                context['contactos'] = contactos
                template_name = 'tenant/clientes/offcanvas_editar_cliente.html'
            except (Cliente.DoesNotExist, NotFound):
                logger.warning(f'[offcanvas] Cliente {cliente_id} no encontrado o IDOR')
                return Response(
                    {'error': 'cliente_not_found', 'detail': f'Cliente {cliente_id} no existe'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        context['is_draft'] = context['modo'] == 'crear'

        # # WARNING: v2.61.4: Usar wrapper seguro para renderizado
        return render_template_safe(
            context, 
            template_name,
            request=request
        )
    
    @action(
        detail=False, 
        methods=['get'], 
        renderer_classes=[TemplateHTMLRenderer, JSONRenderer],
        url_path='render-offcanvas/crear'
    )
    def render_offcanvas_crear(self, request):
        """
        # WARNING: v2.61.4: Endpoint HTMX RESTful para cargar offcanvas de creación de clientes.
        
        # WARNING: v2.61.4: Renderizado robusto con render_template_safe()
        
        GET /api/v1/clientes/render-offcanvas/crear/
        
        Returns:
            Template HTML: clientes/offcanvas_crear_cliente.html
            O JSON con error si template no se encuentra o hay error de lectura
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response(
                {'error': 'empresa_not_found', 'message': 'Empresa no configurada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        context = {
            'empresa': empresa,
            'cliente': None,
            'contactos': [],
            'is_draft': True,
            'modo': 'crear'
        }
        
        # # WARNING: v2.61.4: Usar wrapper seguro
        return render_template_safe(
            context,
            'tenant/clientes/offcanvas_crear_cliente.html',
            request=request
        )
    
    @action(
        detail=True, 
        methods=['get'], 
        renderer_classes=[TemplateHTMLRenderer, JSONRenderer],
        url_path='render-offcanvas/editar'
    )
    def render_offcanvas_editar(self, request, id=None):
        """
        # WARNING: v2.61.4: Endpoint HTMX RESTful para cargar offcanvas de edición de clientes.
        
        # WARNING: v2.61.4: Renderizado robusto con render_template_safe()
        
        GET /api/v1/clientes/{id}/render-offcanvas/editar/
        
        Returns:
            Template HTML: clientes/offcanvas_editar_cliente.html
            O JSON con error si template no se encuentra o hay error de lectura
        """
        cliente = self.get_object() # DSV auto filters by tenant
        if cliente is None:
            return Response(
                {'error': 'cliente_not_found', 'detail': f'Cliente {id} no existe en este tenant'},
                status=status.HTTP_404_NOT_FOUND,
            )
        # PERFORMANCE BIBLE: Cargar contactos con .only()
        contactos = self.contacto_selector.get_contacto_list(empresa_id=cliente.empresa_id, cliente_id=cliente.id)
        context = {
            'cliente': cliente,
            'contactos': contactos,
            'is_draft': False,
            'modo': 'editar',
        }
        return render_template_safe(
            context,
            'tenant/clientes/offcanvas_editar_cliente.html',
            request=request,
        )
    
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request, id=None):
        """
        # WARNING: v2.61: Endpoint HTMX RESTful para cargar offcanvas de detalle de clientes (read-only).

        GET /api/v1/clientes/{id}/render-offcanvas/detalle/

        Returns:
            Template HTML: clientes/offcanvas_detalle_cliente.html
        """
        cliente = self.get_object()

        # # WARNING: PERFORMANCE BIBLE: Cargar contactos con .only()
        contactos = self.contacto_selector.get_contacto_list(empresa_id=cliente.empresa_id, cliente_id=cliente.id)

        context = {
            'cliente': cliente,
            'contactos': contactos,
            'modo': 'detalle'
        }

        # # WARNING: v2.61.4: Usar wrapper seguro para TemplateHTMLRenderer
        return render_template_safe(
            context,
            'tenant/clientes/offcanvas_detalle_cliente.html',
            request=request
        )


class ContactoClienteViewSet(ContactoClienteServiceMixin, BaseTenantViewSet):
    """
    # WARNING: v2.60: ViewSet para Contactos de Cliente con Zero Trust estricto.
    """
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
    
    queryset = ContactoCliente.objects.none()
    serializer_class = ContactoClienteSerializer
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre_completo', 'email', 'telefono', 'cargo', 'cliente__razon_social']

    def get_object(self):
        """DSV for Contacto."""
        pk = self.kwargs.get(self.lookup_url_kwarg)
        empresa = self.get_empresa()
        obj = ContactoCliente.objects.filter(pk=pk, empresa_id=empresa.id).first()
        if not obj:
            raise NotFound("Contacto no encontrado.")
        return obj

    # ... rest of ContactoClienteViewSet truncated for multi-replace ...
    
    # # WARNING: v2.61: Restringir métodos HTTP según requerimiento
    http_method_names = ['get', 'post', 'patch', 'delete']
    
    def list(self, request, *args, **kwargs):
        """
        Lista paginada de contactos.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        empresa = self.get_empresa()
        if not empresa:
            return ContactoCliente.objects.none()

        queryset = self.contacto_selector.get_contacto_list(empresa_id=empresa.id)

        cliente_id = self.request.query_params.get('cliente')
        if cliente_id:
            try:
                queryset = queryset.filter(cliente_id=int(cliente_id))
            except ValueError:
                queryset = queryset.none()
        
        return queryset
    
    def get_empresa(self):
        """
        # WARNING: v2.60: Zero Trust - Obtiene la empresa del usuario.
        """
        return resolve_tenant_empresa(self.request, self)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            empresa = self.get_empresa()
            if empresa:
                context['empresa_id'] = empresa.id
        except Exception:
            pass
        return context

    def create(self, request, *args, **kwargs):
        empresa = self.get_empresa()
        if not empresa:
            return Response(
                {'detail': 'Configure la empresa antes de crear contactos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        contacto = self.contacto_crud.create_contacto(empresa.id, serializer.validated_data)
        output = self.get_serializer(contacto, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        contacto = self.get_object() # DSV
        serializer = self.get_serializer(contacto, data=request.data, partial=True, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        contacto = self.contacto_crud.update_contacto(contacto, serializer.validated_data)
        output = self.get_serializer(contacto, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """DSV + Delegate deletion."""
        contacto = self.get_object()
        self.contacto_crud.delete_contacto(contacto)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        # WARNING: v2.60: Devuelve el HTML del gestor de contactos (vía HTMX).
        """
        empresa = self.get_empresa()
        cliente = None
        contactos = []
        
        cliente_id = request.query_params.get('cliente_id')
        if cliente_id:
            cliente = (
                Cliente.objects.filter(empresa_id=empresa.id, id=cliente_id)
                .only('id', 'empresa_id', 'razon_social')
                .first()
            )
            if not cliente:
                return Response(
                    {'error': 'cliente_not_found', 'detail': 'Cliente no encontrado'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            contactos = self.contacto_selector.get_contacto_list(empresa_id=empresa.id, cliente_id=cliente.id)
        else:
            cliente = Cliente(
                id=None,
                razon_social='Seleccionar Cliente',
                empresa=empresa
            )
        
        context = {
            'cliente': cliente,
            'contactos': contactos
        }
        
        # # WARNING: v2.61.4: Usar wrapper seguro para TemplateHTMLRenderer
        return render_template_safe(
            context,
            'tenant/clientes/contactos_offcanvas.html',
            request=request
        )

    @action(
        detail=False, 
        methods=['get'], 
        renderer_classes=[TemplateHTMLRenderer, JSONRenderer],
        url_path='render-offcanvas/crear'
    )
    def render_offcanvas_crear(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de creación de contacto.
        GET /api/v1/clientes/contactos/render-offcanvas/crear/
        
        Parámetro opcional:
        - cliente_id: Pre-rellenar cliente (ocultar selector de cliente)
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response(
                {'error': 'empresa_not_found', 'message': 'Empresa no configurada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cliente_id = request.query_params.get('cliente_id')
        context = {}
        
        if cliente_id:
            try:
                cliente = Cliente.objects.filter(
                    empresa_id=empresa.id, 
                    id=int(cliente_id)
                ).only('id', 'empresa_id', 'razon_social').first()
                if cliente:
                    context['cliente'] = cliente
            except (ValueError, TypeError):
                pass

        return render_template_safe(
            context,
            'tenant/contactos/offcanvas_crear_contacto_cliente.html',
            request=request
        )

    @action(
        detail=True, 
        methods=['get'], 
        renderer_classes=[TemplateHTMLRenderer, JSONRenderer],
        url_path='render-offcanvas/editar'
    )
    def render_offcanvas_editar(self, request, id=None):
        """
        Endpoint HTMX RESTful para cargar offcanvas de edición de contacto.
        GET /api/v1/clientes/contactos/{id}/render-offcanvas/editar/
        """
        try:
            contacto = self.get_object()
        except ContactoCliente.DoesNotExist:
            return Response(
                {'error': 'contacto_not_found', 'detail': f'Contacto {id} no existe'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        context = {
            'contacto': contacto
        }
        
        return render_template_safe(
            context,
            'tenant/contactos/offcanvas_editar_contacto_cliente.html',
            request=request
        )

    @action(
        detail=True, 
        methods=['get'], 
        renderer_classes=[TemplateHTMLRenderer, JSONRenderer],
        url_path='render-offcanvas/detalle'
    )
    def render_offcanvas_detalle(self, request, id=None):
        """
        Endpoint HTMX RESTful para cargar offcanvas de detalle (read-only).
        GET /api/v1/clientes/contactos/{id}/render-offcanvas/detalle/
        """
        from rest_framework.exceptions import NotFound
        
        try:
            contacto = self.get_object()
        except Exception:
            raise NotFound('Contacto no encontrado')
        
        context = {
            'contacto': contacto
        }
        
        return render_template_safe(
            context,
            'tenant/contactos/offcanvas_detalle_contacto_cliente.html',
            request=request
        )
