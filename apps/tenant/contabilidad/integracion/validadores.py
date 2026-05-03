"""
Validators for journal entry integrity and accounting principles compliance.

Each validator is a stateless function that checks a specific invariant.
They're composed into a validation pipeline during materialization.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from .excepciones import AsientoNoCuadradoError, PeriodoCerradoError

if TYPE_CHECKING:
    from django.contrib.contenttypes.models import ContentType
    from ..models import AsientoContable, PeriodoContable


def validar_cuadratura(debe: Decimal, haber: Decimal) -> None:
    """
    Verify double-entry bookkeeping: debit must equal credit.

    Args:
        debe: Sum of all debit entries
        haber: Sum of all credit entries

    Raises:
        AsientoNoCuadradoError: If debe ≠ haber
    """
    if debe != haber:
        raise AsientoNoCuadradoError(
            f"Asiento no cuadra: DEBE={debe} ≠ HABER={haber}"
        )


def validar_periodo_abierto(periodo: 'PeriodoContable') -> None:
    """
    Verify that accounting period is open for new entries.

    Args:
        periodo: Period to check

    Raises:
        PeriodoCerradoError: If period is closed
    """
    if periodo.estado == 'CERRADO':
        raise PeriodoCerradoError(
            f"Período {periodo.nombre} está cerrado. No se pueden crear asientos nuevos."
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
        raise AsientoNoCuadradoError("Asiento vacío: no tiene movimientos")


def validar_documento_origen_existe(
    documento_origen_app: str,
    documento_origen_modelo: str,
    documento_origen_id: int
) -> None:
    """
    Verify that source document exists in origin app.

    Args:
        documento_origen_app: App label (facturas, gastos, etc.)
        documento_origen_modelo: Model name (Factura, DocumentoSoporte, etc.)
        documento_origen_id: PK in source app

    Raises:
        DocumentoOrigenInvalidoError: If document not found
    """
    from django.apps import apps
    from .excepciones import DocumentoOrigenInvalidoError

    try:
        app_config = apps.get_app_config(documento_origen_app)
        model = app_config.get_model(documento_origen_modelo.lower())
        if not model.objects.filter(pk=documento_origen_id).exists():
            raise DocumentoOrigenInvalidoError(
                f"Documento origen no existe: {documento_origen_app}.{documento_origen_modelo}[{documento_origen_id}]"
            )
    except (LookupError, ValueError) as e:
        raise DocumentoOrigenInvalidoError(
            f"Documento origen inválido: {documento_origen_app}.{documento_origen_modelo} — {e}"
        )
