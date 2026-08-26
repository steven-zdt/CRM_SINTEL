"""Auto-registro del provider de reporting de Inventario (mision Reporting Hub, loop de expansion)."""


def register() -> None:
    from apps.services.reporting.registry import registry
    from apps.tenant.inventario.reporting.provider import InventarioReportProvider

    registry.register(InventarioReportProvider())
