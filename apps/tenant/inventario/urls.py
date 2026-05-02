"""
URLs de UI para la app inventario.

WARNING: v3.5: UI URLs para HTMX y templates.
"""
from django.urls import path

from apps.tenant.inventario.api.viewsets import ProductoViewSet

app_name = 'inventario'

urlpatterns = [
    # Lista de productos (UI)
    path('', 
         ProductoViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='producto-list'),
    path('gestor-offcanvas/', 
         ProductoViewSet.as_view({'get': 'gestor_offcanvas'}), 
         name='producto-gestor-offcanvas'),
]
