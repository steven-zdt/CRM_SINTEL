from django.urls import path

from .views import VentaTableView

app_name = 'ventas'

urlpatterns = [
    # Tabla server-rendered (django-tables2 + HTMX) — Fase 5-BIS, reemplaza
    # la inicializacion de Tabulator en venta_list.js
    path('tabla/', VentaTableView.as_view(), name='tabla'),
]
