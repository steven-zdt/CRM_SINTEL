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
    StockPorSedeSelector,
    TrasladoInventarioSelector,
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
    TrasladoInventarioService,
)

# [ARQ-C2] Los ServiceMixin viven en api_mixins.py, no en business_service.py.
from .api_mixins import (
    CategoriaItemServiceMixin,
    ProductoServiceMixin,
    ServicioServiceMixin,
    ActivoFijoServiceMixin,
    MovimientoServiceMixin,
    HistorialServiceMixin,
    TrasladoInventarioServiceMixin,
)

from .ingesta_service import (
    IngestaService,
    materializar_inventario_desde_dto,
    materializar_carga_masiva_productos,
)

from . import selectors as inv_selectors
from . import business_service as inv_business
