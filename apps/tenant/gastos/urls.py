"""
URLs de UI para la app gastos.

WARNING: v3.5: UI URLs para HTMX y templates.
- Las APIs estan en api/urls.py (DRF)
- Estas URLs son para cargar offcanvas y partials HTML
"""
from django.urls import path

from apps.tenant.gastos.api.viewsets import GastoViewSet

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
]
