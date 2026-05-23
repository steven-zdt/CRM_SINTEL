"""
Permisos centrales para APIs de tenants.

[RULE 13 / RULE 15] SSoT de permisos basados en TenantProfile.rol.
Todas las apps tenant DEBEN importar permisos desde este modulo.

Jerarquia de roles (TenantProfile.rol):
  ADMIN    -> acceso total: CRUD + asignar roles + configuraciones
  OPERADOR -> lectura + escritura limitada (segun app)
  VISOR    -> solo lectura

WARNING: SEGURIDAD: Cross-Tenant Isolation
- IsTenantMember valida TenantMembership antes de cualquier operacion.
- HasTenantRole aplica DSV (Double Semantic Verification) sobre TenantProfile.
"""
import logging

from rest_framework import permissions

log = logging.getLogger("tenant.permissions")


# ---------------------------------------------------------------------------
# Helpers internos (DSV)
# ---------------------------------------------------------------------------

def _resolve_empresa():
    """Resuelve la Empresa del tenant activo. Retorna None si falla."""
    try:
        from apps.tenant.empresa.models import Empresa
        # Buscar prioritariamente la SSoT con singleton_key=1
        empresa = Empresa.objects.filter(singleton_key=1).only('id').first()
        if not empresa:
            empresa = Empresa.objects.only('id').order_by('id').first()
        return empresa
    except Exception:
        return None


def _get_perfil(user):
    """Retorna tenant_profile del user si existe, None en caso contrario."""
    return getattr(user, 'tenant_profile', None)


# ---------------------------------------------------------------------------
# Clase base: membresia cross-schema
# ---------------------------------------------------------------------------

class IsTenantMember(permissions.BasePermission):
    """
    Permiso personalizado que verifica que el usuario tenga membresia activa
    en el tenant actual (request.tenant).

    WARNING: CRITICO: Este permiso debe aplicarse a todas las APIs de tenant
    para garantizar el aislamiento cross-tenant.
    """

    def has_permission(self, request, view):
        # Fallback para desarrollo (v2.62.1)
        from django.conf import settings
        if settings.DEBUG:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return True

        from apps.tenant.core.services.membership import check_membership_exists
        return check_membership_exists(request.user, tenant)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


# ---------------------------------------------------------------------------
# Clases basadas en TenantProfile.rol (SSoT v2.61.8)
# ---------------------------------------------------------------------------

class HasTenantRole(permissions.BasePermission):
    """[RULE 13/15] Verifica que el usuario tenga un rol permitido en el tenant.

    Uso en ViewSet:
        required_roles = ['ADMIN', 'OPERADOR']
        permission_classes = [IsTenantMember, HasTenantRole]

    DSV aplicado:
        1. El tenant_profile debe existir en el usuario autenticado.
        2. El perfil.empresa_id debe coincidir con la Empresa del esquema activo.
        3. El perfil.rol debe estar en view.required_roles.
    """

    def has_permission(self, request, view) -> bool:
        # Fallback para desarrollo (v2.62.1)
        from django.conf import settings
        if settings.DEBUG:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        perfil = _get_perfil(request.user)
        if not perfil:
            return False

        empresa = _resolve_empresa()
        if not empresa or perfil.empresa_id != empresa.id:
            return False

        required_roles = getattr(view, 'required_roles', [])
        if not required_roles:
            return True

        return perfil.rol in required_roles


class IsTenantProfileAdmin(permissions.BasePermission):
    """[RULE 15] Requiere rol ADMIN en el tenant activo.

    Aplica DSV completo (perfil existe y empresa coincide con tenant).
    """

    def has_permission(self, request, view) -> bool:
        # Fallback para desarrollo (v2.62.1)
        from django.conf import settings
        if settings.DEBUG:
            return True

        if not request.user or not request.user.is_authenticated:
            return False
        perfil = _get_perfil(request.user)
        if not perfil:
            return False
        empresa = _resolve_empresa()
        if not empresa or perfil.empresa_id != empresa.id:
            return False
        return perfil.rol == 'ADMIN'


class IsTenantProfileOperadorOrAdmin(permissions.BasePermission):
    """[RULE 15] Requiere rol ADMIN o OPERADOR en el tenant activo.

    Aplica DSV completo (perfil existe y empresa coincide con tenant).
    """

    def has_permission(self, request, view) -> bool:
        # Fallback para desarrollo (v2.62.1)
        from django.conf import settings
        if settings.DEBUG:
            return True

        if not request.user or not request.user.is_authenticated:
            return False
        perfil = _get_perfil(request.user)
        if not perfil:
            return False
        empresa = _resolve_empresa()
        if not empresa or perfil.empresa_id != empresa.id:
            return False
        return perfil.rol in ('ADMIN', 'OPERADOR')


class IsTenantAdmin(IsTenantProfileAdmin):
    """[RULE 15] Alias semantico de IsTenantProfileAdmin.

    Nombre canonico para guards de endpoints que requieren el rol ADMIN
    del tenant activo. Equivalente a IsTenantProfileAdmin pero con nombre
    mas expresivo para uso en viewsets fuera de la app perfil.
    """


# ---------------------------------------------------------------------------
# Permiso compuesto: Admin-or-ReadOnly
# ---------------------------------------------------------------------------

class IsTenantAdminOrReadOnly(permissions.BasePermission):
    """
    Lectura permitida a todo usuario autenticado; escritura solo a ADMIN.

    Usa TenantProfile.rol (SSoT v2.61.8) en lugar de TenantMembership.rol.

    WARNING: Para ViewSets con ENFORCED MODE (_check_enforced_mode), este
    permiso permite todas las operaciones y la verificacion real se hace
    dentro del metodo del ViewSet (retorna 405 con mensaje claro).
    """
    message = "Solo usuarios ADMIN del tenant pueden crear/editar/eliminar."

    def has_permission(self, request, view):
        # Fallback para desarrollo (v2.62.1) — permitir TODO en DEBUG
        from django.conf import settings
        if settings.DEBUG:
            return True

        from rest_framework.permissions import SAFE_METHODS

        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return False

        if request.method in SAFE_METHODS:
            return True

        # ViewSets con enforced mode manejan la verificacion internamente
        if hasattr(view, '_check_enforced_mode'):
            return True

        # En producción, verificar si es ADMIN
        return IsTenantAdmin().has_permission(request, view)
