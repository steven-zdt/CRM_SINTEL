"""
Services de gastos - Re-exporta símbolos de services.py para importación limpia.

⚠️ v2.40: Arquitectura simplificada con importaciones estándar de Django.
Re-exporta todas las funciones del service layer para uso en ViewSets y Serializers.

⚠️ CRÍTICO: Este archivo está en apps/tenant/gastos/services/__init__.py
El archivo services.py está en apps/tenant/gastos/services.py (nivel superior).

PROBLEMA DE CIRCULARIDAD:
- Existe un paquete services/ (con este __init__.py)
- Existe un archivo services.py (nivel superior)
- Python confunde ambos al hacer `from apps.tenant.gastos.services import ...`

SOLUCIÓN:
- Usar importlib para cargar directamente el archivo services.py
- Esto evita que Python intente cargar el paquete services/ primero
- Las funciones se re-exportan explícitamente para uso en ViewSets
"""
# ⚠️ v2.40: Importación directa desde el archivo services.py para evitar circularidad
# El conflicto es: paquete services/ (con __init__.py) vs archivo services.py
# Solución: importar directamente desde el archivo usando importlib
import importlib.util
from pathlib import Path

# Ruta al archivo services.py (nivel superior del paquete gastos)
services_py_path = Path(__file__).resolve().parent.parent / 'services.py'

if services_py_path.exists():
    # Cargar el módulo directamente desde el archivo
    spec = importlib.util.spec_from_file_location('apps.tenant.gastos.services_module', services_py_path)
    services_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(services_module)
    
    # Re-exportar todas las funciones requeridas
    LIST_FIELDS = services_module.LIST_FIELDS
    DETAIL_FIELDS = services_module.DETAIL_FIELDS
    qs_list = services_module.qs_list
    qs_detail = services_module.qs_detail
    get_gastos_summary = services_module.get_gastos_summary
    obtener_resolucion_vigente = services_module.obtener_resolucion_vigente
    obtener_siguiente_numero_soporte = services_module.obtener_siguiente_numero_soporte
    normalize_document_number = services_module.normalize_document_number
    anular_gasto_service = services_module.anular_gasto_service
    desactivar_gasto_service = getattr(services_module, 'desactivar_gasto_service', None)  # ⚠️ v2.40: Función para desactivar
    materializar_gasto_desde_dto = getattr(services_module, 'materializar_gasto_desde_dto', None)
    materializar_inventario_desde_dto = getattr(services_module, 'materializar_inventario_desde_dto', None)
    # ⚠️ v2.40: Funciones de Resoluciones DIAN
    qs_resolucion_list = getattr(services_module, 'qs_resolucion_list', None)
    qs_resolucion_detail = getattr(services_module, 'qs_resolucion_detail', None)
    crear_resolucion = getattr(services_module, 'crear_resolucion', None)
    desactivar_resolucion = getattr(services_module, 'desactivar_resolucion', None)
    puede_eliminar_resolucion = getattr(services_module, 'puede_eliminar_resolucion', None)
    # ⚠️ v2.40: Función de cálculo de retenciones
    calcular_retenciones = getattr(services_module, 'calcular_retenciones', None)
else:
    raise ImportError(f"No se encontró el archivo services.py en {services_py_path.parent}")

# Re-exportar desde gasto_service.py si existe (compatibilidad)
try:
    from .gasto_service import *  # Mantener imports existentes si hay funciones adicionales
except ImportError:
    pass  # No crítico si no existe

# ⚠️ v2.40: Exportar explícitamente todas las funciones requeridas
__all__ = [
    'LIST_FIELDS',
    'DETAIL_FIELDS',
    'qs_list',
    'qs_detail',
    'get_gastos_summary',
    'obtener_resolucion_vigente',
    'obtener_siguiente_numero_soporte',
    'normalize_document_number',
    'anular_gasto_service',
]
if desactivar_gasto_service:
    __all__.append('desactivar_gasto_service')
if materializar_gasto_desde_dto:
    __all__.append('materializar_gasto_desde_dto')
if materializar_inventario_desde_dto:
    __all__.append('materializar_inventario_desde_dto')
# ⚠️ v2.40: Funciones de Resoluciones DIAN
if qs_resolucion_list:
    __all__.append('qs_resolucion_list')
if qs_resolucion_detail:
    __all__.append('qs_resolucion_detail')
if crear_resolucion:
    __all__.append('crear_resolucion')
if desactivar_resolucion:
    __all__.append('desactivar_resolucion')
if puede_eliminar_resolucion:
    __all__.append('puede_eliminar_resolucion')
if calcular_retenciones:
    __all__.append('calcular_retenciones')