"""
URLs de UI para la app clientes.
"""

from django.urls import path

from apps.tenant.clientes.api.viewsets import ClienteViewSet
from apps.tenant.clientes.views import ClienteKpisView

app_name = "clientes"

urlpatterns = [
    # Lista de clientes (UI)
    path("", ClienteViewSet.as_view({"get": "list", "post": "create"}), name="cliente-list"),
    # KPIs del listado (HTMX) -- la tabla la sirve POST /api/v1/clientes/dt/
    # + DataTables JS, ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md
    path("tabla/", ClienteKpisView.as_view(), name="cliente-tabla"),
    path(
        "gestor-offcanvas/",
        ClienteViewSet.as_view({"get": "gestor_offcanvas"}),
        name="cliente-gestor-offcanvas",
    ),
]
