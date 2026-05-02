"""
Choices NIIF para el campo 'codigo_contable' del modelo Proveedor (v2.61.8).

Codigos de subcuenta (nivel 6) clase 2 (Pasivos) segun el Plan Unico de Cuentas (PUC) 
para Colombia - NIIF PYMES.
"""
from __future__ import annotations

PROVEEDORES_NIIF_CHOICES: list[tuple[str, str]] = [
    # Clase 2 - Pasivos: Obligaciones Financieras
    ("210505", "210505 - Bancos Nacionales"),
    ("210510", "210510 - Bancos del Exterior"),
    
    # Clase 2 - Pasivos: Proveedores
    ("220501", "220501 - Proveedores Nacionales"),
    ("220505", "220505 - Proveedores del Exterior"),
    ("221005", "221005 - Casa Matriz"),
    
    # Clase 2 - Pasivos: Cuentas por Pagar (Costos y Gastos)
    ("233505", "233505 - Gastos Legales p/p"),
    ("233510", "233510 - Comisiones p/p"),
    ("233515", "233515 - Libros, Suscripciones y Revistas p/p"),
    ("233520", "233520 - Comisiones y Honorarios p/p"),
    ("233525", "233525 - Honorarios p/p"),
    ("233530", "233530 - Servicios Tecnicos p/p"),
    ("233535", "233535 - Mantenimiento y Reparaciones p/p"),
    ("233540", "233540 - Arrendamientos p/p"),
    ("233545", "233545 - Transportes, Fletes y Acarreos p/p"),
    ("233550", "233550 - Servicios Publicos p/p"),
    ("233555", "233555 - Seguros p/p"),
    ("233560", "233560 - Gastos de Viaje p/p"),
    ("233565", "233565 - Gastos de Representacion y Relaciones Publicas p/p"),
    ("233570", "233570 - Servicios de Aseo y Vigilancia p/p"),
    ("233595", "233595 - Otros p/p"),
    
    # Clase 2 - Pasivos: Retenciones
    ("236505", "236505 - Retencion en la Fuente (Salarios)"),
    ("236515", "236515 - Retencion en la Fuente (Honorarios)"),
    ("236525", "236525 - Retencion en la Fuente (Servicios)"),
    ("236540", "236540 - Retencion en la Fuente (Compras)"),
    ("236701", "236701 - Impuesto sobre las ventas retenido (IVA)"),
    ("236801", "236801 - Impuesto de industria y comercio retenido (ICA)"),
]


def get_proveedores_niif_choices() -> list[tuple[str, str]]:
    """
    Retorna los choices NIIF en runtime.
    """
    return PROVEEDORES_NIIF_CHOICES[:]


# Conjunto de codigos validos para validacion O(1)
PROVEEDORES_NIIF_CODIGOS_VALIDOS: frozenset = frozenset(codigo for codigo, _ in PROVEEDORES_NIIF_CHOICES)
