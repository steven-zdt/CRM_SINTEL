from django.apps import AppConfig


class TenantsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.public.tenants"
    verbose_name = "Tenants"

    def ready(self):
        """
        Inicialización ligera de la app tenants.

        WARNING: CERO SIGNALS:
        - No se registran señales que creen dominios ni que escriban en BD.
        - Toda la lógica de onboarding vive en servicios explícitos.

        Este método NO debe ejecutar escrituras en BD ni agendar tareas.
        """
        # Importes solo para side-effects de tipo validación / logging si fuese necesario.
        # Actualmente no hacemos nada aquí para evitar side-effects en arranque/autoreloader.
        return
