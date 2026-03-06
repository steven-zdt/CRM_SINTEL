# -*- coding: utf-8 -*-
"""
Choices para el campo 'categoria_contable' del modelo Gasto.

⚠️ v2.40: Categorías contables para clasificación de gastos.
Basado en categorías contables estándar para Documentos Soporte.
Excluye gastos de personal (salarios, aportes, etc.).
"""

from __future__ import annotations

from typing import List, Tuple

CATEGORIA_CONTABLE_CHOICES: List[Tuple[str, str]] = [
    ("ARRENDAMIENTOS", "Arrendamientos"),
    ("SERVICIOS_PUBLICOS", "Servicios Públicos"),
    ("PAPELERIA_UTILES", "Papelería y Útiles"),
    ("MANTENIMIENTO_REPARACIONES", "Mantenimiento y Reparaciones"),
    ("EQUIPOS_HERRAMIENTAS", "Equipos y Herramientas"),
    ("LICENCIAS_SOFTWARE", "Licencias y Software"),
    ("HOSTING_DOMINIO", "Hosting y Dominios"),
    ("TRANSPORTE_FLETES", "Transporte y Fletes"),
    ("COMBUSTIBLE", "Combustible"),
    ("VIATICOS", "Viáticos"),
    ("PUBLICIDAD_MARKETING", "Publicidad y Marketing"),
    ("SEGUROS", "Seguros"),
    ("IMPUESTOS_TASAS", "Impuestos, Tasas y Contribuciones"),
    ("HONORARIOS", "Honorarios"),
    ("SERVICIOS_PROFESIONALES", "Servicios Profesionales"),
    ("ASEO_CAFETERIA", "Aseo y Cafetería"),
    ("VIGILANCIA_SEGURIDAD", "Vigilancia y Seguridad"),
    ("CAPACITACION", "Capacitación"),
    ("GASTOS_FINANCIEROS", "Gastos Financieros"),
    ("COMISIONES_BANCARIAS", "Comisiones Bancarias"),
    ("SUSCRIPCIONES", "Suscripciones"),
    ("ELEMENTOS_PROTECCION", "Elementos de Protección"),
    ("MATERIALES_INSUMOS", "Materiales e Insumos"),
    ("ADECUACIONES_INSTALACIONES", "Adecuaciones e Instalaciones"),
    ("COMUNICACIONES", "Comunicaciones"),
    ("ENERGIA", "Energía"),
    ("LIMPEZA_ASEO", "Limpieza y Aseo"),
    ("TECNOLOGIA_INFORMATICA", "Tecnología e Informática"),
    ("GASTOS_LEGALES", "Gastos Legales"),
    ("TRIBUTARIOS", "Gastos Tributarios"),
    ("OTROS", "Otros Gastos"),
]


def get_categoria_contable_choices() -> List[Tuple[str, str]]:
    """
    Provee los choices de categoría contable en runtime.
    
    Returns:
        List[Tuple[str, str]]: Lista de opciones (código, nombre)
    """
    return CATEGORIA_CONTABLE_CHOICES[:]
