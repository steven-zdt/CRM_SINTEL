"""
Choices para el campo 'centro_costo' del modelo Gasto.

WARNING: v2.40: Centros de costo para clasificacion contable de gastos.
Basado en categorias contables estandar para Documentos Soporte.
"""

from __future__ import annotations

CENTRO_COSTO_CHOICES: list[tuple[str, str]] = [
    ("ADMINISTRATIVOS", "Administrativos"),
    ("MATERIA_PRIMA", "Materia Prima"),
    ("MANUTENCION", "Mantenimiento"),
    ("VIATICOS", "Viaticos"),
    ("SERVICIOS_PUBLICOS", "Servicios Publicos"),
    ("TRANSPORTE", "Transporte"),
    ("COMUNICACIONES", "Comunicaciones"),
    ("SEGUROS", "Seguros"),
    ("ARRIENDOS", "Arriendos"),
    ("SERVICIOS_PROFESIONALES", "Servicios Profesionales"),
    ("PUBLICIDAD", "Publicidad y Marketing"),
    ("CAPACITACION", "Capacitacion"),
    ("HERRAMIENTAS", "Herramientas y Equipos"),
    ("INSUMOS", "Insumos y Materiales"),
    ("ENERGIA", "Energia y Combustibles"),
    ("LIMPEZA", "Limpieza y Aseo"),
    ("SEGURIDAD", "Seguridad"),
    ("TECNOLOGIA", "Tecnologia e Informatica"),
    ("LEGALES", "Gastos Legales"),
    ("TRIBUTARIOS", "Gastos Tributarios"),
    ("OTROS", "Otros Gastos"),
]


def get_centro_costo_choices() -> list[tuple[str, str]]:
    """
    Provee los choices de centro de costo en runtime.
    
    Returns:
        List[Tuple[str, str]]: Lista de opciones (codigo, nombre)
    """
    return CENTRO_COSTO_CHOICES[:]
