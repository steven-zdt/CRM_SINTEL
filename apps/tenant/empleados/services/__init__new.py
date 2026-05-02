"""
Service Layer para Empleados - Punto de entrada v2.61.4.

WARNING: SINTEL v2.61.4: Arquitectura Service Layer Modular.
Este archivo exporta las clases principales del paquete services/.
"""

# Selectors - Consultas GET optimizadas (read-only)
from apps.tenant.empleados.services.selectors import (
    ContratoSelector,
    DevengoSelector,
    EmpleadoSelector,
    NominaSummarySelector,
    # Constantes de campos
    EMPLEADO_LIST_FIELDS,
    EMPLEADO_DETAIL_FIELDS,
    CONTRATO_LIST_FIELDS,
    CONTRATO_DETAIL_FIELDS,
    DEVENGO_LIST_FIELDS,
    DEVENGO_DETAIL_FIELDS,
    LIST_FIELDS,
    DETAIL_FIELDS,
)

# CRUD Service - Persistencia transaccional pura
from apps.tenant.empleados.services.crud_service import (
    EmpleadoCRUDService,
    ContratoCRUDService,
    DevengoCRUDService,
)

# Business Service - Lógica de negocio y orquestación
from apps.tenant.empleados.services.business_service import (
    EmpleadoBusinessService,
    ContratoBusinessService,
    DevengoBusinessService,
    NominaCalculationService,
)

# API Mixins - Inyección de servicios en ViewSets
from apps.tenant.empleados.services.api_mixins import (
    EmpleadoServiceMixin,
    ContratoServiceMixin,
    DevengoServiceMixin,
)

# Compatibilidad legacy - funciones de services.py anterior
# Importar desde el archivo services.py del nivel padre para mantener compatibilidad
# durante la transición a la arquitectura modular
try:
    # Importar funciones legacy desde services.py del paquete padre
    import sys
    from pathlib import Path
    
    services_py_path = Path(__file__).resolve().parent.parent / 'services.py'
    if services_py_path.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'empleados.services_legacy', 
            services_py_path
        )
        legacy_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy_module)
        
        # Re-exportar funciones legacy para compatibilidad
        qs_empleado_list = legacy_module.qs_empleado_list
        qs_empleado_detail = legacy_module.qs_empleado_detail
        qs_contrato_list = legacy_module.qs_contrato_list
        qs_contrato_detail = legacy_module.qs_contrato_detail
        qs_devengo_list = legacy_module.qs_devengo_list
        qs_devengo_detail = legacy_module.qs_devengo_detail
        qs_historial_list = legacy_module.qs_historial_list
        get_nomina_summary = legacy_module.get_nomina_summary
        anular_devengo_service = legacy_module.anular_devengo_service
        calcular_devengo_proporcional = legacy_module.calcular_devengo_proporcional
        calcular_nomina_colombia = legacy_module.calcular_nomina_colombia
        calcular_liquidacion_nomina = legacy_module.calcular_liquidacion_nomina
        eliminar_empleado_retirado = legacy_module.eliminar_empleado_retirado
        cancelar_contratos_activos_al_retirar = legacy_module.cancelar_contratos_activos_al_retirar
        gestionar_contrato_service = legacy_module.gestionar_contrato_service
        registrar_devengo_nomina_service = legacy_module.registrar_devengo_nomina_service
        validar_limite_dias_mes = legacy_module.validar_limite_dias_mes
except Exception:
    # Si falla la importación legacy, continuar sin esas funciones
    pass

__all__ = [
    # Selectors
    'EmpleadoSelector',
    'ContratoSelector',
    'DevengoSelector',
    'NominaSummarySelector',
    # Constants
    'EMPLEADO_LIST_FIELDS',
    'EMPLEADO_DETAIL_FIELDS',
    'CONTRATO_LIST_FIELDS',
    'CONTRATO_DETAIL_FIELDS',
    'DEVENGO_LIST_FIELDS',
    'DEVENGO_DETAIL_FIELDS',
    'LIST_FIELDS',
    'DETAIL_FIELDS',
    # CRUD Services
    'EmpleadoCRUDService',
    'ContratoCRUDService',
    'DevengoCRUDService',
    # Business Services
    'EmpleadoBusinessService',
    'ContratoBusinessService',
    'DevengoBusinessService',
    'NominaCalculationService',
    # API Mixins
    'EmpleadoServiceMixin',
    'ContratoServiceMixin',
    'DevengoServiceMixin',
    # Legacy compatibilidad
    'qs_empleado_list',
    'qs_empleado_detail',
    'qs_contrato_list',
    'qs_contrato_detail',
    'qs_devengo_list',
    'qs_devengo_detail',
    'qs_historial_list',
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
]
