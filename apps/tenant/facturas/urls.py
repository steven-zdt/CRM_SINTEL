"""
URLs de UI para la app facturas.

WARNING: v3.5: UI URLs para HTMX y templates.
"""
from django.urls import path

from apps.tenant.facturas.api.viewsets import FacturaViewSet
from apps.tenant.facturas.views import FacturaTableView

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
    # Tabla server-rendered (django-tables2 + HTMX) — Fase 5-BIS, reemplaza
    # la inicializacion de Tabulator en facturas_list.js. naturaleza: venta|compra.
    path('tabla/<str:naturaleza>/',
         FacturaTableView.as_view(),
         name='tabla'),
]
