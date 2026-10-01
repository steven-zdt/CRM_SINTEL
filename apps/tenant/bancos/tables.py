"""
Cuentas Bancarias y Extractos Bancarios migraron a DataTables (ver
docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md) -- CuentaBancariaTable
retirada, ver apps/tenant/bancos/api/viewsets.py::CuentaBancariaViewSet.dt();
ExtractoBancarioTable retirada, ver
apps/tenant/bancos/api/viewsets.py::ExtractoBancarioViewSet.dt() (sus KPIs
de conciliacion, BAN-09, se extrajeron a ExtractoBancarioKpisView, ver
views.py). `TransaccionBancaria` no tiene grilla propia -- sus filas ya se
renderizan server-side dentro del offcanvas de detalle de extracto
(offcanvas_detalle_extracto.html), nunca uso Tabulator.

Este modulo no define tablas django-tables2 activas.
"""
