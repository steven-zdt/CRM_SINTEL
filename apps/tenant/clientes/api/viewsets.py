"""
ViewSet para Clientes v2.60 - Tabulator Implementation + HTMX Offcanvas

⚠️ API-First: Endpoints RESTful para consumo desde Tabulator (Vanilla JS)
⚠️ SSoT: Empresa se inyecta automáticamente desde el tenant
⚠️ v2.60: Soporte para renderizado HTML mediante TemplateHTMLRenderer (HTMX)
"""
from rest_framework import viewsets, mixins, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.renderers import TemplateHTMLRenderer
from django_filters.rest_framework import DjangoFilterBackend
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
        
        # ⚠️ PERFORMANCE BIBLE: Usar .only() con campos necesarios para el template
        return Cliente.objects.filter(empresa_id=empresa.id).only(
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
        ⚠️ v2.60: Zero Trust - Obtiene la empresa del tenant actual.
        """
        empresa = Empresa.objects.only('id').first()
        # ⚠️ v2.61.5: Si no existe, no lanzar excepción. Retornar None.
        return empresa

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
            
            cliente = crear_cliente(empresa, validated_data, contactos_data=contactos_data)
            return Response(
                ClienteDetailSerializer(cliente).data, 
                status=status.HTTP_201_CREATED
            )
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
            return Response(ClienteDetailSerializer(cliente).data)
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
            return Response(ClienteDetailSerializer(cliente).data)
        
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


class ContactoClienteViewSet(viewsets.ModelViewSet):
    """
    ⚠️ v2.60: ViewSet para Contactos de Cliente con Zero Trust estricto.
    
    Endpoints:
    - GET /api/v1/clientes/contactos/ - Lista de contactos (filtrado por cliente, búsqueda global)
    - GET /api/v1/clientes/contactos/{id}/ - Detalle de contacto
    - POST /api/v1/clientes/contactos/ - Crear contacto
    - PATCH /api/v1/clientes/contactos/{id}/ - Actualizar contacto
    - DELETE /api/v1/clientes/contactos/{id}/ - Eliminar contacto
    - GET /api/v1/clientes/contactos/gestor-offcanvas/ - Renderizar HTML del gestor (HTMX)
    
    ⚠️ v2.60: Grid global (Directorio de Contactos) con búsqueda y filtrado.
    """
    # ⚠️ CRÍTICO: DRF necesita un queryset definido como atributo de clase para generar las rutas del router
    # Usamos .none() como base porque el filtrado real se hace en get_queryset()
    queryset = ContactoCliente.objects.none()
    serializer_class = ContactoClienteSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre_completo', 'email', 'telefono', 'cargo', 'cliente__razon_social']
    
    def list(self, request, *args, **kwargs):
        """
        ⚠️ v2.60: Override list para agregar manejo de errores robusto y logging detallado.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # ⚠️ DEBUG: Log del queryset antes de la paginación
            queryset = self.filter_queryset(self.get_queryset())
            logger.info(f'[ContactoClienteViewSet.list] Queryset count: {queryset.count()}')
            
            # Paginación DRF estándar
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                logger.info(f'[ContactoClienteViewSet.list] Página serializada: {len(serializer.data)} registros')
                return self.get_paginated_response(serializer.data)
            
            # Sin paginación
            serializer = self.get_serializer(queryset, many=True)
            logger.info(f'[ContactoClienteViewSet.list] Sin paginación: {len(serializer.data)} registros')
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f'[ContactoClienteViewSet.list] Error: {str(e)}', exc_info=True)
            from rest_framework.response import Response
            from rest_framework import status
            return Response(
                {'detail': f'Error al listar contactos: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_queryset(self):
        """
        ⚠️ Zero Trust: Retorna queryset filtrado por empresa del tenant (SSoT).
        Solo contactos de clientes que pertenecen a la empresa del tenant actual.
        
        ⚠️ PERFORMANCE BIBLE: Usar select_related para optimizar acceso a campos relacionados.
        ⚠️ v2.60: Soporta filtrado por cliente mediante query param 'cliente'.
        ⚠️ v2.60: Grid global - Mantiene Zero Trust pero permite búsqueda y filtrado global.
        ⚠️ CRÍTICO: select_related('cliente') trae el objeto Cliente completo para acceso a razon_social y numero_documento.
        """
        try:
            empresa = self.get_empresa()
            if not empresa:
                # Si no hay empresa, retornar queryset vacío
                return ContactoCliente.objects.none()
            
            # ⚠️ CRÍTICO: Filtrar por cliente__empresa para Zero Trust
            # ⚠️ v2.60: Usar select_related para traer Cliente en una sola query (necesario para cliente_nombre y cliente_documento en el serializer)
            # ⚠️ IMPORTANTE: select_related debe ir después del filter para evitar problemas con relaciones
            # ⚠️ PERFORMANCE BIBLE: Usar .only() para especificar campos necesarios del ContactoCliente
            # ⚠️ CRÍTICO: No usar .only() cuando se necesita acceder a campos del modelo relacionado con select_related
            # select_related('cliente') carga el objeto Cliente completo, pero .only() puede interferir
            # Solución: Cargar todos los campos del ContactoCliente (es un modelo pequeño) y usar select_related para Cliente
            queryset = ContactoCliente.objects.filter(
                cliente__empresa_id=empresa.id
            ).select_related('cliente')
            # ⚠️ NOTA: No usar .only() aquí porque necesitamos acceso completo a los campos del Cliente relacionado
            # El modelo ContactoCliente es pequeño, así que cargar todos los campos no es un problema de performance
            
            # ⚠️ DEBUG: Verificar que el queryset es válido y que los campos del Cliente están disponibles
            # Esto ayuda a detectar problemas antes de la serialización
            try:
                # Hacer una consulta de prueba para verificar que no hay errores
                test_exists = queryset.exists()
                # Verificar que select_related está funcionando correctamente
                if test_exists:
                    test_obj = queryset.first()
                    if test_obj and hasattr(test_obj, 'cliente'):
                        # Verificar que los campos necesarios están disponibles
                        if not hasattr(test_obj.cliente, 'razon_social'):
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(f'[ContactoClienteViewSet.get_queryset] Cliente no tiene razon_social, puede causar error en serializer')
                        if not hasattr(test_obj.cliente, 'numero_documento'):
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(f'[ContactoClienteViewSet.get_queryset] Cliente no tiene numero_documento, puede causar error en serializer')
            except Exception as qs_error:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'[ContactoClienteViewSet.get_queryset] Error en queryset: {str(qs_error)}', exc_info=True)
                return ContactoCliente.objects.none()
            
            # ⚠️ v2.60: Filtrar por cliente específico si se proporciona en query params
            cliente_id = self.request.query_params.get('cliente')
            if cliente_id:
                try:
                    cliente_id = int(cliente_id)
                    # ⚠️ Zero Trust: Validar que el cliente pertenezca al tenant
                    cliente = Cliente.objects.filter(id=cliente_id, empresa_id=empresa.id).only('id').first()
                    if cliente:
                        queryset = queryset.filter(cliente_id=cliente_id)
                    else:
                        # Si el cliente no existe o no pertenece al tenant, retornar queryset vacío
                        queryset = queryset.none()
                except (ValueError, TypeError):
                    # Si cliente_id no es un entero válido, retornar queryset vacío
                    queryset = queryset.none()
            
            return queryset
        except Exception as e:
            # ⚠️ Error Boundary: Capturar cualquier error y retornar queryset vacío
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'[ContactoClienteViewSet.get_queryset] Error: {str(e)}', exc_info=True)
            return ContactoCliente.objects.none()
    
    def get_empresa(self):
        """
        ⚠️ v2.60: Zero Trust - Obtiene la empresa del tenant actual.
        """
        empresa = Empresa.objects.only('id').first()
        # ⚠️ v2.61.5: Si no existe, no lanzar excepción. Retornar None.
        return empresa
    
    def perform_create(self, serializer):
        """
        ⚠️ Zero Trust: Validar que el cliente pertenezca al tenant antes de crear.
        """
        cliente_id = serializer.validated_data.get('cliente_id') or (
            serializer.validated_data.get('cliente').id if serializer.validated_data.get('cliente') else None
        )
        
        if cliente_id:
            empresa = self.get_empresa()
            # ⚠️ Zero Trust: Verificar que el cliente pertenezca al tenant
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
        
        # Si se intenta cambiar el cliente, validar Zero Trust
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
        ⚠️ v2.60: Devuelve el HTML del gestor de contactos para un cliente (vía HTMX).
        
        Query params:
        - cliente_id: ID del cliente (opcional - si no se proporciona, se crea contacto sin cliente específico)
        
        Returns:
            Template HTML renderizado con contexto del cliente y sus contactos
        """
        empresa = self.get_empresa()
        cliente = None
        contactos = []
        
        cliente_id = request.query_params.get('cliente_id')
        if cliente_id:
            # ⚠️ Zero Trust: Validar que el cliente pertenezca al tenant
            from django.shortcuts import get_object_or_404
            cliente = get_object_or_404(
                Cliente.objects.filter(empresa_id=empresa.id).only('id', 'razon_social'),
                id=cliente_id
            )
            
            # ⚠️ PERFORMANCE BIBLE: Cargar contactos con .only()
            contactos = ContactoCliente.objects.filter(cliente=cliente).only(
                'id', 'nombre_completo', 'cargo', 'email', 'telefono', 'activo', 'is_principal'
            ).order_by('-is_principal', 'nombre_completo')
        else:
            # ⚠️ v2.60: Modo creación global - crear un cliente temporal para el contexto
            # El formulario permitirá seleccionar el cliente
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