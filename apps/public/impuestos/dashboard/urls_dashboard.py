"""
URLs del dashboard de ingesta.

Rutas bajo el prefijo /console/impuestos/
"""
from django.urls import path
from apps.public.impuestos.dashboard.views_dashboard import (
    HomeImpuestosView,
    IngestaListView,
    IngestaCreateView,
    IngestaDetailView,
    htmx_refresh_row,
    htmx_logs_fragment,
    action_reintentar_descarga,
    action_reintentar_procesar,
)

app_name = "impuestos_dashboard"

urlpatterns = [
    # Home del módulo
    path("", HomeImpuestosView.as_view(), name="home"),
    
    # Vistas principales
    path("ingesta/", IngestaListView.as_view(), name="ingesta_list"),
    path("ingesta/nuevo/", IngestaCreateView.as_view(), name="ingesta_create"),
    path("ingesta/<int:pk>/", IngestaDetailView.as_view(), name="ingesta_detail"),
    
    # HTMX fragments
    path("ingesta/<int:pk>/row/", htmx_refresh_row, name="ingesta_row"),
    path("ingesta/<int:pk>/logs/", htmx_logs_fragment, name="ingesta_logs"),
    
    # Acciones
    path("ingesta/<int:pk>/reintentar-descarga/", action_reintentar_descarga, name="reintentar_descarga"),
    path("ingesta/<int:pk>/reintentar-procesar/", action_reintentar_procesar, name="reintentar_procesar"),
]
