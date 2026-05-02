"""
Selectores para Landing v3.5 - Zero Waste Queries.
"""
from apps.tenant.empresa.models import Empresa


class LandingSelector:
    """Selector para información pública de landing."""

    @staticmethod
    def get_empresa_public_info(empresa_id):
        """Retorna información pública de la empresa para landing."""
        return Empresa.objects.filter(id=empresa_id).only(
            'razon_social',
            'nombre_comercial',
            'nit',
            'direccion',
            'telefono',
            'email_contacto',
            'website',
            'logo'
        ).first()

    @staticmethod
    def get_tenant_info(tenant):
        """Retorna información básica del tenant."""
        if not tenant:
            return None
        return {
            'id': tenant.id,
            'schema_name': tenant.schema_name,
            'nombre': getattr(tenant, 'name', None),
        }
