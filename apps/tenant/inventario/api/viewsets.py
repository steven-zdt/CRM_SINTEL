from django.conf import settings
from django.core.exceptions import ValidationError
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.request import Request
from rest_framework.response import Response

from apps.tenant.api.permissions import IsTenantAdmin, IsTenantAdminOrReadOnly, IsTenantMember

# SINTEL v3.5: Refactorizacion Service Layer (Tri-Part)
# PROHIBIDO IMPORTAR MODELOS directamente en ViewSets.
# Toda consulta de base de datos DEBE pasar por el Service Layer.
from apps.tenant.inventario import services as inv_services

# Nuevos Serializers
from .serializers import (
    ActivoFijoDetailSerializer,
    ActivoFijoListSerializer,
    CategoriaItemDetailSerializer,
    # v2.60: Serializers List/Detail explicitas
    CategoriaItemListSerializer,
    HistorialServicioSerializer,
    MovimientoInventarioListSerializer,
    # v2.60: Aliases para compatibilidad
    MovimientoInventarioSerializer,
    ProductoDetailSerializer,
    ProductoListSerializer,
    ServicioDetailSerializer,
    ServicioListSerializer,
    StockResponseSerializer,
)

# En dev: usar UnsafeSessionAuthentication si existe (CSRF relajado).
try:
    from apps.tenant.api.authentication import UnsafeSessionAuthentication
    _UnsafeSessionAuthentication = UnsafeSessionAuthentication
except Exception:
    _UnsafeSessionAuthentication = None


class StandardResultsSetPagination(PageNumberPagination):
    """
    v2.40: Paginacion estandar para Tabulator.
    Tabulator espera: {count, next, previous, results: [...]}
    """
    page_size = 10  # Default: 10 (estandar SaaS)
    page_size_query_param = 'page_size'
    max_page_size = 100


