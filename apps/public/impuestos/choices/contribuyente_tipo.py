# apps/public/impuestos/choices/contribuyente_tipo.py
# -*- coding: utf-8 -*-
"""
Choices para los campos 'clase' y 'segmento_dian' del modelo ContribuyenteTipo.
Basado en la clasificación DIAN según Resolución 000013 de 2020.
"""

from __future__ import annotations

from typing import List, Tuple

CLASE_CHOICES: List[Tuple[str, str]] = [
    ("PN", "Persona Natural"),
    ("PJ", "Persona Jurídica"),
]

SEGMENTO_DIAN_CHOICES: List[Tuple[str, str]] = [
    ("GRAN_CONTRIBUYENTE", "Gran contribuyente"),
    ("MEDIANO_ALTO", "Contribuyente mediano alto"),
    ("MEDIANO", "Contribuyente mediano"),
    ("PEQUENO", "Contribuyente pequeño"),
    ("MICRO", "Contribuyente micro"),
    ("OTRO", "Otro / No aplica"),
]

def get_clase_choices() -> List[Tuple[str, str]]:
    """Provee los choices de clase en runtime."""
    return CLASE_CHOICES[:]

def get_segmento_dian_choices() -> List[Tuple[str, str]]:
    """Provee los choices de segmento DIAN en runtime."""
    return SEGMENTO_DIAN_CHOICES[:]
