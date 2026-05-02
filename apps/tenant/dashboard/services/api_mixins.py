"""
API Mixins para Dashboard - Inyección de servicios en ViewSets.

WARNING: SINTEL v3.5: Arquitectura Service Layer Modular.
"""
from apps.tenant.dashboard.services.selectors import DashboardSelector
from apps.tenant.dashboard.services.business_service import DashboardBusinessService
from apps.tenant.dashboard.services.crud_service import DashboardCRUDService


class DashboardServiceMixin:
    """
    Service mixin para Dashboard ViewSet.
    """

    selector_class = DashboardSelector
    business_service_class = DashboardBusinessService
    crud_service_class = DashboardCRUDService

    def service_get_user_role(self):
        """Obtiene rol del usuario actual."""
        user = self.request.user
        tenant = getattr(self.request, 'tenant', None)
        return self.business_service_class.get_user_role(user, tenant)

    def service_get_redirect_url(self):
        """Obtiene URL de redirección según rol."""
        role = self.service_get_user_role()
        return self.business_service_class.get_redirect_url_by_role(role)
