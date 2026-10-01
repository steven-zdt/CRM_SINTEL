from django.urls import path

from apps.tenant.bancos.api.viewsets import ExtractoBancarioViewSet
from apps.tenant.bancos.views import ExtractoBancarioKpisView

app_name = "bancos"

urlpatterns = [
    path("", ExtractoBancarioViewSet.as_view({"get": "list"}), name="bancos-list"),
    # Cuentas y Extractos migraron a DataTables -- POST
    # /api/v1/bancos/{cuentas,extractos}/dt/, ver
    # docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md. KPIs de
    # conciliacion de Extractos (BAN-09) siguen server-rendered via HTMX.
    path("extractos/tabla/", ExtractoBancarioKpisView.as_view(), name="extracto-tabla"),
]
