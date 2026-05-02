"""
Servicios para el dashboard de tenants.

Logica de negocio para determinar roles y obtener datos del dashboard.
"""
from django.conf import settings

from apps.tenant.core.services.membership import (
    get_primary_domain,
    get_user_role,
)


def get_user_role_in_tenant(user, tenant):
    """
    Obtiene el rol del usuario en el tenant actual.

    Delega a Core Membership Bridge (REGLA 2).

    Returns:
        str: Rol del usuario ('ADMIN', 'STAFF', 'USER') o None si no tiene membresia
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
        str: URL relativa o absoluta del dashboard según el rol, o None si no tiene membresía
    """
    role = get_user_role_in_tenant(user, tenant)
    
    if not role:
        # WARNING: Fallback seguro: retornar ruta por defecto en lugar de None
        # Esto evita errores en el frontend cuando no se puede determinar el rol
        # (aunque no debería pasar después de validar membresía)
        relative_url = '/dashboard/'
        
        if not absolute:
            return relative_url
        
        domain = get_primary_domain(tenant)
        if domain:
            protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
            return f"{protocol}://{domain}{relative_url}"
        else:
            return relative_url
    
    # WARNING: v2.30: Opcion B - Rutas "bonitas" que apuntan a shells estaticos
    # Cada ruta redirige a un shell estático que consume la API
    # Mapeo de roles a rutas (estas rutas deben existir como shells estáticos o redirects)
    role_routes = {
        'ADMIN': '/dashboard/admin/',
        'STAFF': '/dashboard/staff/',
        'USER': '/dashboard/user/',
    }
    
    relative_url = role_routes.get(role, '/dashboard/')
    
    if not absolute:
        return relative_url
    
    # Construir URL absoluta via Core Membership Bridge (REGLA 2)
    domain = get_primary_domain(tenant)

    if not domain:
        return relative_url

    protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
    absolute_url = f"{protocol}://{domain}{relative_url}"

    return absolute_url


def get_dashboard_context(user, tenant):
    """
    Obtiene el contexto de datos para el dashboard.
    
    Args:
        user: Usuario autenticado
        tenant: Instancia del tenant (Client)
    
    Returns:
        dict: Contexto con datos simulados para el dashboard
    """
    # Por ahora, retornamos datos simulados
    # En el futuro, aquí se consultarían datos reales del tenant
    context = {
        'total_facturas': 0,
        'facturas_pendientes': 0,
        'total_clientes': 0,
        'ingresos_mes': 0,
    }
    
    # TODO: Implementar consultas reales a los modelos del tenant
    # Ejemplo:
    # from apps.tenant.facturas.models import Factura
    # context['total_facturas'] = Factura.objects.count()
    
    return context
