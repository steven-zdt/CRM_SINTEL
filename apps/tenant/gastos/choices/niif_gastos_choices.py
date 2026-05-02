"""
Choices NIIF para el campo 'codigo_contable' del modelo Gasto (v2.61.7).

Codigos de subcuenta (nivel 6) clase 5 (Gastos) y cuentas de caja/bancos
clase 1 (110505) segun el Plan Unico de Cuentas (PUC) para Colombia - NIIF PYMES.

REGLA: Solo se incluyen codigos de nivel 6 (subcuenta), que son los unicos
que permiten movimientos contables segun normativa NIIF Colombia.
"""
from __future__ import annotations

GASTOS_NIIF_CHOICES: list[tuple[str, str]] = [
    # Clase 5 - Gastos Operacionales de Administracion
    ("510506", "510506 - Honorarios"),
    ("510515", "510515 - Servicios Tecnicos"),
    ("510518", "510518 - Servicios de Aseo y Vigilancia"),
    ("510521", "510521 - Arrendamientos"),
    ("510524", "510524 - Contribuciones y Afiliaciones"),
    ("510527", "510527 - Seguros"),
    ("510530", "510530 - Servicios Publicos"),
    ("510533", "510533 - Gastos de Viaje"),
    ("510536", "510536 - Transporte, Fletes y Acarreos"),
    ("510545", "510545 - Publicidad, Propaganda y Promocion"),
    ("510554", "510554 - Utiles y Papeleria"),
    ("510557", "510557 - Combustibles y Lubricantes"),
    ("510560", "510560 - Envases y Empaques"),
    ("510563", "510563 - Elementos de Aseo y Cafeteria"),
    ("510566", "510566 - Costos y Gastos de Sistemas"),
    ("510569", "510569 - Mantenimiento y Reparaciones"),
    ("510595", "510595 - Gastos Legales"),
    ("510598", "510598 - Amortizaciones"),
    ("519595", "519595 - Gastos Diversos"),
    # Clase 5 - Gastos Operacionales de Ventas
    ("520506", "520506 - Honorarios (Ventas)"),
    ("520521", "520521 - Arrendamientos (Ventas)"),
    ("520530", "520530 - Servicios Publicos (Ventas)"),
    ("520545", "520545 - Publicidad, Propaganda y Promocion (Ventas)"),
    ("520554", "520554 - Utiles y Papeleria (Ventas)"),
    ("520569", "520569 - Mantenimiento y Reparaciones (Ventas)"),
    # Clase 5 - Gastos No Operacionales
    ("530501", "530501 - Financieros"),
    ("530506", "530506 - Perdida en Venta y Retiro de Bienes"),
    ("530520", "530520 - Gastos Extraordinarios"),
    ("530530", "530530 - Comisiones Bancarias"),
    # Clase 1 - Cuentas de Caja y Bancos (para pagos directos)
    ("110505", "110505 - Caja General"),
    ("111005", "111005 - Bancos - Cuenta Corriente"),
    ("111006", "111006 - Bancos - Cuenta de Ahorros"),
]


def get_gastos_niif_choices() -> list[tuple[str, str]]:
    """
    Retorna los choices NIIF en runtime para uso en forms/serializers.

    Returns:
        List[Tuple[str, str]]: Lista de opciones (codigo, descripcion)
    """
    return GASTOS_NIIF_CHOICES[:]


# Conjunto de codigos validos para validacion O(1)
GASTOS_NIIF_CODIGOS_VALIDOS: frozenset = frozenset(codigo for codigo, _ in GASTOS_NIIF_CHOICES)
