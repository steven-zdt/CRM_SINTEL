"""
ViewSet para Clientes - Tabulator Implementation + HTMX Offcanvas
"""
import logging
from django.db.utils import ProgrammingError
from django.db.models import Prefetch
from django.utils.functional import cached_property
from rest_framework import status, serializers, filters
from rest_framework.decorators import action
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from django_filters.rest_framework import DjangoFilterBackend

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantMember, IsTenantAdminOrReadOnly
from apps.tenant.api.utils import render_template_safe, resolve_tenant_empresa
from apps.tenant.core.services.organizational_context import OrganizationalContextMixin
from apps.tenant.clientes.services.api_mixins import ClienteServiceMixin, ContactoClienteServiceMixin, CarteraServiceMixin
from apps.tenant.clientes.api.serializers import (
    ClienteDetailSerializer,
    ClienteListSerializer,
    ContactoClienteSerializer,
    CarteraListSerializer,
    CarteraDetailSerializer,
    CarteraAbonoSerializer,
    FacturaCxCListSerializer,
)
from apps.tenant.clientes.models import Cliente, ContactoCliente, Cartera
from apps.tenant.clientes.services.selectors import ClienteSelector, ContactoSelector, CarteraSelector
from apps.tenant.clientes.services.crud_service import ClienteCRUDService, ContactoCRUDService, CarteraCRUDService
from apps.tenant.clientes.services.business_service import ClienteBusinessService, CarteraBusinessService
from apps.tenant.empresa.models import Empresa

logger = logging.getLogger(__name__)


