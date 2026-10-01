"""
Cuentas, Periodos, Asientos, Retenciones y Plantillas Contables migraron a
DataTables (ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md) --
CuentaContableTable/CuentaContableTableView, PeriodoContableTable/
PeriodoContableTableView, AsientoContableTable/AsientoContableTableView,
RetencionTable/RetencionTableView y PlantillaContableTable/
PlantillaContableTableView (django-tables2) retirados, ver
apps/tenant/contabilidad/api/viewsets.py (CuentaContableViewSet.dt()/
AsientoContableViewSet.dt()/PeriodoContableViewSet.dt()/RetencionViewSet.dt()/
PlantillaContableViewSet.dt()).

No reemplazan la API DRF (apps/tenant/contabilidad/api/viewsets.py), que
sigue viva para crear/editar/aprobar/cerrar y para consumidores API-first.

Este modulo no define vistas HTML activas.
"""
