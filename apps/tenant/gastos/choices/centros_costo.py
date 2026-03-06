# -*- coding: utf-8 -*-
"""
Choices para el campo 'centro_costo' del modelo Gasto.

⚠️ v2.40: Centros de costo para clasificación contable de gastos.
Basado en categorías contables estándar para Documentos Soporte.
"""

from __future__ import annotations

from typing import List, Tuple

CENTRO_COSTO_CHOICES: List[Tuple[str, str]] = [
    ("ADMINISTRATIVOS", "Administrativos"),
    ("MATERIA_PRIMA", "Materia Prima"),
    ("MANUTENCION", "Mantenimiento"),
    ("VIATICOS", "Viáticos"),
    ("SERVICIOS_PUBLICOS", "Servicios Públicos"),
    ("TRANSPORTE", "Transporte"),
    ("COMUNICACIONES", "Comunicaciones"),
    ("SEGUROS", "Seguros"),
    ("ARRIENDOS", "Arriendos"),
    ("SERVICIOS_PROFESIONALES", "Servicios Profesionales"),
    ("PUBLICIDAD", "Publicidad y Marketing"),
    ("CAPACITACION", "Capacitación"),
    ("HERRAMIENTAS", "Herramientas y Equipos"),
    ("INSUMOS", "Insumos y Materiales"),
    ("ENERGIA", "Energía y Combustibles"),
    ("LIMPEZA", "Limpieza y Aseo"),
    ("SEGURIDAD", "Seguridad"),
    ("TECNOLOGIA", "Tecnología e Informática"),
    ("LEGALES", "Gastos Legales"),
    ("TRIBUTARIOS", "Gastos Tributarios"),
    ("OTROS", "Otros Gastos"),
]


def get_centro_costo_choices() -> List[Tuple[str, str]]:
    """
    Provee los choices de centro de costo en runtime.
    
    Returns:
        List[Tuple[str, str]]: Lista de opciones (código, nombre)
    """
    return CENTRO_COSTO_CHOICES[:]
