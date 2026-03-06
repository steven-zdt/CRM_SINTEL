"""
Configuración de la app dashboard.
"""
from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tenant.dashboard'
    verbose_name = 'Dashboard de Tenant'
