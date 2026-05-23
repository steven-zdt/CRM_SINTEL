"""
URLs de API REST para el dashboard de tenants v3.9.4.
API-First: Todos los endpoints retornan JSON.
Usa Router para ViewSets + rutas legacy para compatibilidad.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views, viewsets

router = DefaultRouter()
router.register(r'', viewsets.DashboardViewSet, basename='dashboard')

app_name = 'tenant_dashboard_api'

urlpatterns = [
    # ViewSet principal (metricas consolidadas)
    path('', include(router.urls)),

    # Endpoints legacy APIView (mantener por compatibilidad)
    path('data/', views.DashboardDataAPIView.as_view(), name='dashboard-data'),
    path('summary/', views.DashboardSummaryAPIView.as_view(), name='dashboard-summary'),
    path('kpis/', views.DashboardKPIsAPIView.as_view(), name='dashboard-kpis'),
    path('quick-actions/', views.DashboardQuickActionsAPIView.as_view(), name='dashboard-quick-actions'),
]
