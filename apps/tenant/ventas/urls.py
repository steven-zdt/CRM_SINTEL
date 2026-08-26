from django.urls import path

from .views import VentaTableView
from .views_reportes import VentaReportesContainerView, VentaReportesView

app_name = 'ventas'

urlpatterns = [
    # Tabla server-rendered (django-tables2 + HTMX) — Fase 5-BIS, reemplaza
    # la inicializacion de Tabulator en venta_list.js
    path('tabla/', VentaTableView.as_view(), name='tabla'),
    # Reporte "Resumen de Ventas" -- consume el Reporting Hub (mision
    # Reporting Hub Frontend), no VentaSelector directo.
    path('reportes/', VentaReportesContainerView.as_view(), name='reportes-container'),
    path('reportes/tabla/', VentaReportesView.as_view(), name='reportes-tabla'),
]