class ClienteViewSet(OrganizationalContextMixin, ClienteServiceMixin, ContactoClienteServiceMixin, CarteraServiceMixin, BaseTenantViewSet):
    """
    ViewSet para Clientes con soporte Tabulator y HTMX Offcanvas.

    Fase 9 (OCF): OrganizationalContextMixin adoptado de forma aditiva.
    get_queryset()/get_object()/etc. no migrados - resuelven la empresa via
    resolve_tenant_empresa() (mismo mecanismo ya documentado en empresa,
    Fase 9 app 1/14), que no exige TenantProfile a diferencia de
    OrganizationalContext.resolve().

    Endpoints:
    - GET /api/v1/clientes/ - Lista paginada (Tabulator)
    - GET /api/v1/clientes/{uuid}/ - Detalle
    - POST /api/v1/clientes/ - Crear
    - PUT /api/v1/clientes/{uuid}/ - Actualizar completo
    - PATCH /api/v1/clientes/{uuid}/ - Actualizar parcial
    - DELETE /api/v1/clientes/{uuid}/ - Eliminar
    - GET /api/v1/clientes/offcanvas/ - Renderizar HTML del Offcanvas (HTMX)
    """
    lookup_field = 'uuid'
    lookup_url_kwarg = 'uuid'
    queryset = Cliente.objects.none()
    serializer_class = ClienteDetailSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activo']
    search_fields = ['razon_social', 'numero_documento', 'email']
    ordering_fields = ['razon_social', 'created_at']

    def get_object(self):
        """
        [SSoT] Double Semantic Verification (DSV)
        Validates that the object exists AND belongs to the tenant by UUID.
        """
        uuid_val = self.kwargs.get(self.lookup_url_kwarg)
        empresa = self.get_empresa()
        if not empresa:
            raise NotFound("Empresa no detectada en el contexto del tenant.")
            
        obj = Cliente.objects.filter(uuid=uuid_val, empresa_id=empresa.id).first()
        if not obj:
            logger.warning(f"[clientes:DSV] IDOR Intent or Missing Record: UUID {uuid_val} for Empresa {empresa.id}")
            raise NotFound(f"Cliente con UUID {uuid_val} no encontrado en su organizacion.")
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
        Obtiene empresa con fallback robusto.

        Orden de resolucion:
        1) BaseTenantViewSet.tenant_empresa (si esta disponible)
        2) request.tenant.empresa (inyectado por middleware)
        3) request.tenant_empresa (compatibilidad)
        4) Empresa singleton del esquema tenant
        """
        return self.tenant_empresa

    def list(self, request):
        """
        Endpoint para Tabulator (GET /api/v1/clientes/).
        Soporta filtros servidor: tipo_persona, es_retenedor, activo, search.
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response({'count': 0, 'results': []})

        search = request.query_params.get('search', '').strip() or None

        filters = {}
        tipo_persona = request.query_params.get('tipo_persona', '').strip()
        if tipo_persona:
            filters['tipo_persona'] = tipo_persona

        es_retenedor_raw = request.query_params.get('es_retenedor', '').strip().lower()
        if es_retenedor_raw in ('true', '1'):
            filters['es_retenedor'] = True

        activo_raw = request.query_params.get('activo', '').strip().lower()
        if activo_raw == 'true':
            filters['activo'] = True
        elif activo_raw == 'false':
            filters['activo'] = False

        queryset = self.cliente_selector.get_cliente_list(empresa.id, search, filters or None)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        rows = page if page is not None else list(queryset)

        # Cartera: una query agrupada para todos los clientes de la pagina
        uuids = [c.uuid for c in rows if c.uuid]
        cartera_map = self.cliente_selector.get_cartera_resumen(empresa.id, uuids)

        ctx = self.get_serializer_context()
        ctx['cartera_map'] = cartera_map

        serializer = ClienteListSerializer(rows, many=True, context=ctx)
        if page is not None:
            return paginator.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='kpis')
    def kpis(self, request):
        """GET /api/v1/clientes/kpis/ — Agregados para los KPI cards (una sola query)."""
        empresa = self.get_empresa()
        if not empresa:
            return Response({'total': 0, 'activos': 0, 'inactivos': 0,
                             'juridicas': 0, 'naturales': 0, 'retenedores': 0})
        data = self.cliente_selector.get_kpis(empresa.id)
        return Response(data)
    
    def get_serializer_context(self):
        """
        Agregar empresa_id al contexto del serializer.
        
        Esto permite que los serializers accedan a empresa_id en sus validaciones.
        Usado por ClienteDetailSerializer para validar uniqueness de documento.
        """
        context = super().get_serializer_context()
        try:
            empresa = self.get_empresa()
            if empresa:
                context['empresa_id'] = empresa.id
        except Exception:
            # Si hay error obteniendo empresa, ignorar (sera capturado despues)
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
                cliente, created = self.cliente_service.registrar_cliente_completo(
                    empresa_id=empresa.id, 
                    data=serializer.validated_data, 
                    contactos_raw=contactos_raw
                )
                data = ClienteDetailSerializer(cliente, context=self.get_serializer_context()).data
                data['redirect'] = '/workspace/#clientes'
                status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
                return Response(data, status=status_code)
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
                cliente, created = self.cliente_service.registrar_cliente_completo(
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
                cliente, created = self.cliente_service.registrar_cliente_completo(
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
        Devuelve el HTML del Offcanvas para crear o editar un cliente (via HTMX).
        
        Renderizado robusto con render_template_safe() para manejar:
        - Template no encontrado
        - Errores de filesystem (OSError, PermissionError)
        
        Query params:
        - id: ID del cliente para edicion (opcional)
        
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
        Endpoint HTMX RESTful para cargar offcanvas de creacion de clientes.
        
        Renderizado robusto con render_template_safe()
        
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
    def render_offcanvas_editar(self, request, uuid=None):
        """
        Endpoint HTMX RESTful para cargar offcanvas de edicion de clientes.
        
        Renderizado robusto con render_template_safe()
        
        GET /api/v1/clientes/{uuid}/render-offcanvas/editar/
        
        Returns:
            Template HTML: clientes/offcanvas_editar_cliente.html
            O JSON con error si template no se encuentra o hay error de lectura
        """
        cliente = self.get_object() # DSV auto filters by tenant
        if cliente is None:
            return Response(
                {'error': 'cliente_not_found', 'detail': f'Cliente {uuid} no existe en este tenant'},
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
    def render_offcanvas_detalle(self, request, uuid=None):
        """
        Endpoint HTMX RESTful para cargar offcanvas de detalle de clientes (read-only).

        GET /api/v1/clientes/{uuid}/render-offcanvas/detalle/

        Returns:
            Template HTML: clientes/offcanvas_detalle_cliente.html
        """
        cliente = self.get_object()

        # PERFORMANCE BIBLE: Cargar contactos con .only()
        contactos = self.contacto_selector.get_contacto_list(empresa_id=cliente.empresa_id, cliente_id=cliente.id)

        context = {
            'cliente': cliente,
            'contactos': contactos,
            'modo': 'detalle'
        }

        return render_template_safe(
            context,
            'tenant/clientes/offcanvas_detalle_cliente.html',
            request=request
        )


class ContactoClienteViewSet(OrganizationalContextMixin, ContactoClienteServiceMixin, BaseTenantViewSet):
    """
    ViewSet para Contactos de Cliente con Zero Trust estricto.

    Fase 9 (OCF): OrganizationalContextMixin adoptado de forma aditiva.
    Misma razon que ClienteViewSet para no migrar get_queryset()/get_object().
    """
    lookup_field = 'uuid'
    lookup_url_kwarg = 'uuid'
    queryset = ContactoCliente.objects.none()
    serializer_class = ContactoClienteSerializer
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre_completo', 'email', 'telefono', 'cargo', 'cliente__razon_social']

    def get_object(self):
        """DSV for Contacto."""
        uuid_val = self.kwargs.get(self.lookup_url_kwarg)
        empresa = self.get_empresa()
        if not empresa:
            raise NotFound("Empresa no detectada en el contexto del tenant.")
            
        obj = ContactoCliente.objects.filter(uuid=uuid_val, empresa_id=empresa.id).first()
        if not obj:
            logger.warning(f"[contactos:DSV] IDOR Intent or Missing Record: UUID {uuid_val} for Empresa {empresa.id}")
            raise NotFound("Contacto no encontrado.")
        return obj

    # ... rest of ContactoClienteViewSet truncated for multi-replace ...
    
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
        Zero Trust - Obtiene la empresa del usuario.
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
        Devuelve el HTML del gestor de contactos (via HTMX).
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
    def render_offcanvas_editar(self, request, uuid=None):
        """
        Endpoint HTMX RESTful para cargar offcanvas de edición de contacto.
        GET /api/v1/clientes/contactos/{uuid}/render-offcanvas/editar/
        """
        try:
            contacto = self.get_object()
        except ContactoCliente.DoesNotExist:
            return Response(
                {'error': 'contacto_not_found', 'detail': f'Contacto {uuid} no existe'},
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
    def render_offcanvas_detalle(self, request, uuid=None):
        """
        Endpoint HTMX RESTful para cargar offcanvas de detalle (read-only).
        GET /api/v1/clientes/contactos/{uuid}/render-offcanvas/detalle/
        """
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



class CarteraViewSet(OrganizationalContextMixin, CarteraServiceMixin, BaseTenantViewSet):
    """
    ViewSet for accounts receivable (Cartera) management.

    Fase 9 (OCF): OrganizationalContextMixin adoptado de forma aditiva.
    Misma razon que ClienteViewSet para no migrar get_queryset()/get_object().
    """
    lookup_field = 'uuid'
    lookup_url_kwarg = 'uuid'
    queryset = Cartera.objects.none()
    serializer_class = CarteraListSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['numero_factura', 'cliente__razon_social']
    ordering_fields = ['fecha_vencimiento', 'created_at']

    def get_object(self):
        """DSV for Cartera."""
        uuid_val = self.kwargs.get(self.lookup_url_kwarg)
        empresa = self.get_empresa()
        if not empresa:
            raise NotFound("Empresa no detectada en el contexto del tenant.")
            
        obj = Cartera.objects.filter(uuid=uuid_val, empresa_id=empresa.id).select_related('cliente').first()
        if not obj:
            logger.warning(f"[cartera:DSV] IDOR Intent or Missing Record: UUID {uuid_val} for Empresa {empresa.id}")
            raise NotFound("Obligacion de cartera no encontrada.")
        return obj

    def get_queryset(self):
        empresa = self.get_empresa()
        if not empresa:
            return Cartera.objects.none()
        return Cartera.objects.filter(empresa_id=empresa.id).select_related('cliente').only(
            'id',
            'uuid',
            'cliente__id',
            'cliente__uuid',
            'cliente__razon_social',
            'cliente__numero_documento',
            'numero_factura',
            'factura_uuid',
            'fecha_emision',
            'fecha_vencimiento',
            'valor_total',
            'valor_pagado',
            'estado_pago',
            'observaciones',
        )

    def get_empresa(self):
        return resolve_tenant_empresa(self.request, self)

    def list(self, request, *args, **kwargs):
        """
        GET /api/v1/clientes/cartera/ — Lista facturas de VENTA (fuente de verdad).
        Patron Pull Model: lee de Factura.naturaleza='VENTA' (AGENTS.md §18).
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response({'count': 0, 'results': []})

        cliente_uuid = request.query_params.get('cliente_uuid') or request.query_params.get('cliente_id')
        estado_pago  = request.query_params.get('estado_pago')
        search       = request.query_params.get('search', '').strip() or None

        qs = CarteraSelector.qs_list_facturas_venta(
            empresa_id=empresa.id,
            cliente_uuid=cliente_uuid,
            estado_pago=estado_pago,
            search=search,
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        rows = page if page is not None else list(qs)

        serializer = FacturaCxCListSerializer(rows, many=True)
        if page is not None:
            return paginator.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='kpis')
    def kpis(self, request):
        """GET /api/v1/clientes/cartera/kpis/ — KPIs sobre Facturas VENTA."""
        empresa = self.get_empresa()
        if not empresa:
            return Response({'pendiente_monto': '0', 'pendiente_count': 0, 'pagado_monto': '0', 'total_count': 0})
        data = CarteraSelector.get_cartera_kpis_facturas_venta(empresa.id)
        return Response(data)

    @action(detail=True, methods=['post'], url_path='registrar-abono')
    def registrar_abono(self, request, uuid=None):
        """
        POST /api/v1/clientes/cartera/{uuid}/registrar-abono/
        """
        cartera = self.get_object()
        from apps.tenant.clientes.api.serializers import CarteraAbonoSerializer
        serializer = CarteraAbonoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        monto = serializer.validated_data['monto']
        try:
            cartera, abono_aplicado = self.cartera_service.registrar_abono(
                empresa_id=cartera.empresa_id,
                cartera_uuid=cartera.uuid,
                monto=monto
            )
            return Response({
                "detail": f"Abono de {abono_aplicado} registrado exitosamente.",
                "saldo": str(cartera.saldo),
                "estado_pago": cartera.estado_pago,
                "valor_pagado": str(cartera.valor_pagado)
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return CarteraDetailSerializer
        return CarteraListSerializer

    def create(self, request, *args, **kwargs):
        """
        POST /api/v1/clientes/cartera/ — Registra nueva obligación de cuentas por cobrar.
        DSV: valida que el cliente pertenezca a la empresa del tenant.
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response({'detail': 'Empresa no configurada.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CarteraDetailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # DSV: verificar que el cliente pertenece a esta empresa
        cliente_id = serializer.validated_data.get('cliente')
        if hasattr(cliente_id, 'pk'):
            cliente_id = cliente_id.pk
        cliente_obj = Cliente.objects.filter(id=cliente_id, empresa_id=empresa.id).only('id', 'uuid', 'empresa_id').first()
        if not cliente_obj:
            raise NotFound("Cliente no encontrado en esta empresa.")

        try:
            cartera, created = self.cartera_service.registrar_cartera(
                empresa_id=empresa.id,
                data={**serializer.validated_data, 'empresa_id': empresa.id},
            )
            out_serializer = CarteraDetailSerializer(cartera)
            http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response(out_serializer.data, status=http_status)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, uuid=None, *args, **kwargs):
        """
        PATCH /api/v1/clientes/cartera/{uuid}/ — Edita campos permitidos.
        Solo se permiten: fecha_vencimiento, observaciones, numero_factura.
        DSV: cartera debe pertenecer a la empresa del tenant.
        """
        cartera = self.get_object()
        ALLOWED = {'fecha_vencimiento', 'observaciones', 'numero_factura', 'factura_uuid'}
        data = {k: v for k, v in request.data.items() if k in ALLOWED}
        if not data:
            return Response({'detail': f'Solo se permiten editar: {", ".join(sorted(ALLOWED))}'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CarteraDetailSerializer(cartera, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = self.cartera_crud.update_cartera(cartera, serializer.validated_data)
        return Response(CarteraDetailSerializer(updated).data)

    def destroy(self, request, uuid=None, *args, **kwargs):
        """
        DELETE /api/v1/clientes/cartera/{uuid}/ — Elimina obligación.
        Solo permitido si estado_pago == SIN_PAGO (sin abonos aplicados).
        DSV: cartera debe pertenecer a la empresa del tenant.
        """
        cartera = self.get_object()
        if cartera.estado_pago != 'SIN_PAGO':
            return Response(
                {'detail': 'Solo se puede eliminar una obligación con estado SIN_PAGO (sin abonos registrados).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            self.cartera_crud.delete_cartera(cartera)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'],
            renderer_classes=[TemplateHTMLRenderer, JSONRenderer],
            url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """GET /api/v1/clientes/cartera/render-offcanvas/crear/?cliente_uuid=<uuid>"""
        empresa = self.get_empresa()
        cliente_uuid = request.query_params.get('cliente_uuid')
        cliente = None
        if cliente_uuid:
            cliente = Cliente.objects.filter(uuid=cliente_uuid, empresa_id=empresa.id if empresa else None).only(
                'id', 'uuid', 'razon_social', 'numero_documento'
            ).first()
        return render_template_safe(
            {'empresa': empresa, 'cliente': cliente, 'modo': 'crear'},
            'tenant/clientes/offcanvas_crear_cartera.html',
            request=request,
        )

    @action(detail=False, methods=['get'],
            renderer_classes=[TemplateHTMLRenderer, JSONRenderer],
            url_path='render-offcanvas/abono-factura')
    def render_offcanvas_abono_factura(self, request):
        """
        GET /api/v1/clientes/cartera/render-offcanvas/abono-factura/?factura_uuid=<uuid>

        Encuentra o crea un registro Cartera vinculado a la Factura de Venta
        y devuelve el offcanvas de abono. Si el cliente no esta vinculado,
        devuelve el offcanvas de creacion de Cartera con datos pre-rellenados.
        """
        from decimal import Decimal
        from django.utils import timezone as tz
        from apps.tenant.facturas.models import Factura

        empresa = self.get_empresa()
        if not empresa:
            return Response({'error': 'empresa_not_found'}, status=status.HTTP_400_BAD_REQUEST)

        factura_uuid = request.query_params.get('factura_uuid')
        if not factura_uuid:
            return Response({'error': 'factura_uuid requerido'}, status=status.HTTP_400_BAD_REQUEST)

        factura = Factura.objects.filter(
            uuid=factura_uuid, empresa_id=empresa.id, naturaleza='VENTA'
        ).only(
            'id', 'uuid', 'numero', 'total', 'receptor_razon_social',
            'payment_due_date', 'fecha_emision', 'cliente_uuid', 'estado_pago'
        ).first()

        if not factura:
            return Response({'error': 'Factura de venta no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        # 1. Buscar Cartera existente por referencia blanda factura_uuid
        cartera = (
            Cartera.objects.filter(empresa_id=empresa.id, factura_uuid=factura.uuid)
            .select_related('cliente')
            .first()
        )

        if not cartera and factura.cliente_uuid:
            # 2. Resolver cliente via UUID blando
            cliente = Cliente.objects.filter(
                uuid=factura.cliente_uuid, empresa_id=empresa.id
            ).only('id', 'uuid', 'empresa_id', 'razon_social', 'numero_documento').first()

            if cliente:
                hoy = tz.now().date()
                cartera = Cartera.objects.create(
                    empresa_id=empresa.id,
                    cliente=cliente,
                    numero_factura=factura.numero[:50],
                    factura_uuid=factura.uuid,
                    fecha_emision=(factura.fecha_emision.date() if factura.fecha_emision else hoy),
                    fecha_vencimiento=(factura.payment_due_date or hoy),
                    valor_total=(factura.total or Decimal('0')),
                )

        if not cartera:
            # 3. Sin cliente vinculado: mostrar crear-cartera pre-rellenado
            context = {
                'empresa': empresa,
                'cliente': None,
                'modo': 'crear',
                'factura_prefill': {
                    'numero':       factura.numero[:50],
                    'uuid':         str(factura.uuid),
                    'total':        str(factura.total),
                    'fecha_emision':  str(factura.fecha_emision.date()) if factura.fecha_emision else '',
                    'fecha_vencimiento': str(factura.payment_due_date) if factura.payment_due_date else '',
                },
            }
            return render_template_safe(context, 'tenant/clientes/offcanvas_crear_cartera.html', request=request)

        context = {'cartera': cartera, 'cliente': cartera.cliente, 'empresa': cartera.empresa}
        return render_template_safe(context, 'tenant/clientes/offcanvas_abono_cartera.html', request=request)

    @action(
        detail=True,
        methods=['get'],
        renderer_classes=[TemplateHTMLRenderer, JSONRenderer],
        url_path='render-offcanvas/abono'
    )
    def render_offcanvas_abono(self, request, uuid=None):
        """
        GET /api/v1/clientes/cartera/{uuid}/render-offcanvas/abono/
        """
        cartera = self.get_object()
        context = {
            'cartera': cartera,
            'cliente': cartera.cliente,
            'empresa': cartera.empresa
        }
        return render_template_safe(
            context,
            'tenant/clientes/offcanvas_abono_cartera.html',
            request=request
        )
