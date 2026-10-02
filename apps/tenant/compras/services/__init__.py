"""
Services de compras - SSoT para logica de negocio.

Este archivo actua como el punto de entrada unificado para todos los servicios
del modulo de compras, siguiendo el patron de arquitectura modular.
"""

from .api_mixins import (
    OrdenCompraServiceMixin,
    PlantillaOrdenCompraServiceMixin,
    RecepcionCompraServiceMixin,
)
from .business_service import OrdenCompraBusinessService, RecepcionCompraBusinessService
from .crud_service import (
    OrdenCompraCRUDService,
    PlantillaOrdenCompraCRUDService,
    RecepcionCompraCRUDService,
)
from .project_assignment_service import ProjectOrderAssignmentService
from .selectors import (
    ORDEN_COMPRA_DETAIL_FIELDS,
    ORDEN_COMPRA_LIST_FIELDS,
    OrdenCompraSelector,
    PlantillaOrdenCompraSelector,
    RecepcionCompraSelector,
)

__all__ = [
    "OrdenCompraSelector",
    "PlantillaOrdenCompraSelector",
    "RecepcionCompraSelector",
    "ORDEN_COMPRA_LIST_FIELDS",
    "ORDEN_COMPRA_DETAIL_FIELDS",
    "OrdenCompraCRUDService",
    "PlantillaOrdenCompraCRUDService",
    "RecepcionCompraCRUDService",
    "OrdenCompraBusinessService",
    "RecepcionCompraBusinessService",
    "ProjectOrderAssignmentService",
    "OrdenCompraServiceMixin",
    "PlantillaOrdenCompraServiceMixin",
    "RecepcionCompraServiceMixin",
]
