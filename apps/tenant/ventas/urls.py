from django.urls import path

from .views import VentaKpisView
from .views_reportes import VentaReportesContainerView, VentaReportesView

app_name = "ventas"

urlpatterns = [
    # KPIs del listado de Ventas (HTMX) -- la tabla la sirve POST
    # /api/v1/ventas/dt/ + DataTables JS (ver DATATABLES_PILOT_VENTAS_STATUS.md)
    path("tabla/", VentaKpisView.as_view(), name="tabla"),
    # Reporte "Resumen de Ventas" -- consume el Reporting Hub (mision
    # Reporting Hub Frontend), no VentaSelector directo.
    path("reportes/", VentaReportesContainerView.as_view(), name="reportes-container"),
    path("reportes/tabla/", VentaReportesView.as_view(), name="reportes-tabla"),
]
