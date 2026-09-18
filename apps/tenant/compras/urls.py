from django.urls import path
from .api.viewsets import OrdenCompraViewSet
from .views import OrdenCompraTableView, PlantillaOrdenCompraTableView

app_name = 'compras'

urlpatterns = [
    # UI actions mapped to viewset actions
    path('',
         OrdenCompraViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='orden-compra-list'),
    # Tabla server-rendered (django-tables2 + HTMX) — Fase 5-BIS, reemplaza
    # la inicializacion de Tabulator en compras_list.js
    path('tabla/',
         OrdenCompraTableView.as_view(),
         name='tabla'),
    # CO-1 (2026-09-12): pantalla de gestion de plantillas de numeracion.
    path('plantillas/tabla/',
         PlantillaOrdenCompraTableView.as_view(),
         name='plantillas-tabla'),
]
