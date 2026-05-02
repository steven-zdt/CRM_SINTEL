"""
Fachada estable para Servicios de Gastos v2.61.4.

WARNING: SINTEL v2.61.4: Arquitectura Service Layer Modular.
Este archivo es una FACHADA que reexporta desde el nuevo Service Layer modular.

NUEVA ESTRUCTURA (recomendada):
- services/selectors.py          - Consultas GET optimizadas
- services/crud_service.py       - Persistencia transaccional
- services/business_service.py   - Lógica de negocio
- services/api_mixins.py         - Mixins para ViewSets

Este archivo mantiene compatibilidad con código legacy.
"""
import logging
from decimal import Decimal

from apps.tenant.gastos.services.selectors import (
    GastoSelector,
    ResolucionSelector,
    DocumentoSelector,
    GASTO_LIST_FIELDS,
    GASTO_DETAIL_FIELDS,
    RESOLUCION_LIST_FIELDS,
    RESOLUCION_DETAIL_FIELDS,
    LIST_FIELDS,
    DETAIL_FIELDS,
)
from apps.tenant.gastos.services.business_service import (
    GastoBusinessService,
    ResolucionBusinessService,
    calcular_retenciones,
    normalize_document_number,
)
from apps.tenant.gastos.services.api_mixins import (
    GastoServiceMixin,
    ResolucionServiceMixin,
)

logger = logging.getLogger(__name__)

# ==============================================================================
# COMPATIBILIDAD LEGACY - Funciones que mantienen la interfaz anterior
# ==============================================================================

def _get_empresa_id_from_request(request):
    """Helper para extraer empresa_id de request (Zero Trust)."""
    user = getattr(request, 'user', None)
    if user and getattr(user, 'is_authenticated', False):
        empresa_id = getattr(user, 'empresa_id', None)
        if empresa_id:
            return empresa_id
        empresa_obj = getattr(user, 'empresa', None)
        if empresa_obj and getattr(empresa_obj, 'id', None):
            return empresa_obj.id
    from apps.tenant.empresa.models import Empresa
    empresa = Empresa.objects.only('id').first()
    return empresa.id if empresa else None


# -----------------------------------------------------------------------------
# QuerySets Optimizados (delegan a Selectors)
# -----------------------------------------------------------------------------
def qs_list(empresa_id: int, search=None):
    """DEPRECATED: Usar GastoSelector.get_list()"""
    return GastoSelector.get_list(empresa_id, search=search)

def qs_detail(empresa_id: int, gasto_id: int):
    """DEPRECATED: Usar GastoSelector.get_detail()"""
    return GastoSelector.get_detail(empresa_id, gasto_id)

def qs_resolucion_list(empresa_id: int, search=None, solo_vigentes=False):
    """DEPRECATED: Usar ResolucionSelector.get_list()"""
    return ResolucionSelector.get_list(empresa_id, search=search, solo_vigentes=solo_vigentes)

def qs_resolucion_detail(empresa_id: int, resolucion_id: int):
    """DEPRECATED: Usar ResolucionSelector.get_detail()"""
    return ResolucionSelector.get_detail(empresa_id, resolucion_id)


# -----------------------------------------------------------------------------
# Funciones de Negocio (delegan a Business Services)
# -----------------------------------------------------------------------------
def get_gastos_summary(empresa_id: int):
    """DEPRECATED: Usar GastoSelector.get_summary()"""
    return GastoSelector.get_summary(empresa_id)

def obtener_resolucion_vigente(empresa_id: int):
    """DEPRECATED: Usar ResolucionBusinessService.obtener_vigente()"""
    return ResolucionBusinessService.obtener_vigente(empresa_id)

def obtener_siguiente_numero_soporte(empresa):
    """DEPRECATED: Usar DocumentoCRUDService._obtener_siguiente_consecutivo()"""
    from apps.tenant.gastos.services.crud_service import DocumentoCRUDService
    resolucion = ResolucionBusinessService.obtener_vigente(empresa.id)
    if not resolucion:
        raise ValueError("No hay resolución vigente")
    return DocumentoCRUDService._obtener_siguiente_consecutivo(resolucion)

def anular_gasto_service(gasto):
    """DEPRECATED: Usar GastoCRUDService.anular_gasto()"""
    from apps.tenant.gastos.services.crud_service import GastoCRUDService
    return GastoCRUDService.anular_gasto(gasto)

def desactivar_gasto_service(gasto):
    """DEPRECATED: Usar GastoCRUDService.desactivar_gasto()"""
    from apps.tenant.gastos.services.crud_service import GastoCRUDService
    return GastoCRUDService.desactivar_gasto(gasto)

def crear_resolucion(data, empresa):
    """DEPRECATED: Usar ResolucionCRUDService.crear_resolucion()"""
    from apps.tenant.gastos.services.crud_service import ResolucionCRUDService
    return ResolucionCRUDService.crear_resolucion(data, empresa)

def desactivar_resolucion(resolucion):
    """DEPRECATED: Usar ResolucionCRUDService.desactivar_resolucion()"""
    from apps.tenant.gastos.services.crud_service import ResolucionCRUDService
    return ResolucionCRUDService.desactivar_resolucion(resolucion)

def puede_eliminar_resolucion(resolucion):
    """DEPRECATED: Usar ResolucionCRUDService.puede_eliminar()"""
    from apps.tenant.gastos.services.crud_service import ResolucionCRUDService
    return ResolucionCRUDService.puede_eliminar(resolucion)


# ==============================================================================
# EXPORTS
# ==============================================================================
__all__ = [
    # Selectors (nuevo)
    'GastoSelector',
    'ResolucionSelector',
    'DocumentoSelector',
    # Business Services (nuevo)
    'GastoBusinessService',
    'ResolucionBusinessService',
    'calcular_retenciones',
    'normalize_document_number',
    # Legacy QuerySets
    'qs_list',
    'qs_detail',
    'qs_resolucion_list',
    'qs_resolucion_detail',
    # Legacy funciones de negocio
    'get_gastos_summary',
    'obtener_resolucion_vigente',
    'obtener_siguiente_numero_soporte',
    'anular_gasto_service',
    'desactivar_gasto_service',
    'crear_resolucion',
    'desactivar_resolucion',
    'puede_eliminar_resolucion',
    # Legacy Service Mixins
    'GastoServiceMixin',
    'ResolucionServiceMixin',
    # Constantes
    'GASTO_LIST_FIELDS',
    'GASTO_DETAIL_FIELDS',
    'RESOLUCION_LIST_FIELDS',
    'RESOLUCION_DETAIL_FIELDS',
    'LIST_FIELDS',
    'DETAIL_FIELDS',
]
