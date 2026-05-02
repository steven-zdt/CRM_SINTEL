"""
Fachada estable para Servicios de Empleados v2.61.4.

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
import warnings

from apps.tenant.empleados.services.selectors import (
    # Selectors
    EmpleadoSelector,
    ContratoSelector,
    DevengoSelector,
    NominaSummarySelector,
    # Constantes
    EMPLEADO_LIST_FIELDS,
    EMPLEADO_DETAIL_FIELDS,
    CONTRATO_LIST_FIELDS,
    CONTRATO_DETAIL_FIELDS,
    DEVENGO_LIST_FIELDS,
    DEVENGO_DETAIL_FIELDS,
    LIST_FIELDS,
    DETAIL_FIELDS,
)
from apps.tenant.empleados.services.business_service import (
    EmpleadoBusinessService,
    ContratoBusinessService,
    DevengoBusinessService,
    NominaCalculationService,
)
from apps.tenant.empleados.services.api_mixins import (
    EmpleadoServiceMixin,
    ContratoServiceMixin,
    DevengoServiceMixin,
)

logger = logging.getLogger(__name__)

# ==============================================================================
# COMPATIBILIDAD LEGACY
# Funciones que mantienen la interfaz anterior pero delegan al nuevo Service Layer
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
    # Fallback
    from apps.tenant.empresa.models import Empresa
    empresa = Empresa.objects.only('id').first()
    return empresa.id if empresa else None


# -----------------------------------------------------------------------------
# QuerySets Optimizados (delegan a Selectors)
# -----------------------------------------------------------------------------
def qs_empleado_list(empresa_id, search=None):
    """DEPRECATED: Usar EmpleadoSelector.get_list()"""
    return EmpleadoSelector.get_list(empresa_id, search=search)

def qs_empleado_detail(empresa_id, empleado_id):
    """DEPRECATED: Usar EmpleadoSelector.get_detail()"""
    return EmpleadoSelector.get_detail(empresa_id, empleado_id)

def qs_contrato_list(empresa_id, search=None, empleado_id=None):
    """DEPRECATED: Usar ContratoSelector.get_list()"""
    if empleado_id:
        try:
            empleado_id = int(empleado_id)
        except (TypeError, ValueError):
            empleado_id = None
    return ContratoSelector.get_list(empresa_id, search=search, empleado_id=empleado_id)

def qs_contrato_detail(empresa_id, contrato_id):
    """DEPRECATED: Usar ContratoSelector.get_detail()"""
    return ContratoSelector.get_detail(empresa_id, contrato_id)

def qs_devengo_list(empresa_id, search=None, empleado_id=None, periodo_mes=None):
    """DEPRECATED: Usar DevengoSelector.get_list()"""
    if empleado_id:
        try:
            empleado_id = int(empleado_id)
        except (TypeError, ValueError):
            empleado_id = None
    return DevengoSelector.get_list(
        empresa_id,
        search=search,
        empleado_id=empleado_id,
        periodo_mes=periodo_mes
    )

def qs_devengo_detail(empresa_id, devengo_id):
    """DEPRECATED: Usar DevengoSelector.get_detail()"""
    return DevengoSelector.get_detail(empresa_id, devengo_id)

def qs_historial_list(empleado_id, empresa_id, search=None):
    """DEPRECATED: Usar DevengoSelector.get_historial()"""
    return DevengoSelector.get_historial(empleado_id, empresa_id, search=search)


# -----------------------------------------------------------------------------
# Funciones de Negocio (delegan a Business Services)
# -----------------------------------------------------------------------------
def get_nomina_summary(empresa_id):
    """DEPRECATED: Usar NominaSummarySelector.get_summary()"""
    return NominaSummarySelector.get_summary(empresa_id)

def anular_devengo_service(devengo_id, empresa_id):
    """DEPRECATED: Usar DevengoBusinessService.anular_devengo()"""
    from apps.tenant.empleados.models import Devengo
    devengo = Devengo.objects.get(id=devengo_id, empresa_id=empresa_id)
    return DevengoBusinessService.anular_devengo(devengo, empresa_id)

def calcular_devengo_proporcional(contrato, dias_laborados, otros_devengos=0, prestamos=0, descuentos_operativos=0):
    """DEPRECATED: Usar NominaCalculationService.calcular_liquidacion()"""
    return NominaCalculationService.calcular_liquidacion(
        contrato=contrato,
        dias_laborados=dias_laborados,
        otros_devengos=otros_devengos,
        prestamos=prestamos,
        descuentos_operativos=descuentos_operativos
    )

def calcular_nomina_colombia(contrato, dias_laborados, horas_trabajadas=None, otros_devengos=0,
                              prestamos=0, descuentos_operativos=0, empresa_id=None):
    """DEPRECATED: Usar NominaCalculationService.calcular_liquidacion()"""
    return NominaCalculationService.calcular_liquidacion(
        contrato=contrato,
        dias_laborados=dias_laborados,
        horas_trabajadas=horas_trabajadas,
        otros_devengos=otros_devengos,
        prestamos=prestamos,
        descuentos_operativos=descuentos_operativos,
        empresa_id=empresa_id
    )

def calcular_liquidacion_nomina(contrato, dias_laborados, horas_trabajadas=None, otros_devengos=0,
                                 prestamos=0, descuentos_operativos=0, empresa_id=None):
    """DEPRECATED: Usar NominaCalculationService.calcular_liquidacion()"""
    return NominaCalculationService.calcular_liquidacion(
        contrato=contrato,
        dias_laborados=dias_laborados,
        horas_trabajadas=horas_trabajadas,
        otros_devengos=otros_devengos,
        prestamos=prestamos,
        descuentos_operativos=descuentos_operativos,
        empresa_id=empresa_id
    )

def eliminar_empleado_retirado(empleado):
    """DEPRECATED: Usar EmpleadoBusinessService.eliminar_empleado_retirado()"""
    return EmpleadoBusinessService.eliminar_empleado_retirado(empleado)

def cancelar_contratos_activos_al_retirar(empleado):
    """DEPRECATED: Usar EmpleadoBusinessService.cancelar_contratos_activos()"""
    return EmpleadoBusinessService.cancelar_contratos_activos(empleado)

def gestionar_contrato_service(empleado, data, contrato_existente=None):
    """DEPRECATED: Usar ContratoBusinessService.gestionar_contrato()"""
    return ContratoBusinessService.gestionar_contrato(empleado, data, contrato_existente)

def preparar_datos_contrato(data):
    """DEPRECATED: Usar ContratoBusinessService.preparar_datos_contrato()"""
    return ContratoBusinessService.preparar_datos_contrato(data)

def registrar_devengo_nomina_service(empleado, data):
    """DEPRECATED: Usar DevengoBusinessService.procesar_devengo()"""
    from apps.tenant.empleados.models import Contrato
    # Obtener contrato del empleado
    contrato = Contrato.objects.filter(
        empleado=empleado,
        activo=True,
        estado='ACTIVO'
    ).first()
    if not contrato:
        raise ValueError("No se encontró contrato activo para el empleado")
    return DevengoBusinessService.procesar_devengo(
        empleado=empleado,
        contrato=contrato,
        data=data,
        empresa_id=empleado.empresa_id
    )

def validar_limite_dias_mes(empleado_id, periodo_mes, nuevos_dias, empresa_id, devengo_id_excluir=None):
    """DEPRECATED: Usar DevengoBusinessService.validar_limite_dias_mes()"""
    from decimal import Decimal
    return DevengoBusinessService.validar_limite_dias_mes(
        empleado_id=empleado_id,
        periodo_mes=periodo_mes,
        nuevos_dias=Decimal(str(nuevos_dias)),
        empresa_id=empresa_id,
        devengo_id_excluir=devengo_id_excluir
    )


# -----------------------------------------------------------------------------
# Service Mixins (delegan a API Mixins)
# -----------------------------------------------------------------------------
# Las clases de mixin son importadas directamente desde api_mixins arriba
# para mantener compatibilidad exacta con el código existente


# ==============================================================================
# EXPORTS
# ==============================================================================
__all__ = [
    # Selectors (nuevo)
    'EmpleadoSelector',
    'ContratoSelector',
    'DevengoSelector',
    'NominaSummarySelector',
    # Business Services (nuevo)
    'EmpleadoBusinessService',
    'ContratoBusinessService',
    'DevengoBusinessService',
    'NominaCalculationService',
    # Legacy QuerySets (mantener compatibilidad)
    'qs_empleado_list',
    'qs_empleado_detail',
    'qs_contrato_list',
    'qs_contrato_detail',
    'qs_devengo_list',
    'qs_devengo_detail',
    'qs_historial_list',
    # Legacy funciones de negocio
    'get_nomina_summary',
    'anular_devengo_service',
    'calcular_devengo_proporcional',
    'calcular_nomina_colombia',
    'calcular_liquidacion_nomina',
    'eliminar_empleado_retirado',
    'cancelar_contratos_activos_al_retirar',
    'gestionar_contrato_service',
    'preparar_datos_contrato',
    'registrar_devengo_nomina_service',
    'validar_limite_dias_mes',
    # Legacy Service Mixins (mantener compatibilidad con ViewSets existentes)
    'EmpleadoServiceMixin',
    'ContratoServiceMixin',
    'DevengoServiceMixin',
    # Constantes
    'EMPLEADO_LIST_FIELDS',
    'EMPLEADO_DETAIL_FIELDS',
    'CONTRATO_LIST_FIELDS',
    'CONTRATO_DETAIL_FIELDS',
    'DEVENGO_LIST_FIELDS',
    'DEVENGO_DETAIL_FIELDS',
    'LIST_FIELDS',
    'DETAIL_FIELDS',
]
