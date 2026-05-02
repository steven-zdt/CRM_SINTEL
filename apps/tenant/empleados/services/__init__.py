"""
Service Layer para empleados - Re-exporta símbolos de services.py para importación limpia.

WARNING: v2.40: Arquitectura simplificada con importaciones estándar de Django.
Re-exporta todas las funciones del service layer para uso en ViewSets y Serializers.

WARNING: CRÍTICO: Este archivo está en apps/tenant/empleados/services/__init__.py
El archivo services.py está en apps/tenant/empleados/services.py (nivel superior).

PROBLEMA DE CIRCULARIDAD:
- Existe un paquete services/ (con este __init__.py)
- Existe un archivo services.py (nivel superior)
- Python confunde ambos al hacer `from apps.tenant.empleados.services import ...`

SOLUCIÓN v2.95:
- Importar directamente desde el módulo padre usando importlib con sys.modules
- Esto evita que Python intente cargar el paquete services/ primero
- Las funciones se re-exportan explícitamente para uso en ViewSets
"""
import importlib
import sys

# WARNING: v2.95: Importar directamente desde el módulo services.py del paquete padre
# Usar importlib para cargar el módulo desde el paquete empleados
try:
    # Importar el módulo services.py desde el paquete empleados
    # Esto evita el conflicto con el paquete services/
    parent_module = sys.modules.get('apps.tenant.empleados')
    if parent_module is None:
        # Si el módulo padre no está cargado, cargarlo primero
        import apps.tenant.empleados
        parent_module = sys.modules['apps.tenant.empleados']
    
    # Cargar el módulo services.py desde el paquete
    services_module = importlib.import_module('apps.tenant.empleados.services', package='apps.tenant.empleados')
    
    # Si eso no funciona, intentar cargar directamente desde el archivo
    if not hasattr(services_module, 'gestionar_contrato_service'):
        # Fallback: usar importlib.util para cargar desde archivo
        import importlib.util
        from pathlib import Path
        services_py_path = Path(__file__).resolve().parent.parent / 'services.py'
        if services_py_path.exists():
            spec = importlib.util.spec_from_file_location('apps.tenant.empleados.services_module', services_py_path)
            services_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(services_module)
    
    # Re-exportar todas las funciones requeridas
    # WARNING: v2.60: LIST_FIELDS y DETAIL_FIELDS son diccionarios que contienen todas las constantes
    EMPLEADO_LIST_FIELDS = services_module.EMPLEADO_LIST_FIELDS
    CONTRATO_LIST_FIELDS = services_module.CONTRATO_LIST_FIELDS
    DEVENGO_LIST_FIELDS = services_module.DEVENGO_LIST_FIELDS
    EMPLEADO_DETAIL_FIELDS = services_module.EMPLEADO_DETAIL_FIELDS
    CONTRATO_DETAIL_FIELDS = services_module.CONTRATO_DETAIL_FIELDS
    DEVENGO_DETAIL_FIELDS = services_module.DEVENGO_DETAIL_FIELDS
    
    # Diccionario de compatibilidad para código legacy
    LIST_FIELDS = {
        'empleado': EMPLEADO_LIST_FIELDS,
        'contrato': CONTRATO_LIST_FIELDS,
        'devengo': DEVENGO_LIST_FIELDS,
    }
    
    DETAIL_FIELDS = {
        'empleado': EMPLEADO_DETAIL_FIELDS,
        'contrato': CONTRATO_DETAIL_FIELDS,
        'devengo': DEVENGO_DETAIL_FIELDS,
    }
    
    qs_empleado_list = services_module.qs_empleado_list
    qs_empleado_detail = services_module.qs_empleado_detail
    qs_contrato_list = services_module.qs_contrato_list
    qs_contrato_detail = services_module.qs_contrato_detail
    qs_devengo_list = services_module.qs_devengo_list
    qs_devengo_detail = services_module.qs_devengo_detail
    qs_historial_list = services_module.qs_historial_list
    get_nomina_summary = services_module.get_nomina_summary
    anular_devengo_service = services_module.anular_devengo_service
    calcular_devengo_proporcional = services_module.calcular_devengo_proporcional
    # WARNING: v2.60: Funciones de cálculo de nómina colombiana
    calcular_nomina_colombia = services_module.calcular_nomina_colombia
    calcular_liquidacion_nomina = services_module.calcular_liquidacion_nomina
    # WARNING: v2.40: Nuevas funciones de gestión de empleados
    eliminar_empleado_retirado = services_module.eliminar_empleado_retirado
    cancelar_contratos_activos_al_retirar = services_module.cancelar_contratos_activos_al_retirar
    # WARNING: v2.95: Funciones de gestión de contratos y nómina
    gestionar_contrato_service = services_module.gestionar_contrato_service
    registrar_devengo_nomina_service = services_module.registrar_devengo_nomina_service
    # WARNING: v2.60: Nómina Multitanda - Validación de límite de días
    validar_limite_dias_mes = services_module.validar_limite_dias_mes
    # Service mixins
    EmpleadoServiceMixin = services_module.EmpleadoServiceMixin
    ContratoServiceMixin = services_module.ContratoServiceMixin
    DevengoServiceMixin = services_module.DevengoServiceMixin
    
