"""
Fase 3 y Fase 33 (mision Bancos v3.0): parser monetario robusto. No requiere
BD -- prueba unitaria pura sobre apps/tenant/bancos/services/parsing/money.py.
"""
from decimal import Decimal

import pytest

from apps.tenant.bancos.services.parsing.money import parse_money


@pytest.mark.parametrize("texto,esperado", [
    ("1,400,000.00", Decimal("1400000.00")),
    ("-1,431,900.00", Decimal("-1431900.00")),
    (".97", Decimal("0.97")),
    ("1.00", Decimal("1.00")),
    ("-100,000.00", Decimal("-100000.00")),
    ("1.400.000,00", Decimal("1400000.00")),
    ("-1.431.900,00", Decimal("-1431900.00")),
])
def test_parse_decimal_formatos_reales_del_extracto(texto, esperado):
    assert parse_money(texto) == esperado


@pytest.mark.parametrize("texto,esperado", [
    ("$ 1,400,000.00", Decimal("1400000.00")),
    ("COP 1.400.000,00", Decimal("1400000.00")),
    ("(100,000.00)", Decimal("-100000.00")),
    ("100,000.00-", Decimal("-100000.00")),
    ("0", Decimal("0.00")),
    ("", Decimal("0.00")),
    (None, Decimal("0.00")),
    ("nan", Decimal("0.00")),
    ("abc", Decimal("0.00")),
])
def test_parse_decimal_casos_extra(texto, esperado):
    assert parse_money(texto) == esperado


def test_parse_decimal_desde_float_y_int():
    assert parse_money(1400000) == Decimal("1400000.00")
    assert parse_money(1400000.5) == Decimal("1400000.50")
    assert parse_money(Decimal("1400000.00")) == Decimal("1400000.00")


def test_parse_decimal_nunca_lanza_excepcion():
    for valor in (float("nan"), object(), [], {}, True, False):
        # No debe lanzar -- siempre devuelve un Decimal valido.
        resultado = parse_money(valor)
        assert isinstance(resultado, Decimal)
