"""
Services para Gastos - SSoT para la lógica de negocio y persistencia.

WARNING: v2.62.0: Arquitectura Service Layer Modular.
- Re-exporta símbolos desde selectors, business_service y crud_service.
- Mantiene compatibilidad con nombres legacy para minimizar cambios en ViewSets.
"""

from .selectors import (
    GastoSelector,
    ResolucionSelector,
    DocumentoSelector,
    GASTO_LIST_FIELDS,
    GASTO_DETAIL_FIELDS,
    RESOLUCION_LIST_FIELDS,
    RESOLUCION_DETAIL_FIELDS,
)
from .business_service import (
    GastoBusinessService,
    ResolucionBusinessService,
)
from .crud_service import (
    GastoCRUDService,
    ResolucionCRUDService,
    DocumentoCRUDService,
)
from .api_mixins import (
    GastoServiceMixin,
    ResolucionServiceMixin,
)

# --- Aliases para compatibilidad Legacy (Usados en ViewSets) ---

# Selectores
qs_list = GastoSelector.get_list
qs_detail = GastoSelector.get_detail
qs_resolucion_list = ResolucionSelector.get_list
qs_resolucion_detail = ResolucionSelector.get_detail

# Business/CRUD logic
get_gastos_summary = GastoSelector.get_summary
obtener_resolucion_vigente = ResolucionBusinessService.obtener_vigente
anular_gasto_service = GastoCRUDService.anular_gasto
desactivar_gasto_service = GastoCRUDService.desactivar_gasto
crear_resolucion = ResolucionCRUDService.crear_resolucion
desactivar_resolucion = ResolucionCRUDService.desactivar_resolucion
puede_eliminar_resolucion = ResolucionCRUDService.puede_eliminar
calcular_retenciones = GastoBusinessService.calcular_retenciones

# --- Constantes SSoT ---
LIST_FIELDS = GASTO_LIST_FIELDS
DETAIL_FIELDS = GASTO_DETAIL_FIELDS

__all__ = [
    'GastoSelector',
    'ResolucionSelector',
    'DocumentoSelector',
    'GastoBusinessService',
    'ResolucionBusinessService',
    'GastoCRUDService',
    'ResolucionCRUDService',
    'DocumentoCRUDService',
    'GastoServiceMixin',
    'ResolucionServiceMixin',
    # Legacy aliases
    'qs_list',
    'qs_detail',
    'qs_resolucion_list',
    'qs_resolucion_detail',
    'get_gastos_summary',
    'obtener_resolucion_vigente',
    'anular_gasto_service',
    'desactivar_gasto_service',
    'crear_resolucion',
    'desactivar_resolucion',
    'puede_eliminar_resolucion',
    'calcular_retenciones',
    'LIST_FIELDS',
    'DETAIL_FIELDS',
]