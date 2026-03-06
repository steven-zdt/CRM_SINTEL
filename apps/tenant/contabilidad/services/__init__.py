"""
Servicios internos del dominio Contabilidad.

⚠️ v2.30: Service Layer Pattern - Lógica de negocio del dominio Contabilidad.
- Sin signals: Toda la lógica es explícita
- Sin HTTP: Funciones puras que operan sobre modelos
- Multi-tenant: Transparente (django-tenants maneja el aislamiento por esquema)

⚠️ v2.37: Re-exporta LIST_FIELDS y qs_* desde services.py (nivel superior)
"""
from .cuentas_service import (
    list_cuentas,
    create_cuenta,
    update_cuenta,
    delete_cuenta,
)
from .asientos_service import (
    list_asientos,
    create_asiento,
    update_asiento,
    delete_asiento,
    aprobar_asiento,
)
from .movimientos_service import (
    list_movimientos,
    create_movimiento,
    update_movimiento,
    delete_movimiento,
)

# ⚠️ v2.37: Re-exportar LIST_FIELDS y qs_* desde services.py usando importlib para evitar circularidad
import importlib.util
from pathlib import Path
import sys

services_py_path = Path(__file__).resolve().parent.parent / 'services.py'
if services_py_path.exists():
    module_name = 'apps.tenant.contabilidad.services_module_init'
    if module_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(module_name, services_py_path)
        services_module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = services_module
        spec.loader.exec_module(services_module)
    else:
        services_module = sys.modules[module_name]
    
    # Re-exportar símbolos
    CUENTA_LIST_FIELDS = services_module.CUENTA_LIST_FIELDS
    CUENTA_DETAIL_FIELDS = services_module.CUENTA_DETAIL_FIELDS
    ASIENTO_LIST_FIELDS = services_module.ASIENTO_LIST_FIELDS
    ASIENTO_DETAIL_FIELDS = services_module.ASIENTO_DETAIL_FIELDS
    qs_cuenta_list = services_module.qs_cuenta_list
    qs_cuenta_detail = services_module.qs_cuenta_detail
    qs_asiento_list = services_module.qs_asiento_list
    qs_asiento_detail = services_module.qs_asiento_detail
    # ⚠️ v2.60 Fase 3: Exportar funciones de reportes
    get_balance_prueba = services_module.get_balance_prueba
    verificar_periodo_cerrado = services_module.verificar_periodo_cerrado

__all__ = [
    'list_cuentas',
    'create_cuenta',
    'update_cuenta',
    'delete_cuenta',
    'list_asientos',
    'create_asiento',
    'update_asiento',
    'delete_asiento',
    'aprobar_asiento',
    'list_movimientos',
    'create_movimiento',
    'update_movimiento',
    'delete_movimiento',
    # v2.37: LIST_FIELDS y qs_*
    'CUENTA_LIST_FIELDS', 'CUENTA_DETAIL_FIELDS',
    'ASIENTO_LIST_FIELDS', 'ASIENTO_DETAIL_FIELDS',
    'qs_cuenta_list', 'qs_cuenta_detail',
    'qs_asiento_list', 'qs_asiento_detail',
    # ⚠️ v2.60 Fase 3: Funciones de reportes y validación
    'get_balance_prueba',
    'verificar_periodo_cerrado',
]
