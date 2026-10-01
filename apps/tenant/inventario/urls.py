"""
URLs de UI para la app inventario.

WARNING: v3.5: UI URLs para HTMX y templates.
"""

from django.urls import path

from apps.tenant.inventario.api.viewsets import ProductoViewSet
from apps.tenant.inventario.views import (
    ActivoFijoKpisView,
    CategoriaItemTableView,
    ProductoKpisView,
)

app_name = "inventario"

urlpatterns = [
    # Lista de productos (UI)
    path("", ProductoViewSet.as_view({"get": "list", "post": "create"}), name="producto-list"),
    path(
        "gestor-offcanvas/",
        ProductoViewSet.as_view({"get": "gestor_offcanvas"}),
        name="producto-gestor-offcanvas",
    ),
    # Categorias sigue en django-tables2/HTMX -- no migrada en esta pasada
    # (ver docstring de tables.py). movimientos (Kardex) tampoco -- misma
    # razon (vista agregada cross-model, no un listado plano).
    path("categorias/tabla/", CategoriaItemTableView.as_view(), name="categoria-tabla"),
    # Productos/Servicios/Activos Fijos migraron a DataTables -- POST
    # /api/v1/inventario/{productos,servicios,activos}/dt/, ver
    # docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md. ProductoTable/
    # ServicioTable/ActivoFijoTable (django-tables2) retirados. Los KPIs de
    # Productos/Activos Fijos siguen server-rendered via HTMX.
    path("productos/tabla/", ProductoKpisView.as_view(), name="producto-tabla"),
    path("activos/tabla/", ActivoFijoKpisView.as_view(), name="activo-tabla"),
]
