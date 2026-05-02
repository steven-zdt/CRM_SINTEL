"""
AppConfig para la aplicación console.
"""

from django.apps import AppConfig


class ConsoleConfig(AppConfig):
    """Configuración de la app console."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.public.console"
    verbose_name = "Console (Administración Pública)"
