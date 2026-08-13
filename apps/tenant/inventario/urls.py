"""
URLs de UI para la app inventario.

WARNING: v3.5: UI URLs para HTMX y templates.
"""
from django.urls import path

from apps.tenant.inventario.api.viewsets import ProductoViewSet
from apps.tenant.inventario.views import (
    ActivoFijoTableView,
    CategoriaItemTableView,
    ProductoTableView,
    ServicioTableView,
)

app_name = 'inventario'

urlpatterns = [
    # Lista de productos (UI)
    path('',
         ProductoViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='producto-list'),
    path('gestor-offcanvas/',
         ProductoViewSet.as_view({'get': 'gestor_offcanvas'}),
         name='producto-gestor-offcanvas'),
    # Tablas server-rendered (django-tables2 + HTMX) — Fase 5-BIS, reemplazan
    # la inicializacion de Tabulator en categorias_list.js / productos_list.js /
    # servicios_list.js / activos_list.js. movimientos (Kardex) queda fuera
    # de alcance (ver docstring de tables.py).
    path('categorias/tabla/', CategoriaItemTableView.as_view(), name='categoria-tabla'),
    path('productos/tabla/', ProductoTableView.as_view(), name='producto-tabla'),
    path('servicios/tabla/', ServicioTableView.as_view(), name='servicio-tabla'),
    path('activos/tabla/', ActivoFijoTableView.as_view(), name='activo-tabla'),
]
