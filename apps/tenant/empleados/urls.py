"""
URLs de UI para la app empleados.

WARNING: v3.5: UI URLs para HTMX y templates.
- Las APIs están en api/urls.py (DRF)
- Estas URLs son para cargar offcanvas y partials HTML
"""
from django.urls import path

from apps.tenant.empleados.api.viewsets import EmpleadoViewSet

app_name = 'empleados'

# ViewSet instanciado para métodos de acción
empleado_viewset = EmpleadoViewSet()

urlpatterns = [
    # Offcanvas para crear/editar empleados
    path('gestor-offcanvas/', 
         EmpleadoViewSet.as_view({'get': 'gestor_offcanvas'}), 
         name='empleado-gestor-offcanvas'),
    # Lista de empleados (UI)
    path('', 
         EmpleadoViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='empleado-list'),
]
