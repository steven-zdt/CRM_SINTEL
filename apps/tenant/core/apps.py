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
    
    def ready(self) -> None:
        """
        Se ejecuta cuando todas las apps estan listas.

        1. Registra modelos tenant en el admin site aislado.
        2. Conecta el receiver de limpieza de TenantProfile al signal
           global_user_hard_deleting (emitido por delete_user_service cuando
           se elimina un usuario global).
        """
        from .admin import ensure_tenant_apps_registered
        ensure_tenant_apps_registered()

        # Conectar receiver: limpieza de TenantProfile cross-schema
        from apps.public.accounts.signals import global_user_hard_deleting
        from apps.tenant.core.services.membership import _on_global_user_hard_deleting
        global_user_hard_deleting.connect(_on_global_user_hard_deleting, weak=False)
