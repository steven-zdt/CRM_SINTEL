"""
Choices para la app de gastos (TENANT_APP).

v2.62: FLEXIBILIDAD OPERATIVA - Inmutabilidad deshabilitada.
"""

from .categoria_contable import (
    CATEGORIA_CONTABLE_CHOICES,
    get_categoria_contable_choices,
)

__all__ = [
    'CATEGORIA_CONTABLE_CHOICES',
    'get_categoria_contable_choices',
]
