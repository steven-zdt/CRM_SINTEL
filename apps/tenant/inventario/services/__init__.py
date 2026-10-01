# apps/tenant/inventario/services/__init__.py
# v3.9.0: Re-exports explicitos — reemplaza wildcard imports (DEUDA-02)

from . import business_service as inv_business
from . import selectors as inv_selectors

# [ARQ-C2] Los ServiceMixin viven en api_mixins.py, no en business_service.py.
from .api_mixins import (
    ActivoFijoServiceMixin,
    CategoriaItemServiceMixin,
    HistorialServiceMixin,
    MovimientoServiceMixin,
    ProductoServiceMixin,
    ServicioServiceMixin,
    TrasladoInventarioServiceMixin,
)
from .business_service import (
    KardexService,
    TrasladoInventarioService,
)
from .ingesta_service import (
    IngestaService,
    materializar_carga_masiva_productos,
    materializar_inventario_desde_dto,
)
from .selectors import (
    ACTIVO_DETAIL_FIELDS,
    ACTIVO_LIST_FIELDS,
    CATEGORIA_DETAIL_FIELDS,
    CATEGORIA_LIST_FIELDS,
    MOVIMIENTO_DETAIL_FIELDS,
    MOVIMIENTO_LIST_FIELDS,
    PRODUCTO_DETAIL_FIELDS,
    PRODUCTO_LIST_FIELDS,
    SERVICIO_DETAIL_FIELDS,
    SERVICIO_LIST_FIELDS,
    ActivoFijoSelector,
    CategoriaItemSelector,
    HistorialServicioSelector,
    MovimientoInventarioSelector,
    ProductoSelector,
    ServicioSelector,
    StockPorSedeSelector,
    TrasladoInventarioSelector,
    get_empresa_singleton,
    get_movimientos_timeline,
)

# Re-exports publicos del Service Layer (SSoT) -- declarados explicitamente
# para que ruff (F401) no los marque como "importados pero no usados": el
# proposito de este __init__.py es precisamente exponerlos a otros modulos
# via `from apps.tenant.inventario.services import X`.
__all__ = [
    "inv_business",
    "inv_selectors",
    "ActivoFijoServiceMixin",
    "CategoriaItemServiceMixin",
    "HistorialServiceMixin",
    "MovimientoServiceMixin",
    "ProductoServiceMixin",
    "ServicioServiceMixin",
    "TrasladoInventarioServiceMixin",
    "KardexService",
    "TrasladoInventarioService",
    "IngestaService",
    "materializar_carga_masiva_productos",
    "materializar_inventario_desde_dto",
    "ACTIVO_DETAIL_FIELDS",
    "ACTIVO_LIST_FIELDS",
    "CATEGORIA_DETAIL_FIELDS",
    "CATEGORIA_LIST_FIELDS",
    "MOVIMIENTO_DETAIL_FIELDS",
    "MOVIMIENTO_LIST_FIELDS",
    "PRODUCTO_DETAIL_FIELDS",
    "PRODUCTO_LIST_FIELDS",
    "SERVICIO_DETAIL_FIELDS",
    "SERVICIO_LIST_FIELDS",
    "ActivoFijoSelector",
    "CategoriaItemSelector",
    "HistorialServicioSelector",
    "MovimientoInventarioSelector",
    "ProductoSelector",
    "ServicioSelector",
    "StockPorSedeSelector",
    "TrasladoInventarioSelector",
    "get_empresa_singleton",
    "get_movimientos_timeline",
]
