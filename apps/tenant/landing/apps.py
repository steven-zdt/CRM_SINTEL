"""
Configuración de la app landing.
"""
from django.apps import AppConfig


class LandingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tenant.landing'
    verbose_name = 'Landing Page de Tenant'
