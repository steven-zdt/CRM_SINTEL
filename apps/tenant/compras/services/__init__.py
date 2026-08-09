"""
Services de compras - SSoT para logica de negocio.

Este archivo actua como el punto de entrada unificado para todos los servicios
del modulo de compras, siguiendo el patron de arquitectura modular.
"""

from .selectors import (
    OrdenCompraSelector,
    PlantillaOrdenCompraSelector,
    RecepcionCompraSelector,
    ORDEN_COMPRA_LIST_FIELDS,
    ORDEN_COMPRA_DETAIL_FIELDS
)
from .crud_service import (
    OrdenCompraCRUDService,
    PlantillaOrdenCompraCRUDService,
    RecepcionCompraCRUDService
)
from .business_service import (
    OrdenCompraBusinessService,
    RecepcionCompraBusinessService
)
from .api_mixins import (
    OrdenCompraServiceMixin,
    PlantillaOrdenCompraServiceMixin,
    RecepcionCompraServiceMixin
)

__all__ = [
    'OrdenCompraSelector',
    'PlantillaOrdenCompraSelector',
    'RecepcionCompraSelector',
    'ORDEN_COMPRA_LIST_FIELDS',
    'ORDEN_COMPRA_DETAIL_FIELDS',
    'OrdenCompraCRUDService',
    'PlantillaOrdenCompraCRUDService',
    'RecepcionCompraCRUDService',
    'OrdenCompraBusinessService',
    'RecepcionCompraBusinessService',
    'OrdenCompraServiceMixin',
    'PlantillaOrdenCompraServiceMixin',
    'RecepcionCompraServiceMixin'
]
