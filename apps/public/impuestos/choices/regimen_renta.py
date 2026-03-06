# apps/public/impuestos/choices/regimen_renta.py
# -*- coding: utf-8 -*-
"""
Choices para el campo 'codigo' del modelo RegimenRenta.
Basado en la normativa DIAN:
- Ley 1819 de 2016 (Régimen Simple de Tributación - SIMPLE)
- Ley 1943 de 2018 (Régimen Tributario Especial - RTE)
- Régimen Ordinario (ORDINARIO)
"""

from __future__ import annotations

from typing import List, Tuple

REGIMEN_RENTA_CHOICES: List[Tuple[str, str]] = [
    ("ORDINARIO", "Régimen Ordinario"),
    ("ESPECIAL", "Régimen Tributario Especial (RTE)"),
    ("SIMPLE", "Régimen Simple de Tributación (SIMPLE)"),
]

def get_regimen_renta_choices() -> List[Tuple[str, str]]:
    """
    Provee los choices en runtime por si se prefiere inyectarlos
    dinámicamente en serializers/forms (recomendado).
    """
    return REGIMEN_RENTA_CHOICES[:]