class BaseViewSet(viewsets.GenericViewSet, 
                   mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.CreateModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.DestroyModelMixin):
    """
    v2.60: ViewSet base para inventario usando GenericViewSet con mixins especificos.
    
    SINTEL v2.60: Sincronizacion Arquitectonica
    - GenericViewSet: Base flexible con mixins especificos (List, Retrieve, Create, Update, Destroy)
    - ENFORCED MODE: Validacion de permisos para mutaciones
    - Asignacion de Empresa (SSoT): Automatica en perform_create()
    - Formato DRF {count, results}: Garantizado en list() para Tabulator Factory
    """
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]
    pagination_class = StandardResultsSetPagination

    def get_authenticators(self):
        if settings.DEBUG and _UnsafeSessionAuthentication:
            return [_UnsafeSessionAuthentication()]
        return super().get_authenticators()
    
    def _check_enforced_mode(self, request):
        """
        v2.60: Verifica si el usuario tiene permisos para mutaciones (ENFORCED MODE).
        """
        from rest_framework.permissions import SAFE_METHODS
        
        user = request.user
        if not (user and user.is_authenticated):
            return False, "Usuario no autenticado."
        
        if request.method in SAFE_METHODS:
            return True, None
        
        if IsTenantAdmin().has_permission(request, self):
            return True, None
        
        return False, "Solo usuarios ADMIN/STAFF del tenant pueden crear/editar/eliminar."

    def perform_create(self, serializer):
        """
        v2.60: Asigna automaticamente la Empresa (SSoT) al crear un registro.
        Usa get_empresa_singleton() de services para asegurar Zero Trust.
        """
        empresa = inv_services.get_empresa_singleton()
        serializer.save(empresa=empresa)
    
    def list(self, request, *args, **kwargs):
        """
        v2.60: Listado paginado con formato DRF {count, results} para Tabulator Factory.
        Garantiza que siempre retorne el formato estandar DRF compatible con Tabulator Factory.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # Si no hay paginacion, retornar formato compatible
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': len(serializer.data),
            'next': None,
            'previous': None,
            'results': serializer.data
        })
    
    # --- Overrides para Enforced Mode ---
    def create(self, request: Request, *args, **kwargs) -> Response:
        ok, reason = self._check_enforced_mode(request)
        if not ok: return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return super().create(request, *args, **kwargs)
    
    def update(self, request: Request, *args, **kwargs) -> Response:
        ok, reason = self._check_enforced_mode(request)
        if not ok: return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        ok, reason = self._check_enforced_mode(request)
        if not ok: return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return super().destroy(request, *args, **kwargs)


class CategoriaItemViewSet(BaseViewSet, inv_services.CategoriaItemServiceMixin):
    """
    v2.61: ViewSet para CATEGORIAS de Inventario con Inyeccion de Servicio.
    """
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CategoriaItemListSerializer
        return CategoriaItemDetailSerializer
    
    def get_queryset(self):
        empresa = inv_services.get_empresa_singleton()
        search = self.request.query_params.get('search', None)
        return inv_services.qs_categoria_list(empresa_id=empresa.id, search=search).order_by('nombre')
    
    def get_object(self):
        empresa = inv_services.get_empresa_singleton()
        return inv_services.qs_categoria_detail(empresa_id=empresa.id, categoria_id=self.kwargs['pk'])
    
    def get_empresa(self):
        return inv_services.get_empresa_singleton()

    def destroy(self, request, *args, **kwargs):
        """
        Garantiza que la logica de borrado (set null) viva en el Service Layer.
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        instance = self.get_object()
        self.service_categoria_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['get'], url_path='resumen')
    def resumen(self, request, pk=None):
        """
        v2.40: Retorna un resumen con el conteo de productos/servicios/activos asociados a esta categoria.
        """
        instance = self.get_object()
        resumen = self.service_categoria_get_resumen(instance)
        return Response(resumen)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        v2.60: Devuelve el HTML del formulario de categoria para HTMX Offcanvas via Servicio.
        """
        empresa = self.get_empresa()
        id_instancia = request.query_params.get('id')
        context = self.service_categoria_get_offcanvas_context(empresa, id_instancia)
        return Response(context, template_name='inventario/offcanvas_categoria.html')


class ProductoViewSet(BaseViewSet, inv_services.ProductoServiceMixin):
    """
    WARNING: v2.61: ViewSet para PRODUCTOS con Inyección de Servicio.
    """
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProductoListSerializer
        return ProductoDetailSerializer
    
    def get_queryset(self):
        try:
            empresa = inv_services.get_empresa_singleton()
        except ValidationError:
            return inv_services.qs_producto_list(empresa_id=0)
        
        search = self.request.query_params.get('search', None)
        return inv_services.qs_producto_list(empresa_id=empresa.id, search=search).order_by('nombre')
    
    def get_object(self):
        empresa = inv_services.get_empresa_singleton()
        return inv_services.qs_producto_detail(empresa_id=empresa.id, producto_id=self.kwargs['pk'])
    
    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        WARNING: v2.61.3: Sobrescribe create() para manejar IntegrityError (código duplicado)
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            import re

            from django.db import IntegrityError
            
            # Capturar IntegrityError por código duplicado
            if isinstance(e, IntegrityError):
                error_msg = str(e)
                # Buscar el código duplicado en el mensaje de error
                codigo_match = re.search(r'Key \(codigo\)=\(([^)]+)\)', error_msg)
                if codigo_match:
                    codigo = codigo_match.group(1)
                    return Response(
                        {
                            "error": "duplicate_code",
                            "message": f"Ya existe un producto con el código '{codigo}'. Por favor, use un código diferente.",
                            "detail": f"El código '{codigo}' ya está en uso."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                else:
                    # IntegrityError genérico
                    return Response(
                        {
                            "error": "integrity_error",
                            "message": "Error de integridad: El producto no puede ser creado. Verifique que los datos sean únicos.",
                            "detail": "Violación de restricción de integridad en la base de datos."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Re-lanzar otros errores para que DRF los maneje normalmente
            raise

    @action(detail=False, methods=["get", "post"], url_path="dt")
    def datatables(self, request):
        """
        WARNING: DEPRECATED v2.40: Endpoint legacy para DataTables Server-Side.
        Ya no se usa - Tabulator Factory consume GET /api/v1/inventario/productos/ directamente.
        Se mantiene por compatibilidad temporal, pero será eliminado en v2.50.
        
        WARNING: v2.40: DataTables SERVER-SIDE para Productos.
        Retorna datos paginados en formato estándar DataTables server-side.
        Usa DataTableServer helper para procesamiento seguro.
        """
        from apps.shared.datatable import DataTableServer, DataTableSpec
        from apps.tenant.inventario.api.serializers import ProductoListSerializer
        from apps.tenant.inventario import services as inv_services
        
        empresa = inv_services.get_empresa_singleton()
        qs_base = inv_services.qs_producto_list(empresa_id=empresa.id)
        
        # WARNING: CRÍTICO: fields_map debe coincidir EXACTAMENTE con el orden de columnas en inventario.page.js
        # Columnas: 0=codigo, 1=nombre, 2=categoria_nombre, 3=stock_actual, 4=precio_venta, 5=activo, 6=Acciones (no ordenable)
        spec = DataTableSpec(
            fields_map={
                0: 'codigo',
                1: 'nombre',
                2: 'categoria__nombre',  # Serializer expone como categoria_nombre, pero en DB es categoria__nombre
                3: 'stock_actual',
                4: 'precio_venta',
                5: 'activo'
            },
            search_fields=['codigo', 'nombre', 'categoria__nombre'],
            base_qs=qs_base,
            serializer=ProductoListSerializer,
            extra_filter=lambda req, qs: qs  # Sin filtros adicionales
        )
        
        # Procesar request DataTables
        dt_server = DataTableServer(spec)
        return dt_server.handle(request)

    @action(detail=True, methods=["get"], url_path="stock")
    def stock(self, request, pk=None):
        """
        Retorna solo el stock actual de un producto.
        
        WARNING: PERFORMANCE BIBLE: Solo campos necesarios (id, nombre, stock_actual)
        """
        # WARNING: CRÍTICO: Solo obtener campos necesarios - evitar get_object() que trae todos los campos
        pk = self.kwargs.get('pk')
        empresa = inv_services.get_empresa_singleton()
        producto = self.service_producto_get_stock(empresa, pk)
        
        serializer = StockResponseSerializer({
            "id": producto.id,
            "nombre": producto.nombre,
            "stock_actual": producto.stock_actual
        })
        return Response(serializer.data)
    
    @action(detail=True, methods=["get"], url_path="kardex")
    def kardex(self, request, pk=None):
        """
        WARNING: v2.40: Endpoint para obtener el historial de movimientos (Kardex) de un producto específico.
        Retorna todos los movimientos de inventario asociados al producto ordenados por fecha descendente.
        
        WARNING: PERFORMANCE BIBLE:
        - Usa select_related('producto') para evitar N+1
        - Solo campos necesarios para serializer (MOVIMIENTO_LIST_FIELDS)
        - Producto solo campos necesarios (id, codigo, nombre, stock_actual)
        """
        from apps.tenant.inventario.api.serializers import MovimientoInventarioListSerializer
        pk = self.kwargs.get('pk')
        empresa = inv_services.get_empresa_singleton()
        producto, movimientos = self.service_producto_get_kardex(empresa, pk)
        
        # Usar serializer optimizado para listas
        serializer = MovimientoInventarioListSerializer(movimientos, many=True)
        
        return Response({
            "producto": {
                "id": producto.id,
                "codigo": producto.codigo,
                "nombre": producto.nombre,
                "stock_actual": producto.stock_actual
            },
            "movimientos": serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        """
        WARNING: REGLA DE SEGURIDAD DE ELIMINACIÓN (Inactivar antes de Borrar):
        - No se puede eliminar un producto activo.
        - El producto debe estar inactivo (activo=False) antes de poder eliminarlo.
        - Al eliminar un producto, se eliminan automáticamente:
          * Todos sus movimientos de inventario (Kardex) - CASCADE
          * El stock se elimina junto con el producto (es parte del registro)
        
        WARNING: STANDALONE MODULE: Este módulo es independiente y no depende de otros módulos.
        
        Returns:
            400 Bad Request si el producto está activo
            204 No Content si se elimina exitosamente
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        instance = self.get_object()
        
        # Validar que el producto no esté activo
        if instance.activo:
            return Response(
                {
                    "error": "active_record",
                    "message": "No se puede eliminar un ítem activo. Cámbielo a 'Inactivo' en el formulario de edición antes de intentar borrarlo."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mantener el ViewSet libre de queries directas a modelos; la eliminacion real
        # y el cascade del kardex permanecen delegados al ORM/model layer.
        stock_actual = instance.stock_actual or 0
        
        # Log informativo (opcional, para auditoria)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Eliminando producto {instance.id} ({instance.codigo} - {instance.nombre}). "
            f"Stock actual: {stock_actual}. "
            "Los movimientos de kardex asociados se eliminaran automaticamente (CASCADE)."
        )
        
        # CASCADE: Django eliminara automaticamente los movimientos al eliminar el producto
        # debido a on_delete=models.CASCADE en el modelo MovimientoInventario
        # El stock se elimina junto con el producto ya que es parte del registro
        return super().destroy(request, *args, **kwargs)
    
    def get_empresa(self):
        """
        v2.60: Zero Trust - Obtiene la empresa del tenant actual.
        """
        return inv_services.get_empresa_singleton()
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        v2.60: Devuelve el HTML del formulario de producto o ajuste de inventario para HTMX Offcanvas via Servicio.
        """
        empresa = self.get_empresa()
        id_instancia = request.query_params.get('id')
        tipo_formulario = request.query_params.get('tipo', 'producto')
        context = self.service_producto_get_offcanvas_context(empresa, id_instancia, tipo_formulario)
        return Response(context, template_name='inventario/offcanvas_producto.html')


class ServicioViewSet(BaseViewSet, inv_services.ServicioServiceMixin):
    """
    v2.61: ViewSet para SERVICIOS con Inyeccion de Servicio.
    """
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ServicioListSerializer
        return ServicioDetailSerializer
    
    def get_queryset(self):
        empresa = inv_services.get_empresa_singleton()
        search = self.request.query_params.get('search', None)
        return inv_services.qs_servicio_list(empresa_id=empresa.id, search=search).order_by('nombre')
    
    def get_object(self):
        empresa = inv_services.get_empresa_singleton()
        return inv_services.qs_servicio_detail(empresa_id=empresa.id, servicio_id=self.kwargs['pk'])
    
    def destroy(self, request, *args, **kwargs):
        """
        Delega la validacion de seguridad (inactivar antes de borrar) al Service Layer.
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        instance = self.get_object()
        try:
            self.service_servicio_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def get_empresa(self):
        return inv_services.get_empresa_singleton()
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        v2.60: Devuelve el HTML del formulario de servicio para HTMX Offcanvas via Servicio.
        """
        empresa = self.get_empresa()
        id_instancia = request.query_params.get('id')
        context = self.service_servicio_get_offcanvas_context(empresa, id_instancia)
        return Response(context, template_name='inventario/offcanvas_servicio.html')
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='historial-offcanvas')
    def historial_offcanvas(self, request):
        """
        v2.60: Devuelve el HTML del formulario de historial de servicio para HTMX Offcanvas via Servicio.
        """
        empresa = self.get_empresa()
        context = self.service_servicio_get_historial_context(empresa)
        return Response(context, template_name='inventario/offcanvas_historial_servicio.html')

    @action(detail=False, methods=["get", "post"], url_path="dt")
    def datatables(self, request):
        """
        DEPRECATED v2.40: Endpoint legacy para DataTables Server-Side.
        """
        from apps.shared.datatable import DataTableServer, DataTableSpec
        from apps.tenant.inventario.api.serializers import ServicioListSerializer
        from apps.tenant.inventario import services as inv_services
        
        empresa = inv_services.get_empresa_singleton()
        qs_base = inv_services.qs_servicio_list(empresa_id=empresa.id)
        
        spec = DataTableSpec(
            fields_map={
                0: 'codigo',
                1: 'nombre',
                2: 'categoria__nombre',
                3: 'precio_venta',
                4: 'activo'
            },
            search_fields=['codigo', 'nombre', 'categoria__nombre'],
            base_qs=qs_base,
            serializer=ServicioListSerializer,
            extra_filter=lambda req, qs: qs
        )
        
        dt_server = DataTableServer(spec)
        return dt_server.handle(request)


class ActivoFijoViewSet(BaseViewSet, inv_services.ActivoFijoServiceMixin):
    """
    v2.61: ViewSet para ACTIVOS FIJOS con Inyeccion de Servicio.
    """
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ActivoFijoListSerializer
        return ActivoFijoDetailSerializer
    
    def get_queryset(self):
        empresa = inv_services.get_empresa_singleton()
        search = self.request.query_params.get('search', None)
        return inv_services.qs_activo_list(empresa_id=empresa.id, search=search).order_by('nombre')
    
    def get_object(self):
        empresa = inv_services.get_empresa_singleton()
        return inv_services.qs_activo_detail(empresa_id=empresa.id, activo_id=self.kwargs['pk'])
    
    def destroy(self, request, *args, **kwargs):
        """
        Delega la eliminacion al Service Layer.
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        instance = self.get_object()
        self.service_activo_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'], url_path="list-all")
    def list_all(self, request):
        """
        v2.40: Endpoint optimizado para Client-Side DataTables via Servicio.
        """
        empresa = inv_services.get_empresa_singleton()
        serializer_data = self.service_activo_list_all(empresa)
        return Response(serializer_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        v2.60: Devuelve el HTML del formulario de activo fijo para HTMX Offcanvas via Servicio.
        """
        empresa = inv_services.get_empresa_singleton()
        id_instancia = request.query_params.get('id')
        context = self.service_activo_get_offcanvas_context(empresa, id_instancia)
        return Response(context, template_name='inventario/offcanvas_activo.html')


class MovimientoInventarioViewSet(BaseViewSet, inv_services.MovimientoServiceMixin):
    """
    v2.61: ViewSet para KARDEX con Inyeccion de Servicio.
    """
    
    def get_serializer_class(self):
        if self.action == 'list':
            return MovimientoInventarioListSerializer
        return MovimientoInventarioSerializer
    
    def get_queryset(self):
        empresa = inv_services.get_empresa_singleton()
        search = self.request.query_params.get('search', None)
        return inv_services.qs_movimiento_list(empresa.id, search=search).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """
        GET /api/v1/inventario/movimientos/
        Lista paginada de movimientos de inventario (Tabulator).
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=["get"], renderer_classes=[TemplateHTMLRenderer], url_path="gestor-offcanvas")
    def gestor_offcanvas(self, request):
        """
        GET /api/v1/inventario/movimientos/gestor-offcanvas/
        Devuelve el HTML del formulario de movimiento para HTMX Offcanvas.
        """
        empresa = inv_services.get_empresa_singleton()
        context = self.service_movimiento_get_offcanvas_context(empresa)
        return Response(context, template_name='inventario/offcanvas_movimiento.html')
    
    @action(detail=False, methods=["get", "post"], url_path="dt")
    def datatables(self, request):
        """
        DEPRECATED v2.40: Endpoint legacy para DataTables Server-Side.
        """
        from apps.shared.datatable import DataTableServer, DataTableSpec
        from apps.tenant.inventario.api.serializers import MovimientoInventarioListSerializer
        from apps.tenant.inventario import services as inv_services
        
        empresa = inv_services.get_empresa_singleton()
        qs_base = inv_services.qs_movimiento_list(empresa_id=empresa.id)
        
        spec = DataTableSpec(
            fields_map={
                0: 'created_at',
                1: 'producto__codigo',
                2: 'producto__nombre',
                3: 'tipo',
                4: 'cantidad',
                5: 'origen_referencia',
                6: 'observaciones'
            },
            search_fields=['producto__codigo', 'producto__nombre', 'origen_referencia', 'observaciones'],
            base_qs=qs_base,
            serializer=MovimientoInventarioListSerializer,
            extra_filter=lambda req, qs: qs
        )
        
        dt_server = DataTableServer(spec)
        return dt_server.handle(request)

    def perform_create(self, serializer):
        """
        v2.40: Crea movimiento y recalcula stock automaticamente usando Service Layer.
        """
        empresa = inv_services.get_empresa_singleton()
        self.service_movimiento_perform_create(serializer, empresa)


class HistorialServicioViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet,
    inv_services.HistorialServiceMixin
):
    """
    ViewSet para Historial de Servicios via Service Layer.
    """
    serializer_class = HistorialServicioSerializer
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser]
    
    def get_queryset(self):
        """
        v2.61: Usa QuerySet optimizado del Service Layer.
        """
        empresa = inv_services.get_empresa_singleton()
        return self.service_historial_get_queryset(empresa)

    def perform_create(self, serializer):
        """
        v2.60: Asigna empresa singleton via Servicio.
        """
        empresa = inv_services.get_empresa_singleton()
        serializer.save(empresa=empresa)