"""
Permisos DRF para la app perfil.

[RULE 13 / RULE 15] Las clases de permiso base (HasTenantRole,
IsTenantProfileAdmin, IsTenantProfileOperadorOrAdmin, IsTenantAdmin)
se reexportan desde la SSoT central: apps.tenant.api.permissions.

Este modulo conserva las funciones auxiliares propias de la app perfil:
ROLE_ACTIONS, get_available_actions, get_permissions_context.
"""

# SSoT central - reexport para backwards-compatibility
from apps.tenant.api.permissions import (  # noqa: F401
    HasTenantRole,
    IsTenantAdmin,
    IsTenantProfileAdmin,
    IsTenantProfileOperadorOrAdmin,
    _get_perfil,
    _resolve_empresa,
)
from apps.tenant.core.services.membership import check_primary_admin

# Acciones disponibles por rol (SSoT para serializers y guards de UI)
ROLE_ACTIONS: dict[str, list[str]] = {
    'ADMIN':    ['view', 'edit', 'delete', 'create_profile', 'assign_rol'],
    'OPERADOR': ['view', 'edit'],
    'VISOR':    ['view'],
}


def get_available_actions(perfil) -> list[str]:
    """Retorna la lista de acciones permitidas para el perfil dado.

    Usado por TenantProfileSerializer.get_available_actions para exponer
    acciones dinamicas a la UI (Universal UI Connect / Tabulator).
    """
    if not perfil:
        return []
    return ROLE_ACTIONS.get(perfil.rol, [])


def get_permissions_context(perfil, user=None) -> dict:
    """[RULE 15 / AUTO-ADMIN] Construye el contexto de permisos para la UI.

    Devuelve un dict legible por el frontend (Tabulator, botones de accion)
    que describe que puede hacer el usuario solicitante en este tenant.

    El flag 'is_owner' verifica TenantMembership.is_primary_admin en el
    esquema public usando connection.schema_name (DSV: aislamiento total).

    Args:
        perfil: TenantProfile del usuario autenticado (solicitante).
        user: User global (auth model), requerido para calcular is_owner.

    Returns:
        dict con claves bool para consumo directo en JS:
        {
            'can_edit_users': bool,
            'can_delete_users': bool,
            'can_assign_roles': bool,
            'can_create_profiles': bool,
            'is_owner': bool,
            'rol': str,
        }
    """
    if not perfil:
        return {}

    is_admin = perfil.rol == 'ADMIN'
    is_owner = False

    if is_admin and user is not None:
        try:
            is_owner = check_primary_admin(user.pk)
        except Exception:
            is_owner = False

    return {
        'can_edit_users': is_admin,
        'can_delete_users': is_admin,
        'can_assign_roles': is_admin,
        'can_create_profiles': is_admin,
        'is_owner': is_owner,
        'rol': perfil.rol,
        'user_id': perfil.user_id,
    }


# Las clases HasTenantRole, IsTenantProfileAdmin, IsTenantProfileOperadorOrAdmin
# e IsTenantAdmin se importan desde apps.tenant.api.permissions (SSoT v2.61.8)
# y se reexportan al inicio de este modulo para backwards-compatibility.
