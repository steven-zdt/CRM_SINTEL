"""
Permisos DRF para el dashboard de tenants.

⚠️ v2.30: API-First - Permisos basados en roles de TenantMembership.
"""
from rest_framework import permissions
from apps.tenant.dashboard.services import get_user_role_in_tenant


class HasTenantMembership(permissions.BasePermission):
    """
    Permiso base: verifica que el usuario tenga membresía activa en el tenant actual.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return False
        
        role = get_user_role_in_tenant(request.user, tenant)
        return role is not None


class IsAdminOrHigher(HasTenantMembership):
    """
    Permiso: requiere rol ADMIN o superior.
    """
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        tenant = getattr(request, 'tenant', None)
        role = get_user_role_in_tenant(request.user, tenant)
        
        # ADMIN tiene prioridad 3
        role_priority = {'ADMIN': 3, 'STAFF': 2, 'USER': 1}
        user_priority = role_priority.get(role, 0)
        
        return user_priority >= 3


class IsStaffOrHigher(HasTenantMembership):
    """
    Permiso: requiere rol STAFF o superior (ADMIN o STAFF).
    """
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        tenant = getattr(request, 'tenant', None)
        role = get_user_role_in_tenant(request.user, tenant)
        
        # STAFF tiene prioridad 2, ADMIN tiene 3
        role_priority = {'ADMIN': 3, 'STAFF': 2, 'USER': 1}
        user_priority = role_priority.get(role, 0)
        
        return user_priority >= 2


class IsUserOrHigher(HasTenantMembership):
    """
    Permiso: requiere rol USER o superior (todos los usuarios con membresía).
    """
    def has_permission(self, request, view):
        # Si tiene membresía (verificado por HasTenantMembership), tiene acceso
        return super().has_permission(request, view)
