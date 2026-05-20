# apps/tenant/inventario/services/__init__.py
# v3.9.0: Re-exports explicitos — reemplaza wildcard imports (DEUDA-02)

from .selectors import (
    get_empresa_singleton,
    get_movimientos_timeline,
    CategoriaItemSelector,
    ProductoSelector,
    ServicioSelector,
    ActivoFijoSelector,
    MovimientoInventarioSelector,
    HistorialServicioSelector,
    CATEGORIA_LIST_FIELDS,
    CATEGORIA_DETAIL_FIELDS,
    PRODUCTO_LIST_FIELDS,
    PRODUCTO_DETAIL_FIELDS,
    SERVICIO_LIST_FIELDS,
    SERVICIO_DETAIL_FIELDS,
    ACTIVO_LIST_FIELDS,
    ACTIVO_DETAIL_FIELDS,
    MOVIMIENTO_LIST_FIELDS,
    MOVIMIENTO_DETAIL_FIELDS,
)

from .business_service import (
    KardexService,
    IngestaService,
    CategoriaItemServiceMixin,
    ProductoServiceMixin,
    ServicioServiceMixin,
    ActivoFijoServiceMixin,
    MovimientoServiceMixin,
    HistorialServiceMixin,
)

from .crud_service import (
    crear_producto,
    actualizar_producto,
    crear_servicio,
    actualizar_servicio,
    crear_activo,
    actualizar_activo,
    crear_movimiento_raw,
)

from . import selectors as inv_selectors
from . import business_service as inv_business
from . import crud_service as inv_crud
