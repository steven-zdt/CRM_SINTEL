"""
URLs de UI para la app facturas.

WARNING: v3.5: UI URLs para HTMX y templates.
"""
from django.urls import path

from apps.tenant.facturas.api.viewsets import FacturaViewSet

app_name = 'facturas'

urlpatterns = [
    # Offcanvas para crear/editar facturas
    path('gestor-offcanvas/', 
         FacturaViewSet.as_view({'get': 'gestor_offcanvas'}), 
         name='factura-gestor-offcanvas'),
    # Lista de facturas (UI)
    path('', 
         FacturaViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='factura-list'),
]
