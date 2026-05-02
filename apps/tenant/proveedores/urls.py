"""
URLs de UI para la app proveedores.

WARNING: v3.5: UI URLs para HTMX y templates.
"""
from django.urls import path

from apps.tenant.proveedores.api.viewsets import ProveedorViewSet

app_name = 'proveedores'

urlpatterns = [
    # Lista de proveedores (UI)
    path('', 
         ProveedorViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='proveedor-list'),
    path('gestor-offcanvas/', 
         ProveedorViewSet.as_view({'get': 'gestor_offcanvas'}), 
         name='proveedor-gestor-offcanvas'),
]
