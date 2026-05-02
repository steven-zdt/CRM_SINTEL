"""
Business Service para Dashboard v3.5 - Lógica de negocio.
"""
from apps.tenant.dashboard.services.selectors import DashboardSelector


class DashboardBusinessService:
    """Orquestación de lógica de negocio del dashboard."""

    @staticmethod
    def get_user_role(user, tenant):
        """Obtiene rol del usuario."""
        return DashboardSelector.get_user_role(user, tenant)

    @staticmethod
    def get_redirect_url_by_role(role):
        """Retorna URL de redirección según rol."""
        urls = {
            'ADMIN': '/dashboard/admin/',
            'STAFF': '/dashboard/staff/',
            'USER': '/dashboard/',
        }
        return urls.get(role, '/dashboard/')
