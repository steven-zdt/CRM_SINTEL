"""
Servicios del dominio Contabilidad (v3.5).

[ARCHITECTURE v3.5]
- selectors.py: Consultas y conjuntos de campos (Lectura).
- crud_service.py: Operaciones de persistencia atómica (Escritura).
- business_service.py: Lógica de negocio y orquestación (Dominio).
"""
from .selectors import (
    ASIENTO_DETAIL_FIELDS,
    ASIENTO_LIST_FIELDS,
    CUENTA_DETAIL_FIELDS,
    CUENTA_LIST_FIELDS,
    PERIODO_DETAIL_FIELDS,
    PERIODO_LIST_FIELDS,
    CATALOGO_LIST_FIELDS,
    MOVIMIENTO_LIST_FIELDS,
    MOVIMIENTO_DETAIL_FIELDS,
    AsientoContableSelector,
    CuentaContableSelector,
    PeriodoContableSelector,
    TipoComprobanteSelector,
    ContabilidadSelector,
    get_balance_prueba,
    verificar_periodo_cerrado,
    calcular_saldos_cuenta,
    get_tercero_movimiento,
    PlantillaContableSelector,
)
from .crud_service import ContabilidadCRUDService
from .business_service import ContabilidadBusinessService
from .retenciones_service import RetencionesService

__all__ = [
    # Selectors
    'ASIENTO_LIST_FIELDS', 'ASIENTO_DETAIL_FIELDS',
    'CUENTA_LIST_FIELDS', 'CUENTA_DETAIL_FIELDS',
    'PERIODO_LIST_FIELDS', 'PERIODO_DETAIL_FIELDS',
    'CATALOGO_LIST_FIELDS',
    'MOVIMIENTO_LIST_FIELDS', 'MOVIMIENTO_DETAIL_FIELDS',
    'AsientoContableSelector',
    'CuentaContableSelector',
    'PeriodoContableSelector',
    'TipoComprobanteSelector',
    'ContabilidadSelector',
    'PlantillaContableSelector',
    'get_balance_prueba',
    'verificar_periodo_cerrado',
    'calcular_saldos_cuenta',
    'get_tercero_movimiento',

    # Services
    'ContabilidadCRUDService',
    'ContabilidadBusinessService',
    'RetencionesService',
]
