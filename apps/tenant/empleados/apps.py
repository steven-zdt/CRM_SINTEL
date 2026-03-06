from django.apps import AppConfig


class EmpleadosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tenant.empleados'
    label = 'tenant_empleados'
    verbose_name = 'Empleados'
