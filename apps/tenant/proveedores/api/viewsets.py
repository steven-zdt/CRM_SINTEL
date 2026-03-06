"""
ViewSet para Proveedores v2.60 - Tabulator Implementation + HTMX Offcanvas

⚠️ API-First: Endpoints RESTful para consumo desde Tabulator (Vanilla JS)
⚠️ SSoT: Empresa se inyecta automáticamente desde el tenant
⚠️ v2.60: Migrado a Zero Trust + Service Layer + HTMX Offcanvas
"""
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import APIException
from django.shortcuts import get_object_or_404
from apps.tenant.empresa.models import Empresa
from apps.tenant.proveedores.models import Proveedor
from apps.tenant.proveedores.services import (
    qs_list, qs_detail, crear_proveedor, actualizar_proveedor
)
from apps.tenant.proveedores.api.serializers import (
    ProveedorListSerializer, ProveedorDetailSerializer
)


class StandardResultsSetPagination(PageNumberPagination):
    """
    ⚠️ v2.40: Paginación estándar para Tabulator.
    Tabulator espera: {count, next, previous, results: [...]}
    """
    page_size = 10  # Default: 10 (estándar SaaS)
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProveedorViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    """
    ⚠️ v2.40: ViewSet para Proveedores con soporte Tabulator.
    
    Endpoints:
    - GET /api/v1/proveedores/ - Lista paginada (Tabulator)
    - GET /api/v1/proveedores/{id}/ - Detalle
    - POST /api/v1/proveedores/ - Crear
    - PUT /api/v1/proveedores/{id}/ - Actualizar completo
    - PATCH /api/v1/proveedores/{id}/ - Actualizar parcial
    - DELETE /api/v1/proveedores/{id}/ - Eliminar (soft delete)
    """
    # ⚠️ CRÍTICO: DRF necesita un queryset definido para generar las rutas del router
    queryset = Proveedor.objects.none()
    serializer_class = ProveedorDetailSerializer
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        """
        ⚠️ v2.60: Selecciona el serializer según la acción.
        List usa ProveedorListSerializer (optimizado), resto usa ProveedorDetailSerializer.
        """
        if self.action == 'list':
            return ProveedorListSerializer
        return ProveedorDetailSerializer

    def get_empresa(self):
        """
        ⚠️ v2.60: Zero Trust - Obtiene la empresa del tenant actual.
        
        ⚠️ PERFORMANCE BIBLE:
        - Usa .first() en lugar de .all()[0] (más eficiente)
        - Singleton pattern: Solo debe existir una empresa por tenant
        
        Returns:
            Empresa: Instancia de la empresa del tenant
            
        Raises:
            APIException: Si no se encuentra la empresa
        """
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise APIException(detail='No se encontró empresa para este tenant')
        return empresa

    def list(self, request):
        """
        Endpoint para Tabulator (GET /api/v1/proveedores/).
        
        Parámetros de consulta:
        - search: Búsqueda en razon_social, numero_documento, email_contacto
        - page: Número de página
        - page_size: Tamaño de página (máx 100)
        
        Retorna: {count, next, previous, results: [...]}
        """
        empresa = self.get_empresa()
        search = request.query_params.get('search', '').strip()
        
        queryset = qs_list(empresa.id, search if search else None)
        
        # Paginación DRF estándar
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = ProveedorListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        # Fallback: sin paginación
        serializer = ProveedorListSerializer(queryset, many=True)
        return Response(serializer.data)

    def get_object(self):
        """Obtiene el objeto Proveedor para retrieve/update/partial_update/destroy."""
        empresa = self.get_empresa()
        pk = self.kwargs.get('pk')
        proveedor = qs_detail(empresa.id, pk)
        if not proveedor:
            from rest_framework.exceptions import NotFound
            raise NotFound('Proveedor no encontrado')
        return proveedor
    
    def retrieve(self, request, *args, **kwargs):
        """Obtiene detalle de un proveedor."""
        proveedor = self.get_object()
        serializer = ProveedorDetailSerializer(proveedor)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        ⚠️ v2.60: Crea un nuevo proveedor usando Service Layer con Zero Trust.
        
        ⚠️ Manejo de errores:
        - ValidationError del servicio (duplicados) se convierte automáticamente en HTTP 400
        - DRF maneja automáticamente ValidationError a través de exception_handler
        """
        empresa = self.get_empresa()
        serializer = ProveedorDetailSerializer(data=request.data)
        if serializer.is_valid():
            # ⚠️ v2.60: crear_proveedor ahora recibe empresa_id en lugar de instancia
            proveedor = crear_proveedor(empresa.id, serializer.validated_data)
            return Response(
                ProveedorDetailSerializer(proveedor).data, 
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """
        ⚠️ v2.60: Actualiza un proveedor (PUT completo) usando Service Layer con Zero Trust.
        
        ⚠️ Manejo de errores:
        - ValidationError del servicio (duplicados) se convierte automáticamente en HTTP 400
        """
        empresa = self.get_empresa()
        proveedor = self.get_object()
        serializer = ProveedorDetailSerializer(proveedor, data=request.data, partial=False)
        if serializer.is_valid():
            # ⚠️ v2.60: actualizar_proveedor ahora recibe proveedor_id y empresa_id
            proveedor = actualizar_proveedor(proveedor.id, empresa.id, serializer.validated_data)
            return Response(ProveedorDetailSerializer(proveedor).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        """
        ⚠️ v2.60: Actualiza un proveedor parcialmente (PATCH) usando Service Layer con Zero Trust.
        
        ⚠️ Manejo de errores:
        - ValidationError del servicio (duplicados) se convierte automáticamente en HTTP 400
        """
        empresa = self.get_empresa()
        proveedor = self.get_object()
        serializer = ProveedorDetailSerializer(proveedor, data=request.data, partial=True)
        if serializer.is_valid():
            # ⚠️ v2.60: actualizar_proveedor ahora recibe proveedor_id y empresa_id
            proveedor = actualizar_proveedor(proveedor.id, empresa.id, serializer.validated_data)
            return Response(ProveedorDetailSerializer(proveedor).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """
        ⚠️ REGLA DE SEGURIDAD DE ELIMINACIÓN (Inactivar antes de Borrar):
        - No se puede eliminar un proveedor activo.
        - El proveedor debe estar inactivo (activo=False) antes de poder eliminarlo.
        - Eliminación física (hard delete) solo si está inactivo.
        
        Returns:
            400 Bad Request si el proveedor está activo
            204 No Content si se elimina exitosamente
        """
        proveedor = self.get_object()
        
        # Validar que el proveedor no esté activo
        if proveedor.activo:
            return Response(
                {
                    "error": "active_record",
                    "message": "No se puede eliminar un ítem activo. Cámbielo a 'Inactivo' en el formulario de edición antes de intentar borrarlo."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ⚠️ HARD DELETE: Eliminación física solo si está inactivo
        proveedor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        ⚠️ v2.60: Devuelve el HTML del formulario de proveedor para HTMX Offcanvas.
        
        Endpoint: GET /api/v1/proveedores/gestor-offcanvas/
        
        Query params:
        - id: ID del proveedor (opcional - si no se proporciona, es modo creación)
        
        Returns:
            Template HTML renderizado con contexto del proveedor y catálogos necesarios
        """
        # ⚠️ Zero Trust: Obtener empresa del tenant actual
        empresa = self.get_empresa()
        
        proveedor = None
        id_instancia = request.query_params.get('id')
        
        if id_instancia:
            # ⚠️ Zero Trust: Validar que el proveedor pertenezca al tenant
            proveedor = get_object_or_404(
                self.get_queryset(),
                id=id_instancia
            )
        
        # ⚠️ Catálogos: Preparar choices para los selects del formulario
        tipo_persona_choices = Proveedor.TIPO_PERSONA
        tipo_documento_choices = Proveedor.TIPO_DOCUMENTO
        regimen_choices = Proveedor.REGIMEN
        tipo_cuenta_choices = [("AHORROS", "Ahorros"), ("CORRIENTE", "Corriente")]
        
        context = {
            'proveedor': proveedor,
            'empresa': empresa,
            'tipo_persona_choices': tipo_persona_choices,
            'tipo_documento_choices': tipo_documento_choices,
            'regimen_choices': regimen_choices,
            'tipo_cuenta_choices': tipo_cuenta_choices,
        }
        
        template_name = 'tenant/core/partials/proveedores/proveedor_offcanvas.html'
        
        return Response(context, template_name=template_name)
    
    def get_queryset(self):
        """
        ⚠️ v2.60: Retorna QuerySet filtrado por empresa (Zero Trust).
        Usado por get_object() y gestor_offcanvas.
        """
        empresa = self.get_empresa()
        return Proveedor.objects.filter(empresa_id=empresa.id)