from django.apps import AppConfig


class ContabilidadConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tenant.contabilidad'
    verbose_name = 'Contabilidad'

    def ready(self) -> None:
        from apps.tenant.contabilidad.reporting import register
        register()
