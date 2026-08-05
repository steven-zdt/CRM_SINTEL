"""
URLs de UI para la app gastos.

WARNING: v3.5: UI URLs para HTMX y templates.
- Las APIs estan en api/urls.py (DRF)
- Estas URLs son para cargar offcanvas y partials HTML
"""
from django.urls import path

from apps.tenant.gastos.api.viewsets import GastoViewSet
from apps.tenant.gastos.views import DocumentoSoporteTableView, ResolucionDIANTableView

app_name = 'gastos'

urlpatterns = [
    # Offcanvas para crear/editar gastos
    path('gestor-offcanvas/',
         GastoViewSet.as_view({'get': 'gestor_offcanvas'}),
         name='gasto-gestor-offcanvas'),
    # Lista de gastos (UI)
    path('',
         GastoViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='gasto-list'),
    # Tablas server-rendered (django-tables2 + HTMX) — piloto Fase 5-BIS,
    # reemplazan la inicializacion de Tabulator en gasto_list.js
    path('tabla-documentos/',
         DocumentoSoporteTableView.as_view(),
         name='documentos-tabla'),
    path('tabla-resoluciones/',
         ResolucionDIANTableView.as_view(),
         name='resoluciones-tabla'),
]
