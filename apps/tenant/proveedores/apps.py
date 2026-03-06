from django.apps import AppConfig


class ProveedoresConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tenant.proveedores"
    label = "tenant_proveedores"  # evita colisiones y define prefijo de tablas
    verbose_name = "Proveedores"
