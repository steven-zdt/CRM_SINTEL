from django.apps import AppConfig


class ComprasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tenant.compras"
    label = "tenant_compras"  # evita colisiones de labels
    verbose_name = "Compras"
