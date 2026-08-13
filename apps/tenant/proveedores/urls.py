"""
URLs de UI para la app proveedores.

WARNING: v3.5: UI URLs para HTMX y templates.
"""
from django.urls import path

from apps.tenant.proveedores.api.viewsets import ProveedorViewSet
from apps.tenant.proveedores.views import CuentasPagarTableView, ProveedorTableView

app_name = 'proveedores'

urlpatterns = [
    # Lista de proveedores (UI)
    path('',
         ProveedorViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='proveedor-list'),
    # Tabla server-rendered (django-tables2 + HTMX) — Fase 5-BIS, reemplaza
    # la grilla "Directorio de Proveedores" de proveedores_main.js
    path('tabla/', ProveedorTableView.as_view(), name='proveedor-tabla'),
    # Idem para Cuentas por Pagar — reemplaza la grilla en cuentas_pagar_list.js
    # (que nunca se renderizaba: init() nunca era llamado desde proveedores_main.js)
    path('cuentas-pagar/tabla/', CuentasPagarTableView.as_view(), name='cuentas-pagar-tabla'),
    path('gestor-offcanvas/',
         ProveedorViewSet.as_view({'get': 'gestor_offcanvas'}),
         name='proveedor-gestor-offcanvas'),
]
