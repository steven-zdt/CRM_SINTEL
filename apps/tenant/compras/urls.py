from django.urls import path

from .api.viewsets import OrdenCompraViewSet
from .views import OrdenCompraKpisView

app_name = "compras"

urlpatterns = [
    # UI actions mapped to viewset actions
    path(
        "", OrdenCompraViewSet.as_view({"get": "list", "post": "create"}), name="orden-compra-list"
    ),
    # KPIs del listado (HTMX) -- la tabla la sirve POST /api/v1/compras/dt/
    # + DataTables JS, ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md
    path("tabla/", OrdenCompraKpisView.as_view(), name="tabla"),
    # "Plantillas de Numeracion" migro a DataTables -- POST
    # /api/v1/compras/plantillas/dt/ (PlantillaOrdenCompraViewSet.dt()).
    # PlantillaOrdenCompraTable/PlantillaOrdenCompraTableView (django-tables2)
    # retirados.
]
