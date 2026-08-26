from django.apps import AppConfig


class VentasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tenant.ventas"
    label = "tenant_ventas"
    verbose_name = "Ventas"

    def ready(self) -> None:
        from apps.tenant.ventas.reporting import register
        register()
