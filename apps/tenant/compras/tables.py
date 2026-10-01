"""
Ambas grillas de Compras (Ordenes de Compra y Plantillas de Numeracion)
migraron a DataTables -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md.
OrdenCompraTable retirada, ver
apps/tenant/compras/api/viewsets.py::OrdenCompraViewSet.dt(); Plantilla
OrdenCompraTable retirada, ver
apps/tenant/compras/api/viewsets.py::PlantillaOrdenCompraViewSet.dt().

Este modulo no define tablas django-tables2 activas.
"""
