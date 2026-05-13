"""
Choices para el campo 'categoria_contable' del modelo Gasto.

WARNING: v2.40: Categorias contables para clasificacion de gastos.
Basado en categorias contables estandar para Documentos Soporte.
Excluye gastos de personal (salarios, aportes, etc.).
"""

from __future__ import annotations

CATEGORIA_CONTABLE_CHOICES: list[tuple[str, str]] = [
    ("ARRENDAMIENTOS", "Arrendamientos"),
    ("SERVICIOS_PUBLICOS", "Servicios Publicos"),
    ("PAPELERIA_UTILES", "Papeleria y Utiles"),
    ("MANTENIMIENTO_REPARACIONES", "Mantenimiento y Reparaciones"),
    ("EQUIPOS_HERRAMIENTAS", "Equipos y Herramientas"),
    ("LICENCIAS_SOFTWARE", "Licencias y Software"),
    ("HOSTING_DOMINIO", "Hosting y Dominios"),
    ("TRANSPORTE_FLETES", "Transporte y Fletes"),
    ("COMBUSTIBLE", "Combustible"),
    ("VIATICOS", "Viaticos"),
    ("PUBLICIDAD_MARKETING", "Publicidad y Marketing"),
    ("SEGUROS", "Seguros"),
    ("IMPUESTOS_TASAS", "Impuestos, Tasas y Contribuciones"),
    ("HONORARIOS", "Honorarios"),
    ("SERVICIOS_PROFESIONALES", "Servicios Profesionales"),
    ("ASEO_CAFETERIA", "Aseo y Cafeteria"),
    ("VIGILANCIA_SEGURIDAD", "Vigilancia y Seguridad"),
    ("CAPACITACION", "Capacitacion"),
    ("GASTOS_FINANCIEROS", "Gastos Financieros"),
    ("COMISIONES_BANCARIAS", "Comisiones Bancarias"),
    ("SUSCRIPCIONES", "Suscripciones"),
    ("ELEMENTOS_PROTECCION", "Elementos de Proteccion"),
    ("MATERIALES_INSUMOS", "Materiales e Insumos"),
    ("ADECUACIONES_INSTALACIONES", "Adecuaciones e Instalaciones"),
    ("COMUNICACIONES", "Comunicaciones"),
    ("ENERGIA", "Energia"),
    ("LIMPEZA_ASEO", "Limpieza y Aseo"),
    ("TECNOLOGIA_INFORMATICA", "Tecnologia e Informatica"),
    ("GASTOS_LEGALES", "Gastos Legales"),
    ("TRIBUTARIOS", "Gastos Tributarios"),
    ("OTROS", "Otros Gastos"),
]


def get_categoria_contable_choices() -> list[tuple[str, str]]:
    """
    Provee los choices de categoria contable en runtime.
    
    Returns:
        List[Tuple[str, str]]: Lista de opciones (codigo, nombre)
    """
    return CATEGORIA_CONTABLE_CHOICES[:]
