"""
Service Layer para empleados - Punto de entrada del paquete services/.

WARNING: v2.62.4: Arquitectura simplificada y resolucion de conflicto de modulos.
- Se eliminó el conflicto entre services/ y services.py
- services.py fue renombrado a services_legacy.py
- Se importa directamente de los modulos internos (business_service, crud_service, selectors)
"""

# 1. Importaciones modernas de la estructura Feature-Sliced Design (FSD)
from apps.tenant.empleados.services.selectors import *
from apps.tenant.empleados.services.crud_service import *
from apps.tenant.empleados.services.business_service import *
from apps.tenant.empleados.services.api_mixins import (
    EmpleadoServiceMixin,
    ContratoServiceMixin,
    DevengoServiceMixin,
)

# 2. Re-exportar funciones y constantes desde services_legacy.py
# Estas seran migradas gradualmente a business_service y selectores, 
# pero se mantienen para retrocompatibilidad
from apps.tenant.empleados.services_legacy import (
    qs_empleado_list,
    qs_empleado_detail,
    qs_contrato_list,
    qs_contrato_detail,
    qs_devengo_list,
    qs_devengo_detail,
    qs_historial_list,
    get_nomina_summary,
    anular_devengo_service,
    calcular_devengo_proporcional,
    calcular_nomina_colombia,
    calcular_liquidacion_nomina,
    eliminar_empleado_retirado,
    cancelar_contratos_activos_al_retirar,
    gestionar_contrato_service,
    registrar_devengo_nomina_service,
    validar_limite_dias_mes,
)

__all__ = [
    # Constantes de campos
    'EMPLEADO_LIST_FIELDS',
    'CONTRATO_LIST_FIELDS',
    'DEVENGO_LIST_FIELDS',
    'EMPLEADO_DETAIL_FIELDS',
    'CONTRATO_DETAIL_FIELDS',
    'DEVENGO_DETAIL_FIELDS',
    'LIST_FIELDS',
    'DETAIL_FIELDS',
    # QuerySets optimizados
    'qs_empleado_list',
    'qs_empleado_detail',
    'qs_contrato_list',
    'qs_contrato_detail',
    'qs_devengo_list',
    'qs_devengo_detail',
    'qs_historial_list',
    # Funciones de negocio
    'get_nomina_summary',
    'anular_devengo_service',
    'calcular_devengo_proporcional',
    'calcular_nomina_colombia',
    'calcular_liquidacion_nomina',
    'eliminar_empleado_retirado',
    'cancelar_contratos_activos_al_retirar',
    'gestionar_contrato_service',
    'registrar_devengo_nomina_service',
    'validar_limite_dias_mes',
    # Service mixins
    'EmpleadoServiceMixin',
    'ContratoServiceMixin',
    'DevengoServiceMixin',
]