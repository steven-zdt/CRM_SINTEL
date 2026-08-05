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
from apps.tenant.contabilidad.views import (
    AsientoContableTableView,
    CuentaContableTableView,
    PeriodoContableTableView,
    PlantillaContableTableView,
    RetencionTableView,
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
    path('cuentas/tabla/', CuentaContableTableView.as_view(), name='cuenta-tabla'),

    # Asientos contables
    path('asientos/',
         AsientoContableViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='asiento-list'),
    path('asientos/gestor-offcanvas/',
         AsientoContableViewSet.as_view({'get': 'gestor_offcanvas'}),
         name='asiento-gestor-offcanvas'),
    path('asientos/tabla/', AsientoContableTableView.as_view(), name='asiento-tabla'),

    # Periodos contables
    path('periodos/',
         PeriodoContableViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='periodo-list'),
    path('periodos/gestor-offcanvas/',
         PeriodoContableViewSet.as_view({'get': 'gestor_offcanvas'}),
         name='periodo-gestor-offcanvas'),
    path('periodos/tabla/', PeriodoContableTableView.as_view(), name='periodo-tabla'),

    # Retenciones (solo lectura)
    path('retenciones/tabla/', RetencionTableView.as_view(), name='retencion-tabla'),

    # Plantillas contables
    path('plantillas/tabla/', PlantillaContableTableView.as_view(), name='plantilla-tabla'),

    # Reportes
    path('reportes/',
         AsientoContableViewSet.as_view({'get': 'reporte_page'}),
         name='reporte-page'),
]
