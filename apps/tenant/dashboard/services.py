"""
Servicios para el dashboard de tenants.

Lógica de negocio para determinar roles y obtener datos del dashboard.
"""
from django.db import connection
from django_tenants.utils import get_public_schema_name
from django.conf import settings
from apps.public.tenants.models import Domain


def get_user_role_in_tenant(user, tenant):
    """
    Obtiene el rol del usuario en el tenant actual.
    
    Si el usuario tiene múltiples membresías en el mismo tenant (no debería pasar por unique_together),
    retorna el rol más alto según prioridad: ADMIN > STAFF > USER.
    
    Args:
        user: Usuario autenticado
        tenant: Instancia del tenant (Client)
    
    Returns:
        str: Rol del usuario ('ADMIN', 'STAFF', 'USER') o None si no tiene membresía
    """
    if not user or not user.is_authenticated:
        return None
    
    if not tenant:
        return None
    
    # Asegurar que estamos en el esquema public para consultar TenantMembership
    current_schema = getattr(connection, 'schema_name', None)
    public_schema = get_public_schema_name()
    
    try:
        # Cambiar temporalmente al esquema public si es necesario
        if current_schema != public_schema:
            connection.set_schema_to_public()
        
        # Importar aquí para evitar problemas de importación circular
        from apps.public.tenants.models import TenantMembership
        
        # Buscar membresías activas del usuario en el tenant
        memberships = TenantMembership.objects.filter(
            client=tenant,
            user=user,
            is_active=True
        )
        
        if not memberships.exists():
            return None
        
        # Prioridad de roles: ADMIN > STAFF > USER
        role_priority = {'ADMIN': 3, 'STAFF': 2, 'USER': 1}
        
        # Obtener el rol más alto
        highest_role = None
        highest_priority = 0
        
        for membership in memberships:
            role = membership.rol
            priority = role_priority.get(role, 0)
            if priority > highest_priority:
                highest_priority = priority
                highest_role = role
        
        return highest_role
    
    finally:
        # Restaurar el esquema original si fue cambiado
        if current_schema and current_schema != public_schema:
            connection.set_schema(current_schema)


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
        # ⚠️ Fallback seguro: retornar ruta por defecto en lugar de None
        # Esto evita errores en el frontend cuando no se puede determinar el rol
        # (aunque no debería pasar después de validar membresía)
        relative_url = '/dashboard/'
        
        if not absolute:
            return relative_url
        
        # Intentar construir URL absoluta con fallback
        current_schema = getattr(connection, 'schema_name', None)
        public_schema = get_public_schema_name()
        
        try:
            if current_schema != public_schema:
                connection.set_schema_to_public()
            
            domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
            
            if domain:
                protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
                return f"{protocol}://{domain.domain}{relative_url}"
            else:
                # Último fallback: ruta relativa
                return relative_url
        finally:
            if current_schema and current_schema != public_schema:
                connection.set_schema(current_schema)
    
    # ⚠️ v2.30: Opción B - Rutas "bonitas" que apuntan a shells estáticos
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
    
    # Construir URL absoluta
    # Obtener dominio primario del tenant (en esquema public)
    current_schema = getattr(connection, 'schema_name', None)
    public_schema = get_public_schema_name()
    
    try:
        if current_schema != public_schema:
            connection.set_schema_to_public()
        
        domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
        
        if not domain:
            # ⚠️ Fallback seguro: retornar ruta relativa si no hay dominio primario
            # Nunca retornar None para evitar errores en el frontend
            return relative_url
        
        protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
        absolute_url = f"{protocol}://{domain.domain}{relative_url}"
        
        return absolute_url
    
    finally:
        if current_schema and current_schema != public_schema:
            connection.set_schema(current_schema)


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
