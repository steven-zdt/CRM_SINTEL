"""
Exception hierarchy for accounting integration layer.

All accounting errors inherit from ContabilidadError for uniform error handling.
Specific subclasses provide semantic information for retry logic and admin alerts.
"""


class ContabilidadError(Exception):
    """Base exception for all accounting integration errors."""
    pass


class PeriodoCerradoError(ContabilidadError):
    """Raised when attempting to create entry in closed accounting period."""
    pass


class ReglaContableNoDefinidaError(ContabilidadError):
    """Raised when no accounting rule is configured for transaction type + line concept."""
    pass


class AsientoNoCuadradoError(ContabilidadError):
    """Raised when journal entry debit != credit (internal validation error)."""
    pass


class AsientoYaExisteError(ContabilidadError):
    """
    Raised when attempting to materialize transaction that already has an entry.
    Indicates idempotence failure or duplicate submission.
    """
    pass


class TarifaNoVigenteError(ContabilidadError):
    """Raised when tax rate not defined for transaction date."""
    pass


class DocumentoOrigenInvalidoError(ContabilidadError):
    """Raised when document_origen references non-existent source record."""
    pass


class ConfiguracionContableIncompleteError(ContabilidadError):
    """Raised when tenant configuration is incomplete or corrupted."""
    pass
