"""
Validators for journal entry integrity and accounting principles compliance.

Each validator is a stateless function that checks a specific invariant.
They're composed into a validation pipeline during materialization.
"""

from decimal import Decimal

from ..models import PeriodoContable
from .excepciones import AsientoNoCuadradoError, PeriodoCerradoError


def validar_cuadratura(debe: Decimal, haber: Decimal) -> None:
    """
    Verify double-entry bookkeeping: debit must equal credit.

    Args:
        debe: Sum of all debit entries
        haber: Sum of all credit entries

    Raises:
        AsientoNoCuadradoError: If debe != haber
    """
    if debe != haber:
        raise AsientoNoCuadradoError(
            f"Asiento no cuadra: DEBE={debe} != HABER={haber}"
        )


def validar_periodo_abierto(periodo: PeriodoContable) -> None:
    """
    Verify that accounting period is open for new entries.

    Args:
        periodo: Period to check

    Raises:
        PeriodoCerradoError: If period is closed
    """
    if periodo.estado == 'CERRADO':
        raise PeriodoCerradoError(
            f"Periodo {periodo.periodo} esta cerrado. No se pueden crear asientos nuevos."
        )


def validar_no_vacio(debe: Decimal, haber: Decimal) -> None:
    """
    Verify entry has at least one debit and one credit line.

    Args:
        debe: Sum of debit entries
        haber: Sum of credit entries

    Raises:
        AsientoNoCuadradoError: If entry is empty
    """
    if debe == 0 and haber == 0:
        raise AsientoNoCuadradoError("Asiento vacio: no tiene movimientos")


