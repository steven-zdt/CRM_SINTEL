"""
Cuentas, Periodos, Asientos, Retenciones y Plantillas Contables migraron a
DataTables (ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md) --
CuentaContableTable retirada, ver CuentaContableViewSet.dt();
PeriodoContableTable retirada, ver PeriodoContableViewSet.dt();
AsientoContableTable retirada, ver AsientoContableViewSet.dt();
RetencionTable retirada, ver RetencionViewSet.dt(); PlantillaContableTable
retirada, ver PlantillaContableViewSet.dt().

Los listados restantes (pendientes, libro-diario, reportes) NO son listados
CRUD planos -- son vistas agregadas/cross-app (ver
REPORTE_FASE_5_BIS_CONTABILIDAD.md). Pendientes migro igual a DataTables
via un endpoint MANUAL (DocumentosPendientesViewSet.dt(), su fuente mezcla
4 modelos de 4 apps en una lista Python, no un QuerySet real). Libro-diario
y reportes quedan fuera de este patron por ahora.

Este modulo no define tablas django-tables2 activas.
"""
