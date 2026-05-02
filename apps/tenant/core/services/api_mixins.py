"""
API Mixins para Core - Inyección de servicios en ViewSets.

WARNING: SINTEL v3.5: Arquitectura Service Layer Modular.
Core es un UI Shell que orquesta otras apps.
"""
from apps.tenant.core.services.selectors import CoreSelector


class CoreServiceMixin:
    """
    Service mixin para Core ViewSets.
    Proporciona acceso a datos de configuración del tenant.
    """

    selector_class = CoreSelector

    def get_qs_empresa_metadata(self):
        """Retorna metadata de la empresa."""
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_empresa_metadata(empresa_id)

    def get_tenant_info(self):
        """Retorna información del tenant."""
        return self.selector_class.get_tenant_info(self.request)
