"""Auto-registro del provider de reporting de Gastos (mision Reporting Hub, loop de expansion)."""


def register() -> None:
    from apps.services.reporting.registry import registry
    from apps.tenant.gastos.reporting.provider import GastosReportProvider

    registry.register(GastosReportProvider())
