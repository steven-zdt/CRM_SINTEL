from django.apps import AppConfig


class RequisicionesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tenant.compras.requisiciones"
    label = "tenant_compras_requisiciones"  # evita colisiones de labels
    verbose_name = "Requisiciones de Compra"
