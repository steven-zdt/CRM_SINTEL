from django.urls import path
from .api.viewsets import OrdenCompraViewSet
from .views import OrdenCompraTableView

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
]
