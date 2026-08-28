import re

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import SAFE_METHODS
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.request import Request
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.permissions import IsTenantAdmin, IsTenantAdminOrReadOnly, IsTenantMember
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.core.services.organizational_context import OrganizationalContextMixin

# SINTEL v3.5: Refactorizacion Service Layer (Tri-Part)
# PROHIBIDO IMPORTAR MODELOS directamente en ViewSets.
# Toda consulta de base de datos DEBE pasar por el Service Layer.
from apps.tenant.inventario import services as inv_services

# Nuevos Serializers
from .serializers import (
    ActivoFijoDetailSerializer,
    ActivoFijoListSerializer,
    CargaMasivaInventarioSerializer,
    CategoriaItemDetailSerializer,
    CategoriaItemListSerializer,
    HistorialServicioSerializer,
    MovimientoInventarioListSerializer,
    MovimientoInventarioSerializer,
    MovimientoUnificadoListSerializer,
    ProductoDetailSerializer,
    ProductoListSerializer,
    ServicioDetailSerializer,
    ServicioListSerializer,
    StockResponseSerializer,
    TrasladoInventarioCreateSerializer,
    TrasladoInventarioDetailSerializer,
    TrasladoInventarioListSerializer,
)

class BaseViewSet(OrganizationalContextMixin, BaseTenantViewSet):
    """
    v2.60: ViewSet base para inventario usando GenericViewSet con mixins especificos.

    SINTEL v2.60: Sincronizacion Arquitectonica
    - GenericViewSet: Base flexible con mixins especificos (List, Retrieve, Create, Update, Destroy)
    - ENFORCED MODE: Validacion de permisos para mutaciones
    - Asignacion de Empresa (SSoT): Automatica en perform_create()
    - Formato DRF {count, results}: Garantizado en list() para Tabulator Factory

    Fase 9 (OCF): OrganizationalContextMixin adoptado aqui, en la base, para
    que las 6 subclases lo hereden. get_queryset()/get_object()/etc. no
    migrados - resuelven la empresa via inv_services.get_empresa_singleton()
    (Empresa.objects.only('id').first(), sin exigir TenantProfile), mismo
    patron de riesgo ya documentado en empresa (Fase 9 app 1/14).
    """
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]
    pagination_class = StandardResultsSetPagination

    def _check_enforced_mode(self, request):
        """
        v2.60: Verifica si el usuario tiene permisos para mutaciones (ENFORCED MODE).
        """
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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            empresa = inv_services.get_empresa_singleton()
            context['empresa'] = empresa
            context['empresa_id'] = empresa.id
        except ValidationError:
            context['empresa'] = None
            context['empresa_id'] = None
        return context
    
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
        return inv_services.CategoriaItemSelector.get_list(empresa_id=empresa.id, search=search).order_by('nombre')
    
    def get_object(self):
        empresa = inv_services.get_empresa_singleton()
        return inv_services.CategoriaItemSelector.get_detail(
            empresa_id=empresa.id,
            categoria_uuid=self.kwargs[self.lookup_url_kwarg],
        )
    
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
    def resumen(self, request, uuid=None):
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
        return Response(context, template_name='tenant/inventario/offcanvas_categoria.html')


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
            return inv_services.ProductoSelector.get_list(empresa_id=0)
        
        search = self.request.query_params.get('search', None)
        return inv_services.ProductoSelector.get_list(empresa_id=empresa.id, search=search).order_by('nombre')
    
    def get_object(self):
        empresa = inv_services.get_empresa_singleton()
        return inv_services.ProductoSelector.get_detail(
            empresa_id=empresa.id,
            producto_uuid=self.kwargs[self.lookup_url_kwarg],
        )
    
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

    @action(detail=True, methods=["get"], url_path="stock")
    def stock(self, request, uuid=None):
        """
        Retorna solo el stock actual de un producto.
        
        WARNING: PERFORMANCE BIBLE: Solo campos necesarios (id, nombre, stock_actual)
        """
        # WARNING: CRÍTICO: Solo obtener campos necesarios - evitar get_object() que trae todos los campos
        pk = self.kwargs.get(self.lookup_url_kwarg)
        empresa = inv_services.get_empresa_singleton()
        producto = self.service_producto_get_stock(empresa, pk)
        
        serializer = StockResponseSerializer({
            "id": producto.uuid,
            "pk": producto.id,
            "nombre": producto.nombre,
            "stock_actual": producto.stock_actual
        })
        return Response(serializer.data)
    
    @action(detail=True, methods=["get"], url_path="kardex")
    def kardex(self, request, uuid=None):
        """
        WARNING: v2.40: Endpoint para obtener el historial de movimientos (Kardex) de un producto específico.
        Retorna todos los movimientos de inventario asociados al producto ordenados por fecha descendente.
        
        WARNING: PERFORMANCE BIBLE:
        - Usa select_related('producto') para evitar N+1
        - Solo campos necesarios para serializer (MOVIMIENTO_LIST_FIELDS)
        - Producto solo campos necesarios (id, codigo, nombre, stock_actual)
        """
        from apps.tenant.inventario.api.serializers import MovimientoInventarioListSerializer
        pk = self.kwargs.get(self.lookup_url_kwarg)
        empresa = inv_services.get_empresa_singleton()
        producto, movimientos = self.service_producto_get_kardex(empresa, pk)
        
        # Usar serializer optimizado para listas
        serializer = MovimientoInventarioListSerializer(movimientos, many=True)
        
        return Response({
            "producto": {
                "id": producto.id,
                "uuid": str(producto.uuid),
                "codigo": producto.codigo,
                "nombre": producto.nombre,
                "stock_actual": producto.stock_actual
            },
            "movimientos": serializer.data
        })

    @action(detail=False, methods=["post"], url_path="ingesta-masiva")
    def ingesta_masiva(self, request):
        """Materializa productos desde una lista de DTOs validados."""
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

        serializer = CargaMasivaInventarioSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        empresa = self.get_empresa()
        resultado = inv_services.IngestaService.materializar_carga_masiva_productos(
            empresa.id,
            serializer.validated_data['items'],
            usuario=request.user,
        )
        return Response(resultado, status=status.HTTP_200_OK)
    
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
        return Response(context, template_name='tenant/inventario/offcanvas_producto.html')


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
        return inv_services.ServicioSelector.get_list(empresa_id=empresa.id, search=search).order_by('nombre')
    
    def get_object(self):
        empresa = inv_services.get_empresa_singleton()
        return inv_services.ServicioSelector.get_detail(
            empresa_id=empresa.id,
            servicio_uuid=self.kwargs[self.lookup_url_kwarg],
        )
    
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
        return Response(context, template_name='tenant/inventario/offcanvas_servicio.html')
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='historial-offcanvas')
    def historial_offcanvas(self, request):
        """
        v2.60: Devuelve el HTML del formulario de historial de servicio para HTMX Offcanvas via Servicio.
        """
        empresa = self.get_empresa()
        context = self.service_servicio_get_historial_context(empresa)
        return Response(context, template_name='tenant/inventario/offcanvas_historial_servicio.html')


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
        return inv_services.ActivoFijoSelector.get_list(empresa_id=empresa.id, search=search).order_by('nombre')
    
    def get_object(self):
        empresa = inv_services.get_empresa_singleton()
        return inv_services.ActivoFijoSelector.get_detail(
            empresa_id=empresa.id,
            activo_uuid=self.kwargs[self.lookup_url_kwarg],
        )
    
    def destroy(self, request, *args, **kwargs):
        """
        Delega la eliminacion al Service Layer.
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

        instance = self.get_object()
        try:
            self.service_activo_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path="list-all")
    def list_all(self, request):
        """
        v2.40: Endpoint optimizado para Client-Side DataTables via Servicio.
        """
        empresa = inv_services.get_empresa_singleton()
        qs = self.service_activo_list_all(empresa)
        serializer = ActivoFijoListSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        v2.60: Devuelve el HTML del formulario de activo fijo para HTMX Offcanvas via Servicio.
        """
        empresa = inv_services.get_empresa_singleton()
        id_instancia = request.query_params.get('id')
        context = self.service_activo_get_offcanvas_context(empresa, id_instancia)
        return Response(context, template_name='tenant/inventario/offcanvas_activo.html')


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

        # [OSF Fase F7] mismo criterio de degradacion que facturas/
        # cotizaciones/gastos/compras: sin scope resoluble, no restringir.
        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )
        try:
            sede_ids = OrganizationalScope.resolve(self.request).sede_ids
        except OrganizationalScopeError:
            sede_ids = None

        return inv_services.MovimientoInventarioSelector.get_list(
            empresa_id=empresa.id, search=search, sede_ids=sede_ids,
        ).order_by('-created_at')

    def get_object(self):
        empresa = inv_services.get_empresa_singleton()

        # [OSF Fase F13] mismo criterio de degradacion que get_queryset()
        # (F7): antes de esta fase, get_object() (retrieve/update/
        # partial_update/destroy) solo filtraba por empresa_id.
        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )
        try:
            sede_ids = OrganizationalScope.resolve(self.request).sede_ids
        except OrganizationalScopeError:
            sede_ids = None

        try:
            return inv_services.MovimientoInventarioSelector.get_detail(
                empresa_id=empresa.id,
                movimiento_uuid=self.kwargs[self.lookup_url_kwarg],
                sede_ids=sede_ids,
            )
        except ObjectDoesNotExist as exc:
            # [OSF Fase F13] bug preexistente: `.get()` sin envolver dejaba
            # que un DoesNotExist se propagara como 500 en vez de 404 -
            # invisible antes porque ningun test intentaba acceder a un
            # movimiento fuera de scope/empresa. Se descubrio al agregar el
            # filtro de sede_ids arriba (ahora si se ejercita esta rama).
            raise NotFound("Movimiento no encontrado o no pertenece a este tenant.") from exc
    
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
        GET /api/v1/inventario/movimientos/gestor-offcanvas/?id={uuid}
        Devuelve el HTML del formulario de movimiento (crear o editar).
        """
        empresa = inv_services.get_empresa_singleton()
        id_instancia = request.query_params.get('id')
        context = self.service_movimiento_get_offcanvas_context(empresa, id_instancia)
        return Response(context, template_name='tenant/inventario/offcanvas_movimiento.html')
    
    @action(detail=False, methods=['get'], url_path='timeline')
    def timeline(self, request):
        """
        GET /api/v1/inventario/movimientos/timeline/
        Ledger Universal: lista cronologica unificada de PRODUCTOS + ACTIVOS_FIJOS + SERVICIOS.
        Soporta paginacion remota Tabulator (?page, ?page_size) y busqueda (?search=).
        """
        empresa = inv_services.get_empresa_singleton()
        search = request.query_params.get('search') or None
        data = inv_services.get_movimientos_timeline(empresa_id=empresa.id, search=search)

        page = self.paginate_queryset(data)
        if page is not None:
            serializer = MovimientoUnificadoListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MovimientoUnificadoListSerializer(data, many=True)
        return Response({
            'count': len(data),
            'next': None,
            'previous': None,
            'results': serializer.data,
        })

    def perform_create(self, serializer):
        """
        v2.40: Crea movimiento y recalcula stock automaticamente usando Service Layer.
        """
        empresa = inv_services.get_empresa_singleton()
        self.service_movimiento_perform_create(serializer, empresa)

    def partial_update(self, request, *args, **kwargs):
        # BUG DE SEGURIDAD REAL (2026-08-27): este metodo sobreescribe
        # BaseViewSet.update() (que si llama _check_enforced_mode antes de
        # delegar a super().update()) sin volver a aplicar el guard -- un
        # VISOR/OPERADOR podia editar cualquier movimiento de Kardex via
        # PATCH. IsTenantAdminOrReadOnly.has_permission() confia en que el
        # propio ViewSet aplique el enforcement porque detecta el metodo
        # _check_enforced_mode (hasattr), asi que sin este chequeo aqui no
        # habia NINGUNA verificacion de rol en este endpoint.
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        empresa = inv_services.get_empresa_singleton()
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.service_movimiento_perform_update(instance, serializer.validated_data, empresa)
        return Response(self.get_serializer(instance).data)

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Mismo bug de seguridad que partial_update() arriba -- ver comentario.
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        empresa = inv_services.get_empresa_singleton()
        instance = self.get_object()
        self.service_movimiento_perform_destroy(instance, empresa)
        return Response(status=status.HTTP_204_NO_CONTENT)


class HistorialServicioViewSet(BaseViewSet, inv_services.HistorialServiceMixin):
    """
    ViewSet para Historial de Servicios via Service Layer.
    """
    serializer_class = HistorialServicioSerializer
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

    def update(self, request, *args, **kwargs):
        return Response({"detail": "La edicion de historial de servicio no esta habilitada."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "La edicion de historial de servicio no esta habilitada."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=['post'], url_path='vincular-proyecto')
    def vincular_proyecto(self, request, uuid=None):
        """POST /api/v1/inventario/historial-servicios/{uuid}/vincular-proyecto/"""
        import uuid as uuid_mod
        instance = self.get_object()
        proyecto_uuid_str = request.data.get('proyecto_uuid')
        proyecto_nombre = request.data.get('proyecto_nombre', '')

        if not proyecto_uuid_str:
            return Response({'detail': 'proyecto_uuid es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            proyecto_uuid_val = uuid_mod.UUID(str(proyecto_uuid_str))
        except (ValueError, AttributeError):
            return Response({'detail': 'proyecto_uuid invalido.'}, status=status.HTTP_400_BAD_REQUEST)

        # DSV: el proyecto_uuid es una soft-reference (sin FK), pero debe
        # verificarse que pertenece a este tenant antes de guardarlo — mismo
        # patron que ya aplica ProyectoViewSet.vincular_proyecto() del lado de
        # Proyectos (apps/tenant/proyectos/api/viewsets.py). Sin esto se podia
        # grabar un proyecto_uuid/proyecto_nombre arbitrario no verificado.
        from apps.tenant.proyectos.services.selectors import qs_detail as proyecto_qs_detail
        empresa = inv_services.get_empresa_singleton()
        if proyecto_qs_detail(empresa.id, proyecto_uuid_val) is None:
            return Response(
                {'detail': 'El proyecto especificado no existe o no pertenece a esta empresa.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.proyecto_uuid = proyecto_uuid_val
        instance.proyecto_nombre = proyecto_nombre or ''
        instance.save(update_fields=['proyecto_uuid', 'proyecto_nombre'])
        return Response({'status': 'ok', 'proyecto_uuid': str(proyecto_uuid_val)})


class TrasladoInventarioViewSet(BaseViewSet, inv_services.TrasladoInventarioServiceMixin):
    """
    ViewSet para Traslado de Inventario entre Sedes (F21):
    SOLICITADO -> APROBADO -> EN_TRANSITO -> RECIBIDO (o CANCELADO).
    Solo API — sin renderizado de offcanvas HTMX (misma reduccion de alcance
    que RecepcionCompraViewSet, documentada en F21_TRASLADOS_SEDES.md).
    """
    http_method_names = ['get', 'post', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'list':
            return TrasladoInventarioListSerializer
        if self.action == 'create':
            return TrasladoInventarioCreateSerializer
        return TrasladoInventarioDetailSerializer

    def _get_usuario_id(self, request):
        perfil = getattr(request.user, 'tenant_profile', None)
        return perfil.id if perfil else None

    def get_queryset(self):
        empresa = inv_services.get_empresa_singleton()
        if self.action == 'list':
            estado = self.request.query_params.get('estado')
            return self.get_qs_list(empresa, estado=estado)
        uuid_val = self.kwargs.get(self.lookup_url_kwarg)
        return self.get_qs_detail(empresa, uuid_val)

    def create(self, request, *args, **kwargs):
        """POST /api/v1/inventario/traslados/ — crea en SOLICITADO."""
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        usuario_id = self._get_usuario_id(request)
        if not usuario_id:
            return Response(
                {"detail": "El usuario autenticado no tiene un perfil de tenant asociado."},
                status=status.HTTP_403_FORBIDDEN,
            )
        empresa = inv_services.get_empresa_singleton()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            traslado = self.service_traslado_solicitar(empresa, usuario_id, serializer.validated_data)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        out = TrasladoInventarioDetailSerializer(traslado)
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='aprobar')
    def aprobar(self, request, uuid=None):
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        usuario_id = self._get_usuario_id(request)
        if not usuario_id:
            return Response({"detail": "El usuario autenticado no tiene un perfil de tenant asociado."}, status=status.HTTP_403_FORBIDDEN)
        empresa = inv_services.get_empresa_singleton()
        try:
            traslado = self.service_traslado_aprobar(empresa, uuid, usuario_id)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(TrasladoInventarioDetailSerializer(traslado).data)

    @action(detail=True, methods=['post'], url_path='enviar')
    def enviar(self, request, uuid=None):
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        empresa = inv_services.get_empresa_singleton()
        try:
            traslado = self.service_traslado_enviar(empresa, uuid)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(TrasladoInventarioDetailSerializer(traslado).data)

    @action(detail=True, methods=['post'], url_path='recibir')
    def recibir(self, request, uuid=None):
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        usuario_id = self._get_usuario_id(request)
        if not usuario_id:
            return Response({"detail": "El usuario autenticado no tiene un perfil de tenant asociado."}, status=status.HTTP_403_FORBIDDEN)
        empresa = inv_services.get_empresa_singleton()
        try:
            traslado = self.service_traslado_recibir(empresa, uuid, usuario_id)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(TrasladoInventarioDetailSerializer(traslado).data)

    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, uuid=None):
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        empresa = inv_services.get_empresa_singleton()
        try:
            traslado = self.service_traslado_cancelar(empresa, uuid)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(TrasladoInventarioDetailSerializer(traslado).data)
