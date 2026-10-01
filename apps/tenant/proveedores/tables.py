"""
El "Directorio de Proveedores" y "Cuentas por Pagar" migraron a DataTables
(ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md) -- ProveedorTable
retirada, ver ProveedorViewSet.dt(); CuentasPagarTable retirada, ver
CuentasPagarViewSet.dt() (endpoint MANUAL: CuentasPagarSelector.
qs_list_unificado() mezcla Factura(COMPRA) + CuentasPagar en una lista
Python, no un QuerySet real -- incompatible con DataTableServer sin este
trabajo aparte).

Este modulo no define tablas django-tables2 activas.
"""
