"""
El "Directorio de Proveedores" y "Cuentas por Pagar" migraron a DataTables
(ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md) -- ProveedorTable/
ProveedorTableView retirados, la grilla la sirve POST /api/v1/proveedores/dt/
(ProveedorViewSet.dt()); CuentasPagarTable/CuentasPagarTableView retirados,
la grilla la sirve POST /api/v1/proveedores/cuentas-pagar/dt/
(CuentasPagarViewSet.dt() -- endpoint MANUAL, no via DataTableServer, ver su
docstring: la fuente es una lista Python, no un QuerySet real).

Este modulo no define vistas HTML activas.
"""
