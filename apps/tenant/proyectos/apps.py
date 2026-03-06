from django.apps import AppConfig


class ProyectosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tenant.proyectos"
    label = "tenant_proyectos"  # prefijo de tablas + evita colisiones de labels
    verbose_name = "Proyectos"
