"""
URLs de UI para la app proyectos.

WARNING: v3.5: UI URLs para HTMX y templates.
"""
from django.urls import path

from apps.tenant.proyectos.api.viewsets import ProyectoViewSet

app_name = 'proyectos'

urlpatterns = [
    # Lista de proyectos (UI)
    path('', 
         ProyectoViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='proyecto-list'),
    # Detalle de proyecto (UI) - Para editar/obtener un proyecto especifico
    path('<int:pk>/', 
         ProyectoViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), 
         name='proyecto-detail'),
    path('gestor-offcanvas/', 
         ProyectoViewSet.as_view({'get': 'gestor_offcanvas'}), 
         name='proyecto-gestor-offcanvas'),
]
