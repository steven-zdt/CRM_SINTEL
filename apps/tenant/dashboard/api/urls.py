"""
URLs de API REST para el dashboard de tenants.

WARNING: v2.30: API-First - Todos los endpoints retornan JSON.
"""
from django.urls import path

from . import views

app_name = 'tenant_dashboard_api'

urlpatterns = [
    # Endpoint principal (contrato estandarizado)
    path('data/', views.DashboardDataAPIView.as_view(), name='dashboard-data'),
    
    # Endpoints legacy (mantener por compatibilidad)
    path('summary/', views.DashboardSummaryAPIView.as_view(), name='dashboard-summary'),
    path('kpis/', views.DashboardKPIsAPIView.as_view(), name='dashboard-kpis'),
    path('quick-actions/', views.DashboardQuickActionsAPIView.as_view(), name='dashboard-quick-actions'),
]
