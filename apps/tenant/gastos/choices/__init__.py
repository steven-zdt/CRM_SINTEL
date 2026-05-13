"""
Choices para la app de gastos (TENANT_APP).

v2.62: FLEXIBILIDAD OPERATIVA - Inmutabilidad deshabilitada.
"""

from .categoria_contable import (
    CATEGORIA_CONTABLE_CHOICES,
    get_categoria_contable_choices,
)
from .centros_costo import (
    CENTRO_COSTO_CHOICES,
    get_centro_costo_choices,
)

__all__ = [
    'CENTRO_COSTO_CHOICES',
    'get_centro_costo_choices',
    'CATEGORIA_CONTABLE_CHOICES',
    'get_categoria_contable_choices',
]
