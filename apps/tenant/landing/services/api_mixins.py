"""
API Mixins para Landing - Inyección de servicios en ViewSets.

WARNING: SINTEL v3.5: Arquitectura Service Layer Modular.
"""
from apps.tenant.landing.services.selectors import LandingSelector
from apps.tenant.landing.services.business_service import LandingBusinessService
from apps.tenant.landing.services.crud_service import LandingCRUDService


class LandingServiceMixin:
    """
    Service mixin para Landing ViewSet.
    """

    selector_class = LandingSelector
    business_service_class = LandingBusinessService
    crud_service_class = LandingCRUDService

    def service_get_public_info(self):
        """Obtiene información pública del tenant."""
        return self.business_service_class.get_public_info(self.request)

    def service_get_empresa_branding(self):
        """Obtiene branding de la empresa."""
        empresa_id = getattr(self.request.user, 'empresa_id', None)
        if not empresa_id:
            from apps.tenant.empresa.models import Empresa
            empresa = Empresa.objects.first()
            empresa_id = empresa.id if empresa else None
        return self.business_service_class.get_empresa_branding(empresa_id)
