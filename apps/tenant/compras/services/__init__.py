"""
Services de compras - SSoT para logica de negocio.

Este archivo actua como el punto de entrada unificado para todos los servicios
del modulo de compras, siguiendo el patron de arquitectura modular.
"""

from .selectors import (
    OrdenCompraSelector,
    PlantillaOrdenCompraSelector,
    ORDEN_COMPRA_LIST_FIELDS,
    ORDEN_COMPRA_DETAIL_FIELDS
)
from .crud_service import (
    OrdenCompraCRUDService,
    PlantillaOrdenCompraCRUDService
)
from .business_service import (
    OrdenCompraBusinessService
)
from .api_mixins import (
    OrdenCompraServiceMixin,
    PlantillaOrdenCompraServiceMixin
)

__all__ = [
    'OrdenCompraSelector',
    'PlantillaOrdenCompraSelector',
    'ORDEN_COMPRA_LIST_FIELDS',
    'ORDEN_COMPRA_DETAIL_FIELDS',
    'OrdenCompraCRUDService',
    'PlantillaOrdenCompraCRUDService',
    'OrdenCompraBusinessService',
    'OrdenCompraServiceMixin',
    'PlantillaOrdenCompraServiceMixin'
]
