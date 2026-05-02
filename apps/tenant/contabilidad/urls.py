"""
URLs de UI para la app contabilidad.

WARNING: v3.5: UI URLs para HTMX y templates.
"""
from django.urls import path

from apps.tenant.contabilidad.api.viewsets import (
    AsientoContableViewSet,
    CuentaContableViewSet,
    PeriodoContableViewSet,
)

app_name = 'contabilidad'

urlpatterns = [
    # Cuentas contables
    path('cuentas/', 
         CuentaContableViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='cuenta-list'),
    path('cuentas/gestor-offcanvas/', 
         CuentaContableViewSet.as_view({'get': 'gestor_offcanvas'}), 
         name='cuenta-gestor-offcanvas'),
    
    # Asientos contables
    path('asientos/', 
         AsientoContableViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='asiento-list'),
    path('asientos/gestor-offcanvas/', 
         AsientoContableViewSet.as_view({'get': 'gestor_offcanvas'}), 
         name='asiento-gestor-offcanvas'),
    
    # Periodos contables
    path('periodos/', 
         PeriodoContableViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='periodo-list'),
    path('periodos/gestor-offcanvas/', 
         PeriodoContableViewSet.as_view({'get': 'gestor_offcanvas'}), 
         name='periodo-gestor-offcanvas'),
]
