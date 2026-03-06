from django.apps import AppConfig


class GastosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tenant.gastos"
    label = "tenant_gastos"  # evita colisiones de labels
    verbose_name = "Gastos"
