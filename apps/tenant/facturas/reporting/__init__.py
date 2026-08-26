"""Auto-registro de los providers de reporting de Facturas.

Dos providers, un dataset cada uno (mismo patron que ventas/inventario/
gastos): FacturasTaxReportProvider (tax.iva, mision Tax Service) y
FacturasResumenReportProvider (facturas.resumen, loop de expansion)."""


def register() -> None:
    from apps.services.reporting.registry import registry
    from apps.tenant.facturas.reporting.provider import FacturasTaxReportProvider
    from apps.tenant.facturas.reporting.provider_resumen import FacturasResumenReportProvider

    registry.register(FacturasTaxReportProvider())
    registry.register(FacturasResumenReportProvider())
