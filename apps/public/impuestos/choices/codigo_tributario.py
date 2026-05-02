# apps/public/impuestos/choices/codigo_tributario.py
"""
Choices para el campo 'tipo' del modelo CodigoTributario.
Basado en la clasificación DIAN de códigos tributarios.
"""

from __future__ import annotations

TIPO_CODIGO_TRIBUTARIO_CHOICES: list[tuple[str, str]] = [
    ("Responsabilidad", "Responsabilidad"),
    ("Régimen", "Régimen"),
    ("Obligación", "Obligación"),
    ("Otro", "Otro"),
]


def get_tipo_codigo_tributario_choices() -> list[tuple[str, str]]:
    """Provee los choices de tipo de código tributario en runtime."""
    return TIPO_CODIGO_TRIBUTARIO_CHOICES[:]
