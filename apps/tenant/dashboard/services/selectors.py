"""
Selectores para Dashboard v3.5 - Zero Waste Queries.
"""
from django.db.models import Count, Q
from apps.tenant.empresa.models import Empresa


class DashboardSelector:
    """Selector para datos del dashboard."""

    @staticmethod
    def get_user_role(user, tenant):
        """Obtiene el rol del usuario en el tenant actual.

        Delega a Core Membership Bridge (REGLA 2).
        """
        from apps.tenant.core.services.membership import get_user_role
        return get_user_role(user, tenant)

    @staticmethod
    def get_empresa_summary(empresa_id):
        """Obtiene resumen de la empresa."""
        return Empresa.objects.filter(id=empresa_id).only(
            'id', 'razon_social', 'nit', 'dv', 'regimen_tributario'
        ).first()
