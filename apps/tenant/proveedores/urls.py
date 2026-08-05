"""
URLs de UI para la app proveedores.

WARNING: v3.5: UI URLs para HTMX y templates.
"""
from django.urls import path

from apps.tenant.proveedores.api.viewsets import ProveedorViewSet
from apps.tenant.proveedores.views import ProveedorTableView

app_name = 'proveedores'

urlpatterns = [
    # Lista de proveedores (UI)
    path('',
         ProveedorViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='proveedor-list'),
    # Tabla server-rendered (django-tables2 + HTMX) — Fase 5-BIS, reemplaza
    # la grilla "Directorio de Proveedores" de proveedores_main.js
    path('tabla/', ProveedorTableView.as_view(), name='proveedor-tabla'),
    path('gestor-offcanvas/',
         ProveedorViewSet.as_view({'get': 'gestor_offcanvas'}),
         name='proveedor-gestor-offcanvas'),
]
