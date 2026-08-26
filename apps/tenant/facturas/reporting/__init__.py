"""Auto-registro del provider de reporting fiscal de Facturas (mision Tax Service)."""


def register() -> None:
    from apps.services.reporting.registry import registry
    from apps.tenant.facturas.reporting.provider import FacturasTaxReportProvider

    registry.register(FacturasTaxReportProvider())
