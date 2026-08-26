from django.apps import AppConfig


class InventarioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tenant.inventario"
    label = "tenant_inventario"  # evitar colisiones con apps públicas
    verbose_name = "Inventario (Tenant)"

    def ready(self) -> None:
        from apps.tenant.inventario.reporting import register
        register()
