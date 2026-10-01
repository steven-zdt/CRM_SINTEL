"""
Ambas grillas de Gastos (Documentos Soporte y Resoluciones DIAN) migraron a
DataTables -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md.
DocumentoSoporteTable retirada, ver
apps/tenant/gastos/api/viewsets.py::GastoViewSet.dt(); ResolucionDIANTable
retirada, ver apps/tenant/gastos/api/viewsets.py::ResolucionDIANViewSet.dt().
Este modulo no define tablas django-tables2 activas.
"""
