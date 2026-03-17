"""
ViewSet para Clientes v2.60 - Tabulator Implementation + HTMX Offcanvas

⚠️ API-First: Endpoints RESTful para consumo desde Tabulator (Vanilla JS)
⚠️ SSoT: Empresa se inyecta automáticamente desde el tenant
⚠️ v2.60: Soporte para renderizado HTML mediante TemplateHTMLRenderer (HTMX)
"""
from rest_framework import viewsets, mixins, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.renderers import TemplateHTMLRenderer
from django_filters.rest_framework import DjangoFilterBackend
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.empresa.models import Empresa
from apps.tenant.clientes.models import Cliente, ContactoCliente
from apps.tenant.clientes.services import qs_list, qs_detail, crear_cliente, actualizar_cliente
from apps.tenant.clientes.api.serializers import ClienteListSerializer, ClienteDetailSerializer, ContactoClienteSerializer


class StandardResultsSetPagination(PageNumberPagination):
    """
    ⚠️ v2.40: Paginación estándar para Tabulator.
    Tabulator espera: {count, next, previous, results: [...]}
    """
    page_size = 10  # Default: 10 (estándar SaaS)
    page_size_query_param = 'page_size'
    max_page_size = 100


class ClienteViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    """
    ⚠️ v2.60: ViewSet para Clientes con soporte Tabulator y HTMX Offcanvas.
    
    Endpoints:
    - GET /api/v1/clientes/ - Lista paginada (Tabulator)
    - GET /api/v1/clientes/{id}/ - Detalle
    - POST /api/v1/clientes/ - Crear
    - PUT /api/v1/clientes/{id}/ - Actualizar completo
    - PATCH /api/v1/clientes/{id}/ - Actualizar parcial
    - DELETE /api/v1/clientes/{id}/ - Eliminar
    - GET /api/v1/clientes/offcanvas/ - Renderizar HTML del Offcanvas (HTMX)
    """
    # ⚠️ CRÍTICO: DRF necesita un queryset definido para generar las rutas del router
    # Usamos .none() como base porque el filtrado real se hace en get_queryset() o en los métodos
    queryset = Cliente.objects.none()
    serializer_class = ClienteDetailSerializer  # ⚠️ CRÍTICO: DRF necesita serializer_class para generar rutas
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """
        ⚠️ v2.60: Retorna queryset filtrado por empresa del tenant (SSoT).
        """
        empresa = self.get_empresa()
        if not empresa:
            return Cliente.objects.none()
        
        # ⚠️ PERFORMANCE BIBLE: Usar .only() con campos necesarios y prefetch_related para contactos
        return Cliente.objects.filter(empresa_id=empresa.id).prefetch_related(
            models.Prefetch('contactos', queryset=ContactoCliente.objects.all().order_by('-is_principal', 'nombre_completo'), to_attr='contactos_prefetched')
        ).only(
            'id',
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
        )

    def get_empresa(self):
        """
        ⚠️ v2.60: Zero Trust - Obtiene la empresa del usuario.
        """
        return self.request.user.empresa if hasattr(self.request.user, 'empresa') else None


    def list(self, request):
        """
        Endpoint para Tabulator (GET /api/v1/clientes/).
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response({'count': 0, 'results': []})
            
        search = request.query_params.get('search', '').strip()
        
        queryset = qs_list(empresa.id, search if search else None)
        
        # ... resto del método list igual ...
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = ClienteListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ClienteListSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Crea un nuevo cliente."""
        empresa = self.get_empresa()
        if not empresa:
            return Response({'detail': 'Configure la empresa antes de crear clientes.'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ClienteDetailSerializer(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data.copy()
            contactos_data = validated_data.pop('contactos', None)
            
            try:
                cliente = crear_cliente(empresa, validated_data, contactos_data=contactos_data)
                data = ClienteDetailSerializer(cliente).data
                data['redirect'] = '/workspace/#clientes'
                return Response(data, status=status.HTTP_201_CREATED)
            except serializers.ValidationError as e:
                # ⚠️ Capturar ValidationError del servicio y retornar 400 amigable
                return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """
        Actualiza un cliente (PUT completo).
        
        ⚠️ v2.60: Soporta actualización de contactos asociados en el mismo payload.
        
        ⚠️ Manejo de errores:
        - ValidationError del servicio (duplicados) se convierte automáticamente en HTTP 400
        """
        cliente = self.get_object()
        serializer = ClienteDetailSerializer(cliente, data=request.data, partial=False)
        if serializer.is_valid():
            # ⚠️ v2.60: Extraer contactos del validated_data antes de pasarlo al servicio
            validated_data = serializer.validated_data.copy()
            contactos_data = validated_data.pop('contactos', None)
            
            # ⚠️ actualizar_cliente puede lanzar ValidationError si hay duplicados
            cliente = actualizar_cliente(cliente, validated_data, contactos_data=contactos_data)
            data = ClienteDetailSerializer(cliente).data
            data['redirect'] = '/workspace/#clientes'
            return Response(data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        """
        Actualiza un cliente parcialmente (PATCH).
        
        ⚠️ v2.60: Soporta actualización de contactos asociados en el mismo payload.
        
        ⚠️ Manejo de errores:
        - ValidationError del servicio (duplicados) se convierte automáticamente en HTTP 400
        """
        import logging
        logger = logging.getLogger(__name__)
        
        cliente = self.get_object()
        serializer = ClienteDetailSerializer(cliente, data=request.data, partial=True)
        
        # ⚠️ DEBUG: Log del payload recibido
        logger.info(f'[ClienteViewSet.partial_update] Payload recibido: {request.data}')
        
        if serializer.is_valid():
            # ⚠️ v2.60: Extraer contactos del validated_data antes de pasarlo al servicio
            validated_data = serializer.validated_data.copy()
            contactos_data = validated_data.pop('contactos', None)
            
            logger.info(f'[ClienteViewSet.partial_update] Validated data: {validated_data}')
            logger.info(f'[ClienteViewSet.partial_update] Contactos data: {contactos_data}')
            
            # ⚠️ actualizar_cliente puede lanzar ValidationError si hay duplicados
            cliente = actualizar_cliente(cliente, validated_data, contactos_data=contactos_data)
            data = ClienteDetailSerializer(cliente).data
            data['redirect'] = '/workspace/#clientes'
            return Response(data)
        
        # ⚠️ DEBUG: Log de errores de validación
        logger.error(f'[ClienteViewSet.partial_update] Errores de validación: {serializer.errors}')
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """
        ⚠️ REGLA DE SEGURIDAD DE ELIMINACIÓN (Inactivar antes de Borrar):
        - No se puede eliminar un cliente activo.
        - El cliente debe estar inactivo (activo=False) antes de poder eliminarlo.
        - Eliminación física (hard delete) solo si está inactivo.
        
        Returns:
            400 Bad Request si el cliente está activo
            204 No Content si se elimina exitosamente
        """
        cliente = self.get_object()
        
        # Validar que el cliente no esté activo
        if cliente.activo:
            return Response(
                {
                    "error": "active_record",
                    "message": "No se puede eliminar un ítem activo. Cámbielo a 'Inactivo' en el formulario de edición antes de intentar borrarlo."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ⚠️ HARD DELETE: Eliminación física solo si está inactivo
        cliente.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer])
    def offcanvas(self, request):
        """
        ⚠️ v2.60: Devuelve el HTML del Offcanvas para crear o editar un cliente (vía HTMX).
        
        Query params:
        - id: ID del cliente para edición (opcional)
        
        Returns:
            Template HTML renderizado con contexto del cliente (si existe) y sus contactos
        """
        context = {
            'cliente': None,
            'contactos': [],
            'modo': 'crear'
        }
        
        cliente_id = request.query_params.get('id')
        
        if cliente_id:
            # ⚠️ Modo Edición: Obtener cliente validando el tenant (Zero Trust)
            # Usa get_queryset() que ya filtra por empresa del tenant
            cliente = self.get_queryset().filter(id=cliente_id).first()
            
            if cliente:
                context['cliente'] = cliente
                context['modo'] = 'editar'
                
                # ⚠️ PERFORMANCE BIBLE: Cargar contactos con .only()
                contactos = ContactoCliente.objects.filter(cliente=cliente).only(
                    'id', 'nombre_completo', 'cargo', 'email', 'telefono', 'activo', 'is_principal'
                ).order_by('-is_principal', 'nombre_completo')
                context['contactos'] = contactos
        
        # Retorna el template HTML vacío o con datos
        return Response(context, template_name='tenant/core/partials/clientes/offcanvas_form.html')
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """
        ⚠️ v2.61: Endpoint HTMX RESTful para cargar offcanvas de creación de clientes.
        
        GET /api/v1/clientes/render-offcanvas/crear/
        
        Returns:
            Template HTML: tenant/core/partials/clientes/offcanvas_crear_cliente.html
        """
        context = {
            'cliente': None,
            'contactos': [],
            'is_draft': True,
            'modo': 'crear'
        }
        
        return Response(context, template_name='tenant/core/partials/clientes/offcanvas_crear_cliente.html')
    
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, pk=None):
        """
        ⚠️ v2.61: Endpoint HTMX RESTful para cargar offcanvas de edición de clientes.
        
        GET /api/v1/clientes/{id}/render-offcanvas/editar/
        
        Returns:
            Template HTML: tenant/core/partials/clientes/offcanvas_editar_cliente.html
        """
        # ⚠️ Zero Trust: Obtener cliente validando el tenant
        cliente = self.get_object()
        
        # ⚠️ PERFORMANCE BIBLE: Cargar contactos con .only()
        contactos = ContactoCliente.objects.filter(cliente=cliente).only(
            'id', 'nombre_completo', 'cargo', 'email', 'telefono', 'activo', 'is_principal'
        ).order_by('-is_principal', 'nombre_completo')
        
        context = {
            'cliente': cliente,
            'contactos': contactos,
            'is_draft': False,
            'modo': 'editar'
        }
        
        return Response(context, template_name='tenant/core/partials/clientes/offcanvas_editar_cliente.html')
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request):
        """
        ⚠️ v2.61: Endpoint HTMX RESTful para cargar offcanvas de detalle de clientes (read-only).
        
        GET /api/v1/clientes/render-offcanvas/detalle/?id={id}
        
        Query params:
        - id: ID del cliente (requerido)
        
        Returns:
            Template HTML: tenant/core/partials/clientes/offcanvas_detalle_cliente.html
        """
        cliente_id = request.query_params.get('id')
        
        if not cliente_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'id': 'El parámetro "id" es requerido'})
        
        # ⚠️ Zero Trust: Obtener cliente validando el tenant
        cliente = self.get_queryset().filter(id=cliente_id).first()
        
        if not cliente:
            from rest_framework.exceptions import NotFound
            raise NotFound('Cliente no encontrado')
        
        # ⚠️ PERFORMANCE BIBLE: Cargar contactos con .only()
        contactos = ContactoCliente.objects.filter(cliente=cliente).only(
            'id', 'nombre_completo', 'cargo', 'email', 'telefono', 'activo', 'is_principal'
        ).order_by('-is_principal', 'nombre_completo')
        
        context = {
            'cliente': cliente,
            'contactos': contactos,
            'modo': 'detalle'
        }
        
        return Response(context, template_name='tenant/core/partials/clientes/offcanvas_detalle_cliente.html')


