"""
URLs de UI para la app gastos.

WARNING: v3.5: UI URLs para HTMX y templates.
- Las APIs estan en api/urls.py (DRF)
- Estas URLs son para cargar offcanvas y partials HTML
"""

from django.urls import path

from apps.tenant.gastos.api.viewsets import GastoViewSet
from apps.tenant.gastos.views import GastoKpisView

app_name = "gastos"

urlpatterns = [
    # Offcanvas para crear/editar gastos
    path(
        "gestor-offcanvas/",
        GastoViewSet.as_view({"get": "gestor_offcanvas"}),
        name="gasto-gestor-offcanvas",
    ),
    # Lista de gastos (UI)
    path("", GastoViewSet.as_view({"get": "list", "post": "create"}), name="gasto-list"),
    # KPIs del listado "Gastos" (HTMX) -- la tabla la sirve POST
    # /api/v1/gastos/dt/ + DataTables JS, ver
    # docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md
    path("tabla-documentos/", GastoKpisView.as_view(), name="documentos-tabla"),
    # "Resoluciones DIAN" migro a DataTables -- POST
    # /api/v1/gastos/resoluciones/dt/ (ResolucionDIANViewSet.dt()).
    # ResolucionDIANTable/ResolucionDIANTableView (django-tables2) retirados.
]
