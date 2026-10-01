"""
URLs de UI para la app empleados.

WARNING: v3.5: UI URLs para HTMX y templates.
- Las APIs están en api/urls.py (DRF)
- Estas URLs son para cargar offcanvas y partials HTML
"""

from django.urls import path

from apps.tenant.empleados.api.viewsets import EmpleadoViewSet
from apps.tenant.empleados.views import (
    LiquidacionDetailTableView,
    NominaDetailTableView,
)

app_name = "empleados"

# ViewSet instanciado para métodos de acción
empleado_viewset = EmpleadoViewSet()

urlpatterns = [
    # Offcanvas para crear/editar empleados
    path(
        "gestor-offcanvas/",
        EmpleadoViewSet.as_view({"get": "gestor_offcanvas"}),
        name="empleado-gestor-offcanvas",
    ),
    # Lista de empleados (UI)
    path("", EmpleadoViewSet.as_view({"get": "list", "post": "create"}), name="empleado-list"),
    # Directorio de Empleados/Contratos/Resoluciones DIAN/Periodos de Nomina
    # y los Master de Nominas/Liquidaciones migraron a DataTables -- POST
    # /api/v1/empleados/{dt,contratos/dt,resoluciones-dian/dt,periodos-nomina/dt,
    # con-nominas/dt,con-liquidaciones/dt}/, ver
    # docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md. EmpleadoTable/
    # ContratoTable/ResolucionDIANTable/PeriodoNominaTable/
    # NominaEmpleadoMasterTable/LiquidacionEmpleadoMasterTable (django-tables2)
    # retirados junto con sus TableView.
    #
    # Master-Detail: los paneles Detail (historial del empleado seleccionado
    # en el Master) siguen en django-tables2 + HTMX -- no son listados planos
    # independientes, dependen de la seleccion hecha en el Master.
    path("nominas/detalle/tabla/", NominaDetailTableView.as_view(), name="nomina-detalle-tabla"),
    path(
        "liquidaciones/detalle/tabla/",
        LiquidacionDetailTableView.as_view(),
        name="liquidacion-detalle-tabla",
    ),
]
