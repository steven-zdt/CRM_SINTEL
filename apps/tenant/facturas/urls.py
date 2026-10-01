"""
URLs de UI para la app facturas.

WARNING: v3.5: UI URLs para HTMX y templates.
"""

from django.urls import path

from apps.tenant.facturas.api.viewsets import FacturaViewSet

app_name = "facturas"

urlpatterns = [
    # Offcanvas para crear/editar facturas
    path(
        "gestor-offcanvas/",
        FacturaViewSet.as_view({"get": "gestor_offcanvas"}),
        name="factura-gestor-offcanvas",
    ),
    # Lista de facturas (UI)
    path("", FacturaViewSet.as_view({"get": "list", "post": "create"}), name="factura-list"),
    # La grilla (Ventas/Compras) migro a DataTables -- POST /api/v1/facturas/dt/
    # (FacturaViewSet.dt()), ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md.
    # FacturaTable/FacturaTableView (django-tables2) retirados.
]
