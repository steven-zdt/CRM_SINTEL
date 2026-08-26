"""Auto-registro del provider de reporting de Contabilidad (FASE 19, mision Reporting Hub)."""


def register() -> None:
    from apps.services.reporting.registry import registry
    from apps.tenant.contabilidad.reporting.provider import ContabilidadReportProvider

    registry.register(ContabilidadReportProvider())
