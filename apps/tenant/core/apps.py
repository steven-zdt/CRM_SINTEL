"""
Configuración de la app core para tenants.
"""
from django.apps import AppConfig


class TenantCoreConfig(AppConfig):
    """
    Configuración de la app core para tenants.
    
    Esta app contiene:
    - Vistas core (manejadores de error 404, 403)
    - Templates de error personalizados
    - Admin Site aislado para tenants (tenant_admin_site)
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tenant.core'
    label = 'tenant_core'  # # WARNING: CRÍTICO: Label único para evitar conflicto con apps.public.core
    verbose_name = 'Tenant Core'
    
    def ready(self):
        """
        Se ejecuta cuando todas las apps están listas.
        
        Aquí registramos los modelos de tenant en el admin site aislado.
        Esto garantiza que todos los admin.py de las apps de tenant
        ya hayan registrado sus modelos en admin.site.
        """
        # Importar aquí para evitar problemas de importación circular
        from .admin import ensure_tenant_apps_registered
        ensure_tenant_apps_registered()