except (ImportError, AttributeError) as e:
    # Si falla la importación, intentar importar directamente desde el archivo
    import importlib.util
    from pathlib import Path
    
    services_py_path = Path(__file__).resolve().parent.parent / 'services.py'
    if services_py_path.exists():
        spec = importlib.util.spec_from_file_location('apps.tenant.empleados.services_module', services_py_path)
        services_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(services_module)
        
        # Re-exportar todas las funciones requeridas
        # WARNING: v2.60: LIST_FIELDS y DETAIL_FIELDS son diccionarios que contienen todas las constantes
        EMPLEADO_LIST_FIELDS = services_module.EMPLEADO_LIST_FIELDS
        CONTRATO_LIST_FIELDS = services_module.CONTRATO_LIST_FIELDS
        DEVENGO_LIST_FIELDS = services_module.DEVENGO_LIST_FIELDS
        EMPLEADO_DETAIL_FIELDS = services_module.EMPLEADO_DETAIL_FIELDS
        CONTRATO_DETAIL_FIELDS = services_module.CONTRATO_DETAIL_FIELDS
        DEVENGO_DETAIL_FIELDS = services_module.DEVENGO_DETAIL_FIELDS
        
        # Diccionario de compatibilidad para código legacy
        LIST_FIELDS = {
            'empleado': EMPLEADO_LIST_FIELDS,
            'contrato': CONTRATO_LIST_FIELDS,
            'devengo': DEVENGO_LIST_FIELDS,
        }
        
        DETAIL_FIELDS = {
            'empleado': EMPLEADO_DETAIL_FIELDS,
            'contrato': CONTRATO_DETAIL_FIELDS,
            'devengo': DEVENGO_DETAIL_FIELDS,
        }
        
        qs_empleado_list = services_module.qs_empleado_list
        qs_empleado_detail = services_module.qs_empleado_detail
        qs_contrato_list = services_module.qs_contrato_list
        qs_contrato_detail = services_module.qs_contrato_detail
        qs_devengo_list = services_module.qs_devengo_list
        qs_devengo_detail = services_module.qs_devengo_detail
        qs_historial_list = services_module.qs_historial_list
        get_nomina_summary = services_module.get_nomina_summary
        anular_devengo_service = services_module.anular_devengo_service
        calcular_devengo_proporcional = services_module.calcular_devengo_proporcional
        # WARNING: v2.60: Funciones de cálculo de nómina colombiana
        calcular_nomina_colombia = services_module.calcular_nomina_colombia
        calcular_liquidacion_nomina = services_module.calcular_liquidacion_nomina
        eliminar_empleado_retirado = services_module.eliminar_empleado_retirado
        cancelar_contratos_activos_al_retirar = services_module.cancelar_contratos_activos_al_retirar
        gestionar_contrato_service = services_module.gestionar_contrato_service
        registrar_devengo_nomina_service = services_module.registrar_devengo_nomina_service
        # Service mixins
        EmpleadoServiceMixin = services_module.EmpleadoServiceMixin
        ContratoServiceMixin = services_module.ContratoServiceMixin
        DevengoServiceMixin = services_module.DevengoServiceMixin
    else:
        raise ImportError(f"No se encontró el archivo services.py en {services_py_path.parent} y falló la importación: {e}")

# WARNING: v2.60: Exportar explícitamente todas las funciones y constantes requeridas
__all__ = [
    # Constantes de campos
    'EMPLEADO_LIST_FIELDS',
    'CONTRATO_LIST_FIELDS',
    'DEVENGO_LIST_FIELDS',
    'EMPLEADO_DETAIL_FIELDS',
    'CONTRATO_DETAIL_FIELDS',
    'DEVENGO_DETAIL_FIELDS',
    'LIST_FIELDS',  # Diccionario de compatibilidad
    'DETAIL_FIELDS',  # Diccionario de compatibilidad
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
    # WARNING: v2.60: Funciones de cálculo de nómina colombiana
    'calcular_nomina_colombia',
    'calcular_liquidacion_nomina',
    'eliminar_empleado_retirado',
    'cancelar_contratos_activos_al_retirar',
    'gestionar_contrato_service',
    'registrar_devengo_nomina_service',
    # WARNING: v2.60: Nómina Multitanda - Validación de límite de días
    'validar_limite_dias_mes',
    # Service mixins
    'EmpleadoServiceMixin',
    'ContratoServiceMixin',
    'DevengoServiceMixin',
]