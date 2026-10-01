"""
URLs de UI para la app contabilidad.

WARNING: v3.5: UI URLs para HTMX y templates.
"""

from django.urls import path

from apps.tenant.contabilidad.api.viewsets import (
    AsientoContableViewSet,
    CuentaContableViewSet,
    PeriodoContableViewSet,
)

app_name = "contabilidad"

urlpatterns = [
    # Cuentas contables
    path(
        "cuentas/",
        CuentaContableViewSet.as_view({"get": "list", "post": "create"}),
        name="cuenta-list",
    ),
    path(
        "cuentas/gestor-offcanvas/",
        CuentaContableViewSet.as_view({"get": "gestor_offcanvas"}),
        name="cuenta-gestor-offcanvas",
    ),
    # Asientos contables
    path(
        "asientos/",
        AsientoContableViewSet.as_view({"get": "list", "post": "create"}),
        name="asiento-list",
    ),
    path(
        "asientos/gestor-offcanvas/",
        AsientoContableViewSet.as_view({"get": "gestor_offcanvas"}),
        name="asiento-gestor-offcanvas",
    ),
    # Periodos contables
    path(
        "periodos/",
        PeriodoContableViewSet.as_view({"get": "list", "post": "create"}),
        name="periodo-list",
    ),
    path(
        "periodos/gestor-offcanvas/",
        PeriodoContableViewSet.as_view({"get": "gestor_offcanvas"}),
        name="periodo-gestor-offcanvas",
    ),
    # Cuentas, Asientos, Periodos, Retenciones y Plantillas migraron a
    # DataTables -- POST /api/v1/contabilidad/{cuentas-contables,
    # asientos-contables,periodos-contables,retenciones,plantillas-contables}/dt/,
    # ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md.
    # CuentaContableTable/AsientoContableTable/PeriodoContableTable/
    # RetencionTable/PlantillaContableTable (django-tables2) retirados junto
    # con sus TableView.
    # Reportes
    path("reportes/", AsientoContableViewSet.as_view({"get": "reporte_page"}), name="reporte-page"),
]