class ContactoClienteViewSet(BaseTenantViewSet):
    """
    ⚠️ v2.60: ViewSet para Contactos de Cliente con Zero Trust estricto.
    """
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
    
    queryset = ContactoCliente.objects.none()
    serializer_class = ContactoClienteSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre_completo', 'email', 'telefono', 'cargo', 'cliente__razon_social']
    
    # ⚠️ v2.61: Restringir métodos HTTP según requerimiento
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
        """
        ⚠️ Zero Trust: Retorna queryset filtrado por empresa del tenant (SSoT).
        """
        empresa = self.get_empresa()
        if not empresa:
            return ContactoCliente.objects.none()
            
        queryset = ContactoCliente.objects.filter(
            cliente__empresa_id=empresa.id
        ).select_related('cliente')
        
        # Filtrado por cliente
        cliente_id = self.request.query_params.get('cliente')
        if cliente_id:
            try:
                queryset = queryset.filter(cliente_id=int(cliente_id))
            except ValueError:
                queryset = queryset.none()
        
        return queryset
    
    def get_empresa(self):
        """
        ⚠️ v2.60: Zero Trust - Obtiene la empresa del usuario.
        """
        return self.request.user.empresa if hasattr(self.request.user, 'empresa') else None
    
    def perform_create(self, serializer):
        """
        ⚠️ Zero Trust: Validar que el cliente pertenezca al tenant antes de crear.
        """
        cliente_id = serializer.validated_data.get('cliente_id') or (
            serializer.validated_data.get('cliente').id if serializer.validated_data.get('cliente') else None
        )
        
        if cliente_id:
            empresa = self.get_empresa()
            cliente = Cliente.objects.filter(id=cliente_id, empresa_id=empresa.id).only('id').first()
            if not cliente:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({
                    'cliente': ['El cliente especificado no existe o no pertenece a este tenant.']
                })
        
        serializer.save()
    
    def perform_update(self, serializer):
        """
        ⚠️ Zero Trust: Validar que el contacto y su cliente pertenezcan al tenant.
        """
        contacto = self.get_object()  # Ya está filtrado por get_queryset()
        
        nuevo_cliente_id = serializer.validated_data.get('cliente_id') or (
            serializer.validated_data.get('cliente').id if serializer.validated_data.get('cliente') else None
        )
        
        if nuevo_cliente_id and nuevo_cliente_id != contacto.cliente_id:
            empresa = self.get_empresa()
            cliente = Cliente.objects.filter(id=nuevo_cliente_id, empresa_id=empresa.id).only('id').first()
            if not cliente:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({
                    'cliente': ['El cliente especificado no existe o no pertenece a este tenant.']
                })
        
        serializer.save()
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        ⚠️ v2.60: Devuelve el HTML del gestor de contactos (vía HTMX).
        """
        empresa = self.get_empresa()
        cliente = None
        contactos = []
        
        cliente_id = request.query_params.get('cliente_id')
        if cliente_id:
            from django.shortcuts import get_object_or_404
            cliente = get_object_or_404(
                Cliente.objects.filter(empresa_id=empresa.id).only('id', 'razon_social'),
                id=cliente_id
            )
            
            contactos = ContactoCliente.objects.filter(cliente=cliente).only(
                'id', 'nombre_completo', 'cargo', 'email', 'telefono', 'activo', 'is_principal'
            ).order_by('-is_principal', 'nombre_completo')
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
        
        return Response(context, template_name='tenant/core/partials/clientes/contactos_offcanvas.html')