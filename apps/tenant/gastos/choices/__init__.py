# -*- coding: utf-8 -*-
"""
Choices para la app de gastos (TENANT_APP).

⚠️ v2.40: Sistema de Documento Soporte Inmutable.
"""

from .centros_costo import (
    CENTRO_COSTO_CHOICES,
    get_centro_costo_choices,
)

from .categoria_contable import (
    CATEGORIA_CONTABLE_CHOICES,
    get_categoria_contable_choices,
)

__all__ = [
    'CENTRO_COSTO_CHOICES',
    'get_centro_costo_choices',
    'CATEGORIA_CONTABLE_CHOICES',
    'get_categoria_contable_choices',
]
