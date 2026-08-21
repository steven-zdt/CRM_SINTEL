"""
URLs de UI para la app empleados.

WARNING: v3.5: UI URLs para HTMX y templates.
- Las APIs están en api/urls.py (DRF)
- Estas URLs son para cargar offcanvas y partials HTML
"""
from django.urls import path

from apps.tenant.empleados.api.viewsets import EmpleadoViewSet
from apps.tenant.empleados.views import (
    ContratoTableView,
    EmpleadoTableView,
    LiquidacionDetailTableView,
    LiquidacionMasterTableView,
    NominaDetailTableView,
    NominaMasterTableView,
    PeriodoNominaTableView,
    ResolucionDIANTableView,
)

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
    # Tablas server-rendered (django-tables2 + HTMX) — Fase 5-BIS, reemplazan
    # la inicializacion de Tabulator en empleado_list.js / contrato_list.js /
    # resolucion_list.js
    path('tabla/', EmpleadoTableView.as_view(), name='empleado-tabla'),
    path('contratos/tabla/', ContratoTableView.as_view(), name='contrato-tabla'),
    path('resoluciones/tabla/', ResolucionDIANTableView.as_view(), name='resolucion-tabla'),
    path('periodos/tabla/', PeriodoNominaTableView.as_view(), name='periodo-tabla'),
    # Master-Detail: Nominas y Liquidaciones
    path('nominas/master/tabla/', NominaMasterTableView.as_view(), name='nomina-master-tabla'),
    path('nominas/detalle/tabla/', NominaDetailTableView.as_view(), name='nomina-detalle-tabla'),
    path('liquidaciones/master/tabla/', LiquidacionMasterTableView.as_view(), name='liquidacion-master-tabla'),
    path('liquidaciones/detalle/tabla/', LiquidacionDetailTableView.as_view(), name='liquidacion-detalle-tabla'),
]
