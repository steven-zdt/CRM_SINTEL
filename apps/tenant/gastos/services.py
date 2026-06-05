"""
Fachada estable para el modulo de gastos.
Re-exporta simbolos de business_service.py para compatibilidad de imports existentes.
"""
from apps.tenant.gastos.services.business_service import (
    GastoBusinessService,
    ResolucionBusinessService,
    materializar_gasto_desde_dto
)

__all__ = [
    'GastoBusinessService',
    'ResolucionBusinessService',
    'materializar_gasto_desde_dto'
]
