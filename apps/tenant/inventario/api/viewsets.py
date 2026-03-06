from decimal import Decimal
from rest_framework import viewsets, permissions, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import APIException
from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404

# Nuevos Modelos
from apps.tenant.inventario.models import (
    CategoriaItem, ActivoFijo, Producto, Servicio, 
    MovimientoInventario, HistorialServicio
)
from apps.tenant.empresa.models import Empresa
from apps.tenant.api.permissions import IsTenantAdminOrReadOnly
from apps.tenant.empresa.permissions import IsTenantAdmin

# Nuevos Serializers
from .serializers import (
    # ⚠️ v2.60: Serializers List/Detail explícitos
    CategoriaItemListSerializer, CategoriaItemDetailSerializer,
    ProductoListSerializer, ProductoDetailSerializer,
    ServicioListSerializer, ServicioDetailSerializer,
    ActivoFijoListSerializer, ActivoFijoDetailSerializer,
    MovimientoInventarioListSerializer, MovimientoInventarioDetailSerializer,
    HistorialServicioDetailSerializer,
    StockResponseSerializer,
    # ⚠️ v2.60: Aliases para compatibilidad
    CategoriaItemSerializer, ProductoSerializer, ServicioSerializer,
    ActivoFijoSerializer, MovimientoInventarioSerializer, HistorialServicioSerializer
)

# En dev: usar UnsafeSessionAuthentication si existe (CSRF relajado).
try:
    from apps.tenant.api.authentication import UnsafeSessionAuthentication
    _UnsafeSessionAuthentication = UnsafeSessionAuthentication
except Exception:
    _UnsafeSessionAuthentication = None


class StandardResultsSetPagination(PageNumberPagination):
    """
    ⚠️ v2.40: Paginación estándar para Tabulator.
    Tabulator espera: {count, next, previous, results: [...]}
    """
    page_size = 10  # Default: 10 (estándar SaaS)
    page_size_query_param = 'page_size'
    max_page_size = 100


class BaseViewSet(viewsets.GenericViewSet, 
                   mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.CreateModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.DestroyModelMixin):
    """
    ⚠️ v2.60: ViewSet base para inventario usando GenericViewSet con mixins específicos.
    
    SINTEL v2.60: Sincronización Arquitectónica
    - GenericViewSet: Base flexible con mixins específicos (List, Retrieve, Create, Update, Destroy)
    - ENFORCED MODE: Validación de permisos para mutaciones
    - Asignación de Empresa (SSoT): Automática en perform_create()
    - Formato DRF {count, results}: Garantizado en list() para Tabulator Factory
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsTenantAdminOrReadOnly]
    # Se agrega MultiPartParser para permitir subida de imágenes
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]
    pagination_class = StandardResultsSetPagination

    def get_authenticators(self):
        if settings.DEBUG and _UnsafeSessionAuthentication:
            return [_UnsafeSessionAuthentication()]
        return super().get_authenticators()
    
    def _check_enforced_mode(self, request):
        """
        ⚠️ v2.60: Verifica si el usuario tiene permisos para mutaciones (ENFORCED MODE).
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
        ⚠️ v2.60: Asigna automáticamente la Empresa (SSoT) al crear un registro.
        Asume que existe una única empresa por esquema tenant.
        
        ⚠️ PERFORMANCE BIBLE: Usar .only('id') para obtener empresa singleton
        """
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            # Fallback de seguridad, aunque en tenant siempre debería haber una
            raise ValueError("No se encontró configuración de Empresa para este tenant.")
        serializer.save(empresa=empresa)
    
    def list(self, request, *args, **kwargs):
        """
        ⚠️ v2.60: Listado paginado con formato DRF {count, results} para Tabulator Factory.
        Garantiza que siempre retorne el formato estándar DRF compatible con Tabulator Factory.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # ⚠️ v2.60: get_paginated_response() retorna formato DRF estándar: {count, next, previous, results}
            return self.get_paginated_response(serializer.data)
        
        # Si no hay paginación, retornar formato compatible
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


