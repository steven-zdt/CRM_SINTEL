from django.urls import path
from apps.tenant.bancos.api.viewsets import ExtractoBancarioViewSet
from apps.tenant.bancos.views import CuentaBancariaTableView, ExtractoBancarioTableView

app_name = "bancos"

urlpatterns = [
    path("", ExtractoBancarioViewSet.as_view({"get": "list"}), name="bancos-list"),
    # Tablas server-rendered (django-tables2 + HTMX) — Fase 5-BIS, reemplazan
    # la inicializacion de Tabulator en cuenta_list.js / extracto_list.js
    path("cuentas/tabla/", CuentaBancariaTableView.as_view(), name="cuenta-tabla"),
    path("extractos/tabla/", ExtractoBancarioTableView.as_view(), name="extracto-tabla"),
]
