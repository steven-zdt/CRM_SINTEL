"""
Services de gastos - SSoT para logica de negocio v2.62.0.

Este archivo actua como el punto de entrada unificado para todos los servicios
del modulo de gastos, siguiendo el patron de arquitectura modular (selectors, crud, business).
"""

from .selectors import (
    ResolucionSelector,
    DocumentoSelector,
    RESOLUCION_LIST_FIELDS,
    DOCUMENTO_LIST_FIELDS,
    DOCUMENTO_DETAIL_FIELDS,
    RESOLUCION_DETAIL_FIELDS
)
from .crud_service import (
    ResolucionCRUDService,
    DocumentoCRUDService
)
from .business_service import (
    GastoBusinessService,
    ResolucionBusinessService,
    materializar_gasto_desde_dto
)
from .api_mixins import GastoServiceMixin, ResolucionServiceMixin

__all__ = [
    'ResolucionSelector',
    'DocumentoSelector',
    'ResolucionCRUDService',
    'DocumentoCRUDService',
    'GastoBusinessService',
    'ResolucionBusinessService',
    'materializar_gasto_desde_dto',
    'GastoServiceMixin',
    'ResolucionServiceMixin',
    'RESOLUCION_LIST_FIELDS',
    'DOCUMENTO_LIST_FIELDS',
    'DOCUMENTO_DETAIL_FIELDS',
    'RESOLUCION_DETAIL_FIELDS'
]