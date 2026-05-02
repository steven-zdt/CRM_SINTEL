"""
Business Service para Landing v3.5 - Lógica de negocio.
"""
import logging
from django.http import HttpRequest
from apps.tenant.landing.services.selectors import LandingSelector

logger = logging.getLogger(__name__)


class LandingBusinessService:
    """Orquestación de lógica de negocio del landing."""

    @staticmethod
    def get_public_info(request: HttpRequest):
        """Obtiene información pública del tenant."""
        tenant = getattr(request, 'tenant', None)
        
        if not tenant:
            raise ValueError("No se pudo determinar el tenant actual.")
        
        tenant_info = LandingSelector.get_tenant_info(tenant)
        
        return {
            'tenant': tenant,
            'tenant_info': tenant_info,
            'request': request,
        }

    @staticmethod
    def get_empresa_branding(empresa_id):
        """Obtiene branding de la empresa."""
        empresa = LandingSelector.get_empresa_public_info(empresa_id)
        if not empresa:
            return None
        
        return {
            'razon_social': empresa.razon_social,
            'nombre_comercial': empresa.nombre_comercial,
            'nit': empresa.nit,
            'direccion': empresa.direccion,
            'telefono': empresa.telefono,
            'email': empresa.email_contacto,
            'website': empresa.website,
            'logo': empresa.logo.url if empresa.logo else None,
        }
