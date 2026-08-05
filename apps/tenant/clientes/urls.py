"""
URLs de UI para la app clientes.
"""
from django.urls import path

from apps.tenant.clientes.api.viewsets import ClienteViewSet
from apps.tenant.clientes.views import ClienteTableView

app_name = 'clientes'

urlpatterns = [
    # Lista de clientes (UI)
    path('',
         ClienteViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='cliente-list'),
    # Tabla server-rendered (django-tables2 + HTMX) — Fase 5-BIS, reemplaza
    # la grilla "clientes" de clientes.list.js
    path('tabla/', ClienteTableView.as_view(), name='cliente-tabla'),
    path('gestor-offcanvas/',
         ClienteViewSet.as_view({'get': 'gestor_offcanvas'}),
         name='cliente-gestor-offcanvas'),
]
