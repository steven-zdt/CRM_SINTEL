"""
Selectores para Core v3.5 - Zero Waste Queries.

WARNING: Core es un UI Shell que orquesta otras apps.
Estos selectors son para datos de configuración y metadata del core.
"""
from apps.tenant.empresa.models import Empresa


class CoreSelector:
    """Selector para datos de configuración del core."""

    @staticmethod
    def get_empresa_metadata(empresa_id):
        """Retorna metadata de la empresa para el core."""
        return Empresa.objects.filter(id=empresa_id).only(
            'id', 'razon_social', 'nit', 'dv', 'logo', 'regimen_tributario'
        ).first()

    @staticmethod
    def get_tenant_info(request):
        """Retorna información del tenant desde el request."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return None
        return {
            'id': tenant.id,
            'schema_name': tenant.schema_name,
            'name': getattr(tenant, 'name', None),
        }
