"""Auto-registro del provider de reporting de Ventas (FASE 7/8, mision Reporting Hub)."""


def register() -> None:
    from apps.services.reporting.registry import registry
    from apps.tenant.ventas.reporting.provider import VentasReportProvider

    registry.register(VentasReportProvider())
