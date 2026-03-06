# apps/public/impuestos/choices/codigo_tributario.py
# -*- coding: utf-8 -*-
"""
Choices para el campo 'tipo' del modelo CodigoTributario.
Basado en la clasificación DIAN de códigos tributarios.
"""

from __future__ import annotations

from typing import List, Tuple

TIPO_CODIGO_TRIBUTARIO_CHOICES: List[Tuple[str, str]] = [
    ("Responsabilidad", "Responsabilidad"),
    ("Régimen", "Régimen"),
    ("Obligación", "Obligación"),
    ("Otro", "Otro"),
]

def get_tipo_codigo_tributario_choices() -> List[Tuple[str, str]]:
    """Provee los choices de tipo de código tributario en runtime."""
    return TIPO_CODIGO_TRIBUTARIO_CHOICES[:]
