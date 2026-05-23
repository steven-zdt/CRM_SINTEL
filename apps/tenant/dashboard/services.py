"""
Servicios para el dashboard de tenants v3.9.4.
Legacy facade que delega a Core Membership Bridge y BusinessService.
"""
from django.conf import settings

from apps.tenant.core.services.membership import (
    get_primary_domain,
    get_user_role,
)
from apps.tenant.dashboard.services.business_service import DashboardBusinessService


def get_user_role_in_tenant(user, tenant):
    """
    Obtiene el rol del usuario en el tenant actual.
    Delega a Core Membership Bridge (REGLA 2 de AGENTS.md).

    Returns:
        str: Rol del usuario ('ADMIN', 'STAFF', 'USER') o None si no tiene membresía
    """
    return get_user_role(user, tenant)


def get_dashboard_redirect_url(user, tenant, absolute=False):
    """
    Obtiene la URL de redirección al dashboard según el rol del usuario.

    Mapeo de roles a rutas:
    - ADMIN → /dashboard/admin/
    - STAFF → /dashboard/staff/
    - USER → /dashboard/

    Args:
        user: Usuario autenticado
        tenant: Instancia del tenant (Client)
        absolute: Si True, retorna URL absoluta (con protocolo y dominio)

    Returns:
        str: URL relativa o absoluta del dashboard según el rol
    """
    role = get_user_role_in_tenant(user, tenant)

    if not role:
        relative_url = '/dashboard/'

        if not absolute:
            return relative_url

        domain = get_primary_domain(tenant)
        if domain:
            protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
            return f"{protocol}://{domain}{relative_url}"
        else:
            return relative_url

    role_routes = {
        'ADMIN': '/dashboard/admin/',
        'STAFF': '/dashboard/staff/',
        'USER': '/dashboard/user/',
    }

    relative_url = role_routes.get(role, '/dashboard/')

    if not absolute:
        return relative_url

    domain = get_primary_domain(tenant)
    if not domain:
        return relative_url

    protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
    absolute_url = f"{protocol}://{domain}{relative_url}"

    return absolute_url


def get_dashboard_context(user, tenant):
    """
    Obtiene el contexto de datos para el dashboard v3.9.4.
    Ahora retorna datos reales via BusinessService + Pull Model.

    Args:
        user: Usuario autenticado
        tenant: Instancia del tenant (Client)

    Returns:
        dict: Contexto con métricas consolidadas (v3.9.4 Pull Model)
    """
    try:
        # Obtener empresa_id desde el tenant
        empresa_id = tenant.id if hasattr(tenant, 'id') else None

        if not empresa_id:
            return {'error': 'No se pudo determinar la empresa'}

        # Delegar a BusinessService (orquestación de extractores)
        metricas = DashboardBusinessService.obtener_metricas_consolidadas(empresa_id)

        # Convertir DTO a dict para compatibilidad con serializers legacy
        return {
            'empresa_nombre': metricas.empresa_nombre,
            'empresa_nit': metricas.empresa_nit,
            'fecha_actualizacion': metricas.fecha_actualizacion,
            'total_facturas': metricas.facturas.total_facturas,
            'facturas_pendientes': metricas.facturas.facturas_pendientes,
            'ingresos_mes': float(metricas.facturas.ingresos_mes),
            'total_empleados': metricas.empleados.total_empleados,
            'empleados_activos': metricas.empleados.empleados_activos,
            'total_inventario': metricas.inventario.total_productos,
        }

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error en get_dashboard_context: {str(e)}")

        # Retornar estructura segura
        return {
            'error': 'Error al cargar métricas',
            'total_facturas': 0,
            'facturas_pendientes': 0,
            'ingresos_mes': 0,
        }
