"""
Membership Bridge - Puente centralizado entre tenant y public schema.

POLITICA DE AISLAMIENTO (REGLA 2):
    apps/tenant/core es la UNICA app tenant autorizada para importar
    directamente desde apps/public/.

    Todas las demas apps tenant que necesiten consultar membresia,
    roles, dominios o tokens de invitacion DEBEN hacerlo exclusivamente
    a traves de este modulo.

    Queda PROHIBIDO importar apps.public.tenants.models directamente
    desde cualquier app tenant que NO sea core.

Operaciones expuestas:
    - check_membership()          Verifica membresia activa (retorna instancia).
    - check_membership_exists()   Verifica membresia activa (solo bool).
    - check_admin_membership()    Verifica rol ADMIN/STAFF.
    - check_primary_admin()       Verifica is_primary_admin por schema.
    - get_user_role()             Obtiene rol mas alto del usuario.
    - get_primary_domain()        Obtiene dominio primario del tenant.
    - verify_invitation()         Verifica token de invitacion.
"""
import logging

from django.db import connection
from django_tenants.utils import get_public_schema_name

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Contexto de esquema
# ---------------------------------------------------------------------------

class _PublicSchemaContext:
    """Context manager que cambia al esquema public y restaura al salir."""

    def __enter__(self):
        self._original = connection.schema_name
        self._switched = self._original != get_public_schema_name()
        if self._switched:
            connection.set_schema_to_public()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._switched:
            connection.set_schema(self._original)
        return False


def _public_schema():
    """Retorna context manager para ejecutar queries en esquema public."""
    return _PublicSchemaContext()


# ---------------------------------------------------------------------------
# Membresia
# ---------------------------------------------------------------------------

def check_membership(user, tenant):
    """Verifica si el usuario tiene membresia activa en el tenant.

    Args:
        user: Usuario autenticado (instancia de AUTH_USER_MODEL).
        tenant: Client instance (request.tenant).

    Returns:
        TenantMembership instance o None si no existe membresia activa.
    """
    if not user or not tenant:
        return None
    try:
        from apps.public.tenants.models import TenantMembership
        with _public_schema():
            return TenantMembership.objects.filter(
                client=tenant,
                user=user,
                is_active=True,
            ).first()
    except Exception:
        logger.exception(
            "[core:membership] check_membership error | user=%s",
            getattr(user, "email", "?"),
        )
        return None


def check_membership_exists(user, tenant):
    """Verifica existencia de membresia activa (solo booleano).

    Returns:
        bool
    """
    return check_membership(user, tenant) is not None


def check_membership_by_schema(user_id, schema_name=None):
    """Verifica membresia activa por user_id y schema_name.

    Variante de check_membership_exists para uso desde la capa de
    servicios donde no se dispone de request.tenant (Client instance).

    Args:
        user_id: PK del usuario.
        schema_name: Nombre del esquema. Si es None, usa el actual.

    Returns:
        bool
    """
    if not user_id:
        return False
    if schema_name is None:
        schema_name = connection.schema_name
    if schema_name == get_public_schema_name():
        return True
    try:
        from apps.public.tenants.models import TenantMembership
        with _public_schema():
            return TenantMembership.objects.filter(
                user_id=user_id,
                client__schema_name=schema_name,
                is_active=True,
            ).exists()
    except Exception:
        logger.exception(
            "[core:membership] check_membership_by_schema error | user_id=%s schema=%s",
            user_id,
            schema_name,
        )
        return False


def check_admin_membership(user, tenant):
    """Verifica si el usuario tiene rol ADMIN o STAFF en el tenant.

    Returns:
        TenantMembership instance o None.
    """
    if not user or not tenant:
        return None
    try:
        from apps.public.tenants.models import TenantMembership
        with _public_schema():
            return TenantMembership.objects.filter(
                client=tenant,
                user=user,
                rol__in=["ADMIN", "STAFF"],
                is_active=True,
            ).first()
    except Exception:
        logger.exception(
            "[core:membership] check_admin_membership error | user=%s",
            getattr(user, "email", "?"),
        )
        return None


def check_primary_admin(user_id, schema_name=None):
    """Verifica si el usuario es el admin primario del tenant.

    Args:
        user_id: PK del usuario.
        schema_name: Nombre del esquema. Si es None, usa el esquema actual.

    Returns:
        bool
    """
    if not user_id:
        return False
    if schema_name is None:
        schema_name = connection.schema_name
    try:
        from apps.public.tenants.models import TenantMembership
        with _public_schema():
            return TenantMembership.objects.filter(
                user_id=user_id,
                client__schema_name=schema_name,
                is_primary_admin=True,
                is_active=True,
            ).exists()
    except Exception:
        logger.exception(
            "[core:membership] check_primary_admin error | user_id=%s",
            user_id,
        )
        return False


def get_user_role(user, tenant):
    """Obtiene el rol mas alto del usuario en el tenant.

    Prioridad: ADMIN > STAFF > USER.

    Returns:
        str ('ADMIN', 'STAFF', 'USER') o None si no hay membresia.
    """
    if not user or not getattr(user, "is_authenticated", False) or not tenant:
        return None
    try:
        from apps.public.tenants.models import TenantMembership
        role_priority = {"ADMIN": 3, "STAFF": 2, "USER": 1}
        with _public_schema():
            memberships = TenantMembership.objects.filter(
                client=tenant,
                user=user,
                is_active=True,
            ).only("rol")
            highest_role = None
            highest_pri = 0
            for m in memberships:
                pri = role_priority.get(m.rol, 0)
                if pri > highest_pri:
                    highest_pri = pri
                    highest_role = m.rol
            return highest_role
    except Exception:
        logger.exception(
            "[core:membership] get_user_role error | user=%s",
            getattr(user, "email", "?"),
        )
        return None


# ---------------------------------------------------------------------------
# Dominio
# ---------------------------------------------------------------------------

def get_primary_domain(tenant):
    """Obtiene el dominio primario del tenant.

    Returns:
        str (dominio) o None.
    """
    if not tenant:
        return None
    try:
        from apps.public.tenants.models import Domain
        with _public_schema():
            d = Domain.objects.filter(tenant=tenant, is_primary=True).first()
            return d.domain if d else None
    except Exception:
        logger.exception(
            "[core:membership] get_primary_domain error | tenant=%s",
            getattr(tenant, "schema_name", "?"),
        )
        return None


# ---------------------------------------------------------------------------
# Invitaciones
# ---------------------------------------------------------------------------

def verify_invitation(token):
    """Verifica un token de invitacion.

    Delega a apps.public.tenants.services.invitations.verify_invitation_token.

    Returns:
        dict con datos del payload o None si el token es invalido/expirado.
    """
    if not token:
        return None
    try:
        from apps.public.tenants.services.invitations import (
            verify_invitation_token,
        )
        return verify_invitation_token(token)
    except Exception:
        logger.exception("[core:membership] verify_invitation error")
        return None
