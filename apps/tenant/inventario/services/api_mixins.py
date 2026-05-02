"""
API Mixins para Inventario - Inyección de servicios en ViewSets.

WARNING: SINTEL v3.5: Arquitectura Service Layer Modular.
- Este archivo contiene mixins específicos para cada modelo.
- Inyectan acceso estandarizado a Selectors, CRUDService y BusinessService.
- Usan get_empresa_id() de SintelDSVMixin para Zero Trust.
"""
from apps.tenant.inventario.services.selectors import (
    CategoriaSelector,
    ProductoSelector,
    ServicioSelector,
    ActivoSelector,
    MovimientoSelector,
)
from apps.tenant.inventario.services.business_service import (
    InventarioBusinessService,
)
from apps.tenant.inventario.services.crud_service import (
    InventarioCRUDService,
)


class CategoriaServiceMixin:
    """Service mixin para CategoriaItem ViewSet."""

    selector_class = CategoriaSelector
    business_service_class = InventarioBusinessService
    crud_service_class = InventarioCRUDService

    def get_qs_list(self):
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        aplicacion = self.request.query_params.get('aplicacion') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, search=search, aplicacion=aplicacion)

    def get_qs_detail(self):
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_detail(empresa_id, self.kwargs.get('pk'))


class ProductoServiceMixin:
    """Service mixin para Producto ViewSet."""

    selector_class = ProductoSelector
    business_service_class = InventarioBusinessService
    crud_service_class = InventarioCRUDService

    def get_qs_list(self):
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        categoria = self.request.query_params.get('categoria') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, search=search, categoria_id=categoria)

    def get_qs_detail(self):
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_detail(empresa_id, self.kwargs.get('pk'))

    def service_recalcular_stock(self, producto_id):
        return self.business_service_class.recalcular_stock_producto(producto_id)


class ServicioServiceMixin:
    """Service mixin para Servicio ViewSet."""

    selector_class = ServicioSelector
    crud_service_class = InventarioCRUDService

    def get_qs_list(self):
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, search=search)

    def get_qs_detail(self):
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_detail(empresa_id, self.kwargs.get('pk'))


class ActivoServiceMixin:
    """Service mixin para ActivoFijo ViewSet."""

    selector_class = ActivoSelector
    crud_service_class = InventarioCRUDService

    def get_qs_list(self):
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        estado = self.request.query_params.get('estado') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, search=search, estado=estado)

    def get_qs_detail(self):
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_detail(empresa_id, self.kwargs.get('pk'))


class MovimientoServiceMixin:
    """Service mixin para MovimientoInventario ViewSet."""

    selector_class = MovimientoSelector
    business_service_class = InventarioBusinessService
    crud_service_class = InventarioCRUDService

    def get_qs_list(self):
        empresa_id = self.get_empresa_id()
        producto = self.request.query_params.get('producto') if hasattr(self, 'request') else None
        tipo = self.request.query_params.get('tipo') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, producto_id=producto, tipo=tipo)

    def get_qs_detail(self):
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_detail(empresa_id, self.kwargs.get('pk'))

    def service_registrar_movimiento(self, serializer):
        empresa_id = self.get_empresa_id()
        return self.business_service_class.registrar_movimiento(
            empresa_id=empresa_id,
            data=serializer.validated_data
        )
