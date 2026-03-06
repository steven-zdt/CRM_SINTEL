from django.apps import AppConfig


class ClientesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tenant.clientes"
    label = "tenant_clientes"  # prefijo de tablas + evita colisiones de labels
    verbose_name = "Clientes"
