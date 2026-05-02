"""
URLs de UI para la app clientes.

WARNING: v3.5: UI URLs para HTMX y templates.
"""
from django.urls import path

from apps.tenant.clientes.api.viewsets import ClienteViewSet

app_name = 'clientes'

urlpatterns = [
    # Lista de clientes (UI)
    path('', 
         ClienteViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='cliente-list'),
    path('gestor-offcanvas/', 
         ClienteViewSet.as_view({'get': 'gestor_offcanvas'}), 
         name='cliente-gestor-offcanvas'),
]