class CategoriaItemViewSet(BaseViewSet):
    """
    ⚠️ v2.60: ViewSet para CATEGORÍAS de Inventario.
    
    SINTEL v2.60: Sincronización Arquitectónica
    - GenericViewSet con mixins específicos (List, Retrieve, Create, Update, Destroy)
    - Filtra automáticamente por empresa (SSoT - Zero Trust)
    - Usa qs_categoria_list() y qs_categoria_detail() del service layer
    - Serializers List/Detail explícitos
    - Formato DRF {count, results} garantizado en list()
    """
    
    def get_serializer_class(self):
        """
        ⚠️ v2.60: Selecciona el serializer según la acción.
        - list: CategoriaItemListSerializer (campos mínimos para tabla)
        - retrieve/create/update: CategoriaItemDetailSerializer (campos completos para formulario)
        """
        if self.action == 'list':
            return CategoriaItemListSerializer
        return CategoriaItemDetailSerializer
    
    def get_queryset(self):
        """
        ⚠️ v2.60: QuerySet optimizado usando qs_categoria_list() del service layer.
        Filtra por empresa (SSoT - Zero Trust) y aplica búsqueda si se proporciona.
        
        ⚠️ PERFORMANCE BIBLE: Usar .only('id') para obtener empresa singleton
        """
        from apps.tenant.inventario.services import qs_categoria_list
        
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            return CategoriaItem.objects.none()
        
        search = self.request.query_params.get('search', None)
        # ⚠️ v2.60: Usar qs_categoria_list() del service layer (ya incluye empresa_id y search)
        qs = qs_categoria_list(empresa_id=empresa.id, search=search)
        
        return qs.order_by('nombre')
    
    def get_object(self):
        """
        ⚠️ v2.60: Obtiene objeto usando qs_categoria_detail() del service layer.
        Garantiza que el objeto pertenezca al tenant (Zero Trust).
        """
        from apps.tenant.inventario.services import qs_categoria_detail
        
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise CategoriaItem.DoesNotExist("No se encontró configuración de Empresa para este tenant.")
        
        return qs_categoria_detail(empresa_id=empresa.id, categoria_id=self.kwargs['pk'])
    
    def get_empresa(self):
        """
        ⚠️ v2.60: Zero Trust - Obtiene la empresa del tenant actual.
        """
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise APIException("No se encontró configuración de Empresa para este tenant.")
        return empresa
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        ⚠️ v2.60: Devuelve el HTML del formulario de categoría para HTMX Offcanvas.
        
        Endpoint: GET /api/v1/inventario/categorias/gestor-offcanvas/
        
        Query params:
        - id: ID de la categoría (opcional - si no se proporciona, es modo creación)
        
        Returns:
            Template HTML renderizado con contexto de la categoría
        """
        # ⚠️ Zero Trust: Obtener empresa del tenant actual
        empresa = self.get_empresa()
        
        categoria = None
        id_instancia = request.query_params.get('id')
        
        if id_instancia:
            # ⚠️ Zero Trust: Validar que la categoría pertenezca al tenant
            categoria = get_object_or_404(
                self.get_queryset(),
                id=id_instancia
            )
        
        template_name = 'tenant/core/partials/inventario/categorias_offcanvas.html'
        
        context = {
            'categoria': categoria,
            'empresa': empresa,
        }
        
        return Response(context, template_name=template_name)
    
    @action(detail=False, methods=["get", "post"], url_path="dt")
    def datatables(self, request):
        """
        ⚠️ v2.40: DataTables CLIENT-SIDE para Categorías.
        Retorna TODAS las categorías sin paginación para filtrado instantáneo en frontend.
        Usa CategoriaItemListSerializer optimizado (solo campos necesarios para tabla).
        
        ⚠️ FORMATO: Retorna {"data": [...]} para compatibilidad con DataTables client-side.
        """
        from apps.tenant.inventario.services import qs_categoria_list
        
        # Usar QuerySet optimizado del service layer
        qs = qs_categoria_list()
        
        # ⚠️ PERFORMANCE BIBLE: Usar .only('id') para obtener empresa singleton
        empresa = Empresa.objects.only('id').first()
        if empresa:
            qs = qs.filter(empresa=empresa)
        
        # Ordenar por nombre por defecto
        qs = qs.order_by('nombre')
        
        # ⚠️ CRÍTICO: Usar serializer de lista optimizado
        serializer = CategoriaItemListSerializer(qs, many=True)
        
        # Retornar formato simple para client-side DataTables
        return Response({"data": serializer.data})
    
    def destroy(self, request, *args, **kwargs):
        """
        ⚠️ REGLA DE SEGURIDAD DE ELIMINACIÓN (Inactivar antes de Borrar):
        - No se puede eliminar una categoría activa.
        - La categoría debe estar inactiva (activo=False) antes de poder eliminarla.
        - Al eliminar una categoría, los productos, servicios y activos asociados quedan sin categoría (null).
          Esto es equivalente a "eliminar el kardex de categorías" - los ítems quedan sin categoría asignada.
        
        ⚠️ STANDALONE MODULE: Este módulo es completamente independiente.
        - No depende de otros módulos del inventario
        - Los ítems (productos, servicios, activos) pueden tener o no categoría asignada (null=True)
        - Al eliminar una categoría, los ítems asociados simplemente quedan sin categoría
        
        Returns:
            400 Bad Request si la categoría está activa
            204 No Content si se elimina exitosamente
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        instance = self.get_object()
        
        # Validar que la categoría no esté activa
        if instance.activo:
            return Response(
                {
                    "error": "active_category",
                    "message": "No se puede eliminar una categoría activa. Desactívela primero."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ⚠️ ESTABLECER CATEGORÍA A NULL: Antes de eliminar, establecer la categoría de los ítems asociados a null
        # Esto permite eliminar la categoría sin bloquear por PROTECT
        try:
            conteo_productos = Producto.objects.filter(categoria=instance).update(categoria=None)
            conteo_servicios = Servicio.objects.filter(categoria=instance).update(categoria=None)
            conteo_activos = ActivoFijo.objects.filter(categoria=instance).update(categoria=None)
            
            # Log informativo (opcional, para auditoría)
            if conteo_productos > 0 or conteo_servicios > 0 or conteo_activos > 0:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(
                    f"Eliminando categoría {instance.id} ({instance.nombre}). "
                    f"Ítems afectados: {conteo_productos} productos, {conteo_servicios} servicios, {conteo_activos} activos. "
                    f"Sus categorías fueron establecidas a null."
                )
        except Exception as e:
            # Si hay un error al actualizar (ej: columna no permite NULL), registrar y retornar error
            import logging
            from django.db import DatabaseError, IntegrityError
            
            logger = logging.getLogger(__name__)
            error_msg = str(e)
            
            # Detectar si es un error de restricción NOT NULL
            if 'null' in error_msg.lower() or 'not null' in error_msg.lower() or isinstance(e, (DatabaseError, IntegrityError)):
                mensaje_usuario = (
                    "Error: La base de datos no permite valores NULL en la columna 'categoria'. "
                    "Esto indica que la migración no se ha aplicado. "
                    "Por favor, ejecute: python manage.py makemigrations tenant_inventario && python manage.py migrate"
                )
            else:
                mensaje_usuario = f"Error al actualizar ítems asociados: {error_msg}"
            
            logger.error(
                f"Error al establecer categoría a null antes de eliminar categoría {instance.id}: {e}",
                exc_info=True
            )
            return Response(
                {
                    "error": "update_failed",
                    "message": mensaje_usuario
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as e:
            # Capturar errores durante la eliminación
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Error al eliminar categoría {instance.id}: {e}",
                exc_info=True
            )
            return Response(
                {
                    "error": "delete_failed",
                    "message": f"Error al eliminar la categoría: {str(e)}"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='resumen')
    def resumen(self, request, pk=None):
        """
        ⚠️ v2.40: Retorna un resumen con el conteo de productos/servicios/activos asociados a esta categoría.
        
        Returns:
            {
                "id": int,
                "nombre": str,
                "activo": bool,
                "conteo_productos": int,
                "conteo_servicios": int,
                "conteo_activos": int,
                "total_items": int
            }
        """
        instance = self.get_object()
        
        # ⚠️ PERFORMANCE BIBLE: Usar .count() directamente (más eficiente que len())
        conteo_productos = Producto.objects.filter(categoria=instance).count()
        conteo_servicios = Servicio.objects.filter(categoria=instance).count()
        conteo_activos = ActivoFijo.objects.filter(categoria=instance).count()
        
        return Response({
            "id": instance.id,
            "nombre": instance.nombre,
            "activo": instance.activo,
            "conteo_productos": conteo_productos,
            "conteo_servicios": conteo_servicios,
            "conteo_activos": conteo_activos,
            "total_items": conteo_productos + conteo_servicios + conteo_activos
        })


class ProductoViewSet(BaseViewSet):
    """
    ⚠️ v2.60: ViewSet para PRODUCTOS (Bienes tangibles con Stock).
    
    SINTEL v2.60: Sincronización Arquitectónica
    - GenericViewSet con mixins específicos (List, Retrieve, Create, Update, Destroy)
    - Filtra automáticamente por empresa (SSoT - Zero Trust)
    - Usa qs_producto_list() y qs_producto_detail() del service layer
    - Serializers List/Detail explícitos
    - Formato DRF {count, results} garantizado en list()
    """
    queryset = Producto.objects.none()  # ⚠️ v2.60: Solo para DRF, se sobrescribe en get_queryset()
    
    def get_serializer_class(self):
        """
        ⚠️ v2.60: Selecciona el serializer según la acción.
        - list: ProductoListSerializer (campos mínimos para tabla)
        - retrieve/create/update: ProductoDetailSerializer (campos completos para formulario)
        """
        if self.action == 'list':
            return ProductoListSerializer
        return ProductoDetailSerializer
    
    def get_queryset(self):
        """
        ⚠️ v2.60: QuerySet optimizado usando qs_producto_list() del service layer.
        Filtra por empresa (SSoT - Zero Trust) y aplica búsqueda si se proporciona.
        
        ⚠️ PERFORMANCE BIBLE: Siempre filtrar por empresa (SSoT) - PROHIBIDO .all()
        """
        from apps.tenant.inventario.services import qs_producto_list
        
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            return Producto.objects.none()
        
        search = self.request.query_params.get('search', None)
        # ⚠️ v2.60: Usar qs_producto_list() del service layer
        return qs_producto_list(empresa_id=empresa.id, search=search).order_by('nombre')
    
    def get_object(self):
        """
        ⚠️ v2.60: Obtiene objeto usando qs_producto_detail() del service layer.
        Garantiza que el objeto pertenezca al tenant (Zero Trust).
        """
        from apps.tenant.inventario.services import qs_producto_detail
        
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise Producto.DoesNotExist("No se encontró configuración de Empresa para este tenant.")
        
        return qs_producto_detail(empresa_id=empresa.id, producto_id=self.kwargs['pk'])

    @action(detail=False, methods=["get", "post"], url_path="dt")
    def datatables(self, request):
        """
        ⚠️ DEPRECATED v2.40: Endpoint legacy para DataTables Server-Side.
        Ya no se usa - Tabulator Factory consume GET /api/v1/inventario/productos/ directamente.
        Se mantiene por compatibilidad temporal, pero será eliminado en v2.50.
        
        ⚠️ v2.40: DataTables SERVER-SIDE para Productos.
        Retorna datos paginados en formato estándar DataTables server-side.
        Usa DataTableServer helper para procesamiento seguro.
        """
        from apps.shared.datatable import DataTableSpec, DataTableServer
        from apps.tenant.inventario.services import qs_producto_list
        from apps.tenant.inventario.api.serializers import ProductoListSerializer
        
        # QuerySet base optimizado
        qs_base = qs_producto_list()
        
        # ⚠️ PERFORMANCE BIBLE: Usar .only('id') para obtener empresa singleton
        empresa = Empresa.objects.only('id').first()
        if empresa:
            qs_base = qs_base.filter(empresa=empresa)
        
        # ⚠️ CRÍTICO: fields_map debe coincidir EXACTAMENTE con el orden de columnas en inventario.page.js
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
        
        ⚠️ PERFORMANCE BIBLE: Solo campos necesarios (id, nombre, stock_actual)
        """
        # ⚠️ CRÍTICO: Solo obtener campos necesarios - evitar get_object() que trae todos los campos
        pk = self.kwargs.get('pk')
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            from rest_framework.exceptions import NotFound
            raise NotFound('Empresa no encontrada')
        
        producto = Producto.objects.filter(empresa=empresa, pk=pk).only('id', 'nombre', 'stock_actual').first()
        if not producto:
            from rest_framework.exceptions import NotFound
            raise NotFound('Producto no encontrado')
        
        serializer = StockResponseSerializer({
            "id": producto.id,
            "nombre": producto.nombre,
            "stock_actual": producto.stock_actual
        })
        return Response(serializer.data)
    
    @action(detail=True, methods=["get"], url_path="kardex")
    def kardex(self, request, pk=None):
        """
        ⚠️ v2.40: Endpoint para obtener el historial de movimientos (Kardex) de un producto específico.
        Retorna todos los movimientos de inventario asociados al producto ordenados por fecha descendente.
        
        ⚠️ PERFORMANCE BIBLE:
        - Usa select_related('producto') para evitar N+1
        - Solo campos necesarios para serializer (MOVIMIENTO_LIST_FIELDS)
        - Producto solo campos necesarios (id, codigo, nombre, stock_actual)
        """
        from apps.tenant.inventario.models import MovimientoInventario
        from apps.tenant.inventario.api.serializers import MovimientoInventarioListSerializer
        from apps.tenant.inventario.services import MOVIMIENTO_LIST_FIELDS
        
        # ⚠️ CRÍTICO: Solo obtener campos necesarios del producto
        pk = self.kwargs.get('pk')
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            from rest_framework.exceptions import NotFound
            raise NotFound('Empresa no encontrada')
        
        producto = Producto.objects.filter(empresa=empresa, pk=pk).only('id', 'codigo', 'nombre', 'stock_actual').first()
        if not producto:
            from rest_framework.exceptions import NotFound
            raise NotFound('Producto no encontrado')
        
        # ⚠️ PERFORMANCE BIBLE: select_related + only() para evitar N+1 y SELECT *
        movimientos = MovimientoInventario.objects.filter(producto=producto)\
            .select_related('producto')\
            .only(*MOVIMIENTO_LIST_FIELDS)\
            .order_by('-created_at')
        
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
        ⚠️ REGLA DE SEGURIDAD DE ELIMINACIÓN (Inactivar antes de Borrar):
        - No se puede eliminar un producto activo.
        - El producto debe estar inactivo (activo=False) antes de poder eliminarlo.
        - Al eliminar un producto, se eliminan automáticamente:
          * Todos sus movimientos de inventario (Kardex) - CASCADE
          * El stock se elimina junto con el producto (es parte del registro)
        
        ⚠️ STANDALONE MODULE: Este módulo es independiente y no depende de otros módulos.
        
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
        
        # ⚠️ ELIMINAR MOVIMIENTOS Y STOCK: Contar movimientos antes de eliminar para logging
        conteo_movimientos = MovimientoInventario.objects.filter(producto=instance).count()
        stock_actual = instance.stock_actual or 0
        
        # Log informativo (opcional, para auditoría)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Eliminando producto {instance.id} ({instance.codigo} - {instance.nombre}). "
            f"Stock actual: {stock_actual}. "
            f"Se eliminarán {conteo_movimientos} movimiento(s) de kardex automáticamente (CASCADE)."
        )
        
        # ⚠️ CASCADE: Django eliminará automáticamente los movimientos al eliminar el producto
        # debido a on_delete=models.CASCADE en el modelo MovimientoInventario
        # El stock se elimina junto con el producto ya que es parte del registro
        return super().destroy(request, *args, **kwargs)
    
    def get_empresa(self):
        """
        ⚠️ v2.60: Zero Trust - Obtiene la empresa del tenant actual.
        """
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise APIException("No se encontró configuración de Empresa para este tenant.")
        return empresa
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        ⚠️ v2.60: Devuelve el HTML del formulario de producto o ajuste de inventario para HTMX Offcanvas.
        
        Endpoint: GET /api/v1/inventario/productos/gestor-offcanvas/
        
        Query params:
        - id: ID del producto (opcional - si no se proporciona, es modo creación)
        - tipo: Tipo de formulario ('producto' o 'ajuste'). Default: 'producto'
        
        Returns:
            Template HTML renderizado con contexto del producto y catálogos necesarios
        """
        # ⚠️ Zero Trust: Obtener empresa del tenant actual
        empresa = self.get_empresa()
        
        producto = None
        id_instancia = request.query_params.get('id')
        tipo_formulario = request.query_params.get('tipo', 'producto')  # 'producto' o 'ajuste'
        
        if id_instancia:
            # ⚠️ Zero Trust: Validar que el producto pertenezca al tenant
            producto = get_object_or_404(
                self.get_queryset(),
                id=id_instancia
            )
        
        # ⚠️ Catálogos: Cargar lista de categorías para el select
        categorias = []
        try:
            from apps.tenant.inventario.models import CategoriaItem
            categorias = CategoriaItem.objects.filter(
                empresa_id=empresa.id,
                activo=True
            ).only('id', 'nombre', 'aplicacion').order_by('nombre')[:100]
        except Exception:
            # Si hay error, continuar sin catálogo
            pass
        
        # ⚠️ Tipos de movimiento para el formulario de ajuste
        tipos_movimiento = []
        if tipo_formulario == 'ajuste':
            from apps.tenant.inventario.models import MovimientoInventario
            tipos_movimiento = MovimientoInventario.TipoMovimiento.choices
        
        # Usar el template unificado
        template_name = 'tenant/core/partials/inventario/offcanvas_form.html'
        
        context = {
            'producto': producto,
            'categorias': categorias,
            'tipo_formulario': tipo_formulario,
            'empresa': empresa,
            'tipos_movimiento': tipos_movimiento,
        }
        
        return Response(context, template_name=template_name)


class ServicioViewSet(BaseViewSet):
    """
    ⚠️ v2.60: ViewSet para SERVICIOS (Bienes intangibles sin Stock).
    
    SINTEL v2.60: Sincronización Arquitectónica
    - GenericViewSet con mixins específicos (List, Retrieve, Create, Update, Destroy)
    - Filtra automáticamente por empresa (SSoT - Zero Trust)
    - Usa qs_servicio_list() y qs_servicio_detail() del service layer
    - Serializers List/Detail explícitos
    - Formato DRF {count, results} garantizado en list()
    """
    queryset = Servicio.objects.none()  # ⚠️ v2.60: Solo para DRF, se sobrescribe en get_queryset()
    
    def get_serializer_class(self):
        """
        ⚠️ v2.60: Selecciona el serializer según la acción.
        - list: ServicioListSerializer (campos mínimos para tabla)
        - retrieve/create/update: ServicioDetailSerializer (campos completos para formulario)
        """
        if self.action == 'list':
            return ServicioListSerializer
        return ServicioDetailSerializer
    
    def get_queryset(self):
        """
        ⚠️ v2.60: QuerySet optimizado usando qs_servicio_list() del service layer.
        Filtra por empresa (SSoT - Zero Trust) y aplica búsqueda si se proporciona.
        
        ⚠️ PERFORMANCE BIBLE: Siempre filtrar por empresa (SSoT) - PROHIBIDO .all()
        """
        from apps.tenant.inventario.services import qs_servicio_list
        
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            return Servicio.objects.none()
        
        search = self.request.query_params.get('search', None)
        # ⚠️ v2.60: Usar qs_servicio_list() del service layer
        return qs_servicio_list(empresa_id=empresa.id, search=search).order_by('nombre')
    
    def get_object(self):
        """
        ⚠️ v2.60: Obtiene objeto usando qs_servicio_detail() del service layer.
        Garantiza que el objeto pertenezca al tenant (Zero Trust).
        """
        from apps.tenant.inventario.services import qs_servicio_detail
        
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise Servicio.DoesNotExist("No se encontró configuración de Empresa para este tenant.")
        
        return qs_servicio_detail(empresa_id=empresa.id, servicio_id=self.kwargs['pk'])
    
    def get_empresa(self):
        """
        ⚠️ v2.60: Zero Trust - Obtiene la empresa del tenant actual.
        """
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise APIException("No se encontró configuración de Empresa para este tenant.")
        return empresa
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        ⚠️ v2.60: Devuelve el HTML del formulario de servicio para HTMX Offcanvas.
        
        Endpoint: GET /api/v1/inventario/servicios/gestor-offcanvas/
        
        Query params:
        - id: ID del servicio (opcional - si no se proporciona, es modo creación)
        
        Returns:
            Template HTML renderizado con contexto del servicio y catálogos necesarios
        """
        # ⚠️ Zero Trust: Obtener empresa del tenant actual
        empresa = self.get_empresa()
        
        servicio = None
        id_instancia = request.query_params.get('id')
        
        if id_instancia:
            # ⚠️ Zero Trust: Validar que el servicio pertenezca al tenant
            servicio = get_object_or_404(
                self.get_queryset(),
                id=id_instancia
            )
        
        # ⚠️ Catálogos: Cargar lista de categorías para el select
        categorias = []
        try:
            from apps.tenant.inventario.models import CategoriaItem
            categorias = CategoriaItem.objects.filter(
                empresa_id=empresa.id,
                activo=True,
                aplicacion__in=[CategoriaItem.Aplicacion.SERVICIO, CategoriaItem.Aplicacion.TODO]
            ).only('id', 'nombre', 'aplicacion').order_by('nombre')[:100]
        except Exception:
            # Si hay error, continuar sin catálogo
            pass
        
        template_name = 'tenant/core/partials/inventario/servicios_offcanvas.html'
        
        context = {
            'servicio': servicio,
            'categorias': categorias,
            'empresa': empresa,
        }
        
        return Response(context, template_name=template_name)
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='historial-offcanvas')
    def historial_offcanvas(self, request):
        """
        ⚠️ v2.60: Devuelve el HTML del formulario de historial de servicio para HTMX Offcanvas.
        
        Endpoint: GET /api/v1/inventario/servicios/historial-offcanvas/
        
        Returns:
            Template HTML renderizado con contexto para el formulario de historial
        """
        # ⚠️ Zero Trust: Obtener empresa del tenant actual
        empresa = self.get_empresa()
        
        template_name = 'tenant/core/partials/inventario/historial_servicio_offcanvas.html'
        
        context = {
            'empresa': empresa,
        }
        
        return Response(context, template_name=template_name)

    @action(detail=False, methods=["get", "post"], url_path="dt")
    def datatables(self, request):
        """
        ⚠️ DEPRECATED v2.40: Endpoint legacy para DataTables Server-Side.
        Ya no se usa - Tabulator Factory consume GET /api/v1/inventario/servicios/ directamente.
        Se mantiene por compatibilidad temporal, pero será eliminado en v2.50.
        
        ⚠️ v2.40: DataTables SERVER-SIDE para Servicios.
        Retorna datos paginados en formato estándar DataTables server-side.
        Usa DataTableServer helper para procesamiento seguro.
        """
        from apps.shared.datatable import DataTableSpec, DataTableServer
        from apps.tenant.inventario.services import qs_servicio_list
        from apps.tenant.inventario.api.serializers import ServicioListSerializer
        
        # QuerySet base optimizado
        qs_base = qs_servicio_list()
        
        # ⚠️ PERFORMANCE BIBLE: Usar .only('id') para obtener empresa singleton
        empresa = Empresa.objects.only('id').first()
        if empresa:
            qs_base = qs_base.filter(empresa=empresa)
        
        # ⚠️ CRÍTICO: fields_map debe coincidir EXACTAMENTE con el orden de columnas en inventario.page.js
        # Columnas: 0=codigo, 1=nombre, 2=categoria_nombre, 3=precio_venta, 4=activo, 5=Acciones (no ordenable)
        spec = DataTableSpec(
            fields_map={
                0: 'codigo',
                1: 'nombre',
                2: 'categoria__nombre',  # Serializer expone como categoria_nombre, pero en DB es categoria__nombre
                3: 'precio_venta',
                4: 'activo'
            },
            search_fields=['codigo', 'nombre', 'categoria__nombre'],
            base_qs=qs_base,
            serializer=ServicioListSerializer,
            extra_filter=lambda req, qs: qs  # Sin filtros adicionales
        )
        
        # Procesar request DataTables
        dt_server = DataTableServer(spec)
        return dt_server.handle(request)
    
    def destroy(self, request, *args, **kwargs):
        """
        ⚠️ REGLA DE SEGURIDAD DE ELIMINACIÓN (Inactivar antes de Borrar):
        - No se puede eliminar un servicio activo.
        - El servicio debe estar inactivo (activo=False) antes de poder eliminarlo.
        - Al eliminar un servicio, se eliminan automáticamente:
          * Todos sus historiales de ventas - CASCADE
        
        ⚠️ STANDALONE MODULE: Este módulo es independiente y no depende de otros módulos.
        
        Returns:
            400 Bad Request si el servicio está activo
            204 No Content si se elimina exitosamente
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        instance = self.get_object()
        
        # Validar que el servicio no esté activo
        if instance.activo:
            return Response(
                {
                    "error": "active_record",
                    "message": "No se puede eliminar un ítem activo. Cámbielo a 'Inactivo' en el formulario de edición antes de intentar borrarlo."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ⚠️ ELIMINAR HISTORIALES: Contar historiales antes de eliminar para logging
        conteo_historiales = HistorialServicio.objects.filter(servicio=instance).count()
        
        # Log informativo (opcional, para auditoría)
        if conteo_historiales > 0:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"Eliminando servicio {instance.id} ({instance.codigo} - {instance.nombre}). "
                f"Se eliminarán {conteo_historiales} historial(es) de ventas automáticamente (CASCADE)."
            )
        
        # ⚠️ CASCADE: Django eliminará automáticamente los historiales al eliminar el servicio
        # debido a on_delete=models.CASCADE en el modelo HistorialServicio
        return super().destroy(request, *args, **kwargs)


class ActivoFijoViewSet(BaseViewSet):
    """
    ViewSet para ACTIVOS FIJOS.
    
    ⚠️ v2.40: Migrado a Tabulator Factory - usa StandardResultsSetPagination.
    
    ⚠️ PERFORMANCE BIBLE:
    - PROHIBIDO .all(): get_queryset() filtra por empresa (SSoT)
    - queryset base solo para DRF, se sobrescribe en get_queryset()
    """
    # ⚠️ NOTA: Este queryset es solo para DRF, se sobrescribe en get_queryset()
    queryset = ActivoFijo.objects.none()
    serializer_class = ActivoFijoSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_serializer_class(self):
        """
        ⚠️ v2.60: Selecciona el serializer según la acción.
        - list: ActivoFijoListSerializer (campos mínimos para tabla)
        - retrieve/create/update: ActivoFijoDetailSerializer (campos completos para formulario)
        """
        if self.action == 'list':
            return ActivoFijoListSerializer
        return ActivoFijoDetailSerializer
    
    def get_queryset(self):
        """
        ⚠️ v2.60: QuerySet optimizado usando qs_activo_list() del service layer.
        Filtra por empresa (SSoT - Zero Trust) y aplica búsqueda si se proporciona.
        
        ⚠️ PERFORMANCE BIBLE: Siempre filtrar por empresa (SSoT) - PROHIBIDO .all()
        """
        from apps.tenant.inventario.services import qs_activo_list
        
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            return ActivoFijo.objects.none()
        
        search = self.request.query_params.get('search', None)
        # ⚠️ v2.60: Usar qs_activo_list() del service layer
        return qs_activo_list(empresa_id=empresa.id, search=search).order_by('nombre')
    
    def get_object(self):
        """
        ⚠️ v2.60: Obtiene objeto usando qs_activo_detail() del service layer.
        Garantiza que el objeto pertenezca al tenant (Zero Trust).
        """
        from apps.tenant.inventario.services import qs_activo_detail
        
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise ActivoFijo.DoesNotExist("No se encontró configuración de Empresa para este tenant.")
        
        return qs_activo_detail(empresa_id=empresa.id, activo_id=self.kwargs['pk'])
    
    def get_empresa(self):
        """
        ⚠️ v2.60: Zero Trust - Obtiene la empresa del tenant actual.
        """
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise APIException("No se encontró configuración de Empresa para este tenant.")
        return empresa
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        ⚠️ v2.60: Devuelve el HTML del formulario de activo fijo para HTMX Offcanvas.
        
        Endpoint: GET /api/v1/inventario/activos/gestor-offcanvas/
        
        Query params:
        - id: ID del activo (opcional - si no se proporciona, es modo creación)
        
        Returns:
            Template HTML renderizado con contexto del activo y catálogos necesarios
        """
        # ⚠️ Zero Trust: Obtener empresa del tenant actual
        empresa = self.get_empresa()
        
        activo = None
        id_instancia = request.query_params.get('id')
        
        if id_instancia:
            # ⚠️ Zero Trust: Validar que el activo pertenezca al tenant
            activo = get_object_or_404(
                self.get_queryset(),
                id=id_instancia
            )
        
        # ⚠️ Catálogos: Cargar lista de categorías para el select
        categorias = []
        try:
            from apps.tenant.inventario.models import CategoriaItem
            categorias = CategoriaItem.objects.filter(
                empresa_id=empresa.id,
                activo=True,
                aplicacion__in=[CategoriaItem.Aplicacion.ACTIVO, CategoriaItem.Aplicacion.TODO]
            ).only('id', 'nombre', 'aplicacion').order_by('nombre')[:100]
        except Exception:
            # Si hay error, continuar sin catálogo
            pass
        
        template_name = 'tenant/core/partials/inventario/activos_offcanvas.html'
        
        context = {
            'activo': activo,
            'categorias': categorias,
            'empresa': empresa,
        }
        
        return Response(context, template_name=template_name)
    
    def list(self, request, *args, **kwargs):
        """
        GET /api/v1/inventario/activos/
        Lista paginada de activos fijos (Tabulator).
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=["get", "post"], url_path="dt")
    def datatables(self, request):
        """
        ⚠️ DEPRECATED v2.40: Endpoint legacy para DataTables Server-Side.
        Ya no se usa - Tabulator Factory consume GET /api/v1/inventario/activos/ directamente.
        Se mantiene por compatibilidad temporal, pero será eliminado en v2.50.
        
        ⚠️ v2.40: DataTables SERVER-SIDE para Activos Fijos.
        Retorna datos paginados en formato estándar DataTables server-side.
        Usa DataTableServer helper para procesamiento seguro.
        """
        from apps.shared.datatable import DataTableSpec, DataTableServer
        from apps.tenant.inventario.services import qs_activo_list
        from apps.tenant.inventario.api.serializers import ActivoFijoListSerializer
        
        # QuerySet base optimizado
        qs_base = qs_activo_list()
        
        # ⚠️ PERFORMANCE BIBLE: Usar .only('id') para obtener empresa singleton
        empresa = Empresa.objects.only('id').first()
        if empresa:
            qs_base = qs_base.filter(empresa=empresa)
        
        # ⚠️ CRÍTICO: fields_map debe coincidir EXACTAMENTE con el orden de columnas en inventario.page.js
        # Columnas: 0=codigo, 1=nombre, 2=categoria_nombre, 3=ubicacion, 4=responsable, 5=estado, 6=Acciones (no ordenable)
        spec = DataTableSpec(
            fields_map={
                0: 'codigo',
                1: 'nombre',
                2: 'categoria__nombre',  # Serializer expone como categoria_nombre, pero en DB es categoria__nombre
                3: 'ubicacion',
                4: 'responsable',
                5: 'estado'
            },
            search_fields=['codigo', 'nombre', 'categoria__nombre', 'ubicacion', 'responsable'],
            base_qs=qs_base,
            serializer=ActivoFijoListSerializer,
            extra_filter=lambda req, qs: qs  # Sin filtros adicionales
        )
        
        # Procesar request DataTables
        dt_server = DataTableServer(spec)
        return dt_server.handle(request)
    
    def destroy(self, request, *args, **kwargs):
        """
        ⚠️ REGLA DE SEGURIDAD DE ELIMINACIÓN (Inactivar antes de Borrar):
        - No se puede eliminar un activo fijo con estado 'ACTIVO'.
        - El activo debe cambiar su estado (MANTENIMIENTO, BAJA, VENDIDO) antes de poder eliminarlo.
        
        Returns:
            400 Bad Request si el activo está en estado 'ACTIVO'
            204 No Content si se elimina exitosamente
        """
        instance = self.get_object()
        
        # Validar que el activo no esté en estado ACTIVO
        if instance.estado == ActivoFijo.Estado.ACTIVO:
            return Response(
                {
                    "error": "active_record",
                    "message": "No se puede eliminar un ítem activo. Cámbielo a 'Inactivo' en el formulario de edición antes de intentar borrarlo."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'], url_path="list-all")
    def list_all(self, request):
        """
        ⚠️ v2.40: Endpoint optimizado para Client-Side DataTables.
        Retorna TODOS los activos en un array JSON simple (sin paginación DRF).
        Usa QuerySet optimizado del service layer.
        
        ⚠️ FORMATO: Retorna array JSON directo (no objeto con "data").
        DataTables con ajax.dataSrc: '' espera un array directo.
        
        Nota: ActivoFijo no tiene campo 'activo', usa 'estado' (ACTIVO, MANTENIMIENTO, BAJA, VENDIDO).
        Este endpoint retorna todos los activos sin filtrar por estado.
        """
        from apps.tenant.inventario.services import qs_activo_list
        
        # ⚠️ PERFORMANCE BIBLE: Usar .only('id') para obtener empresa singleton
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            return Response([], status=status.HTTP_200_OK)
        
        # ⚠️ CRÍTICO: Usar QuerySet optimizado del service layer
        qs = qs_activo_list().filter(empresa=empresa).order_by('nombre')
        
        # ⚠️ CRÍTICO: Usar serializer de lista optimizado
        serializer = ActivoFijoListSerializer(qs, many=True)
        
        # ⚠️ CRÍTICO: Retornar array JSON simple (no objeto con "data")
        # DataTables con ajax.dataSrc: '' espera un array directo
        return Response(serializer.data, status=status.HTTP_200_OK)


class MovimientoInventarioViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    ViewSet para KARDEX. Solo lectura y creación.
    No permite editar/borrar movimientos para garantizar integridad.
    
    ⚠️ v2.40: Migrado a Tabulator Factory - usa StandardResultsSetPagination.
    
    ⚠️ PERFORMANCE BIBLE:
    - PROHIBIDO .all(): get_queryset() filtra por empresa (SSoT) a través de producto
    - queryset base solo para DRF, se sobrescribe en get_queryset()
    """
    # ⚠️ NOTA: Este queryset es solo para DRF, se sobrescribe en get_queryset()
    queryset = MovimientoInventario.objects.none()
    serializer_class = MovimientoInventarioSerializer
    pagination_class = StandardResultsSetPagination
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser]
    renderer_classes = [JSONRenderer]
    
    def get_serializer_class(self):
        """Selecciona el serializer según la acción."""
        if self.action == 'list':
            return MovimientoInventarioListSerializer
        return MovimientoInventarioSerializer
    
    def get_queryset(self):
        """
        ⚠️ PERFORMANCE BIBLE: Siempre filtrar por empresa (SSoT) - PROHIBIDO .all()
        Filtra a través de producto__empresa para mantener integridad.
        """
        from apps.tenant.inventario.services import qs_movimiento_list
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            return MovimientoInventario.objects.none()
        search = self.request.query_params.get('search', None)
        return qs_movimiento_list(empresa.id, search=search).order_by('-created_at')
    
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
    
    @action(detail=False, methods=["get", "post"], url_path="dt")
    def datatables(self, request):
        """
        ⚠️ DEPRECATED v2.40: Endpoint legacy para DataTables Server-Side.
        Ya no se usa - Tabulator Factory consume GET /api/v1/inventario/movimientos/ directamente.
        Se mantiene por compatibilidad temporal, pero será eliminado en v2.50.
        
        ⚠️ v2.40: DataTables SERVER-SIDE para Kardex (Movimientos de Inventario).
        Retorna datos paginados en formato estándar DataTables server-side.
        Usa DataTableServer helper para procesamiento seguro.
        """
        from apps.shared.datatable import DataTableSpec, DataTableServer
        from apps.tenant.inventario.services import qs_movimiento_list
        from apps.tenant.inventario.api.serializers import MovimientoInventarioListSerializer
        
        # QuerySet base optimizado
        qs_base = qs_movimiento_list()
        
        # ⚠️ PERFORMANCE BIBLE: Usar .only('id') para obtener empresa singleton
        empresa = Empresa.objects.only('id').first()
        if empresa:
            qs_base = qs_base.filter(producto__empresa=empresa)
        
        # ⚠️ CRÍTICO: fields_map debe coincidir EXACTAMENTE con el orden de columnas en inventario.page.js
        # Columnas: 0=created_at, 1=producto_codigo, 2=producto_nombre, 3=tipo_display, 4=cantidad, 5=origen_referencia, 6=observaciones
        spec = DataTableSpec(
            fields_map={
                0: 'created_at',
                1: 'producto__codigo',  # Serializer expone como producto_codigo, pero en DB es producto__codigo
                2: 'producto__nombre',  # Serializer expone como producto_nombre, pero en DB es producto__nombre
                3: 'tipo',  # Serializer expone como tipo_display, pero ordenamos por tipo
                4: 'cantidad',
                5: 'origen_referencia',
                6: 'observaciones'
            },
            search_fields=['producto__codigo', 'producto__nombre', 'origen_referencia', 'observaciones'],
            base_qs=qs_base,
            serializer=MovimientoInventarioListSerializer,
            extra_filter=lambda req, qs: qs  # Sin filtros adicionales
        )
        
        # Procesar request DataTables
        dt_server = DataTableServer(spec)
        return dt_server.handle(request)

    def perform_create(self, serializer):
        """
        ⚠️ v2.40: Crea movimiento y recalcula stock automáticamente usando Service Layer.
        """
        from apps.tenant.empresa.models import Empresa
        from apps.tenant.inventario.services import recalcular_stock_producto
        
        # ⚠️ PERFORMANCE BIBLE: Usar .only('id') para obtener empresa singleton
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise ValueError("No se encontró configuración de Empresa para este tenant.")
        
        # Guardar movimiento
        movimiento = serializer.save(empresa=empresa)
        
        # ⚠️ CRÍTICO: Recalcular stock después de crear movimiento
        recalcular_stock_producto(movimiento.producto.id)
        
        return movimiento


class HistorialServicioViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    ViewSet para Historial de Servicios.
    
    ⚠️ PERFORMANCE BIBLE:
    - PROHIBIDO .all(): get_queryset() filtra por empresa (SSoT)
    - queryset base solo para DRF, se sobrescribe en get_queryset()
    """
    # ⚠️ NOTA: Este queryset es solo para DRF, se sobrescribe en get_queryset()
    queryset = HistorialServicio.objects.none()
    serializer_class = HistorialServicioSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser]
    
    def get_queryset(self):
        """
        ⚠️ PERFORMANCE BIBLE: Siempre filtrar por empresa (SSoT) - PROHIBIDO .all()
        """
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            return HistorialServicio.objects.none()
        return HistorialServicio.objects.select_related('servicio').filter(empresa=empresa).order_by('-created_at')

    def perform_create(self, serializer):
        """
        ⚠️ PERFORMANCE BIBLE: Usar .only('id') para obtener empresa singleton
        """
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise ValueError("No se encontró configuración de Empresa para este tenant.")
        serializer.save(empresa=empresa)