from django.apps import AppConfig


class CotizacionesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tenant.cotizaciones'
    label = 'tenant_cotizaciones'  # # WARNING: v2.40: Evita colisiones de labels
    verbose_name = 'Cotizaciones'
