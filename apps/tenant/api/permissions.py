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

class HasOrganizationalScope(permissions.BasePermission):
    """[ADR-003] Restringe el acceso a un objeto segun
    TenantProfile.alcance (EMPRESA/SEDE/AREA), ortogonal a HasTenantRole.

    - alcance=EMPRESA (o perfil ausente, ej. fallback DEBUG): sin
      restriccion adicional - es el comportamiento de hoy.
    - alcance=SEDE: el objeto debe tener `sede_id` en
      perfil.sedes_asignadas.
    - alcance=AREA: el objeto debe tener `area_id` en
      perfil.areas_asignadas.

    Solo verifica a nivel de objeto (retrieve/update/delete de un recurso
    puntual, ej. anti-IDOR cross-sede via UUID directo) - el filtrado de
    listas ya ocurre en el selector (ver OrdenCompraServiceMixin.get_qs_list
    en apps/tenant/compras/services/api_mixins.py), por lo que
    has_permission() siempre permite continuar.
    """
    message = "No tiene acceso a la sede/area de este recurso (alcance organizacional)."

    def has_permission(self, request, view) -> bool:
        return True

    def has_object_permission(self, request, view, obj) -> bool:
        perfil = _get_perfil(request.user)
        if perfil is None or perfil.alcance == 'EMPRESA':
            return True

        if perfil.alcance == 'SEDE':
            sede_id = getattr(obj, 'sede_id', None)
            return sede_id is not None and perfil.sedes_asignadas.filter(id=sede_id).exists()

        if perfil.alcance == 'AREA':
            area_id = getattr(obj, 'area_id', None)
            return area_id is not None and perfil.areas_asignadas.filter(id=area_id).exists()

        return True


class OrganizationalPermission(permissions.BasePermission):
    """[Fase 4, OCF] Permiso generalizado por nivel jerarquico organizacional
    (ADMIN_GLOBAL > ADMIN_EMPRESA > ADMIN_SEDE > JEFE_AREA > OPERADOR >
    CONSULTA - ver apps/tenant/core/services/organizational_permissions.py).

    Nueva infraestructura, aditiva: NO reemplaza HasTenantRole/
    IsTenantProfileAdmin/HasOrganizationalScope, que siguen funcionando
    exactamente igual. Un ViewSet puede seguir usando esas clases tal cual;
    esta es una via alternativa para el ViewSet que prefiera declarar un
    nivel jerarquico en vez de una lista de roles.

    Uso (opt-in):
        class MiViewSet(OrganizationalContextMixin, BaseTenantViewSet):
            minimum_organizational_level = 'ADMIN_SEDE'
            permission_classes = [IsTenantMember, OrganizationalPermission]

    Requiere que el ViewSet herede OrganizationalContextMixin (Fase 3,
    apps/tenant/core/services/organizational_context.py) para resolver el
    contexto - si no lo hereda, deniega (fail-closed) en vez de asumir un
    nivel. Si el ViewSet no declara `minimum_organizational_level`, esta
    clase no restringe nada (permite continuar) - es responsabilidad del
    ViewSet optar explicitamente.
    """
    message = "Su nivel organizacional no tiene permiso para esta operacion."

    def has_permission(self, request, view) -> bool:
        minimum = getattr(view, 'minimum_organizational_level', None)
        if not minimum:
            return True

        get_context = getattr(view, 'get_organizational_context', None)
        if get_context is None:
            return False  # fail-closed: el ViewSet no hereda OrganizationalContextMixin

        from apps.tenant.core.services.organizational_context import OrganizationalContextError
        from apps.tenant.core.services.organizational_permissions import (
            level_meets_minimum,
            resolve_organizational_permission_level,
        )

        try:
            context = get_context()
        except OrganizationalContextError:
            return False

        is_staff = bool(getattr(request.user, 'is_staff', False))
        level = resolve_organizational_permission_level(rol=context.rol, alcance=context.alcance, is_staff=is_staff)
        return level_meets_minimum(level, minimum)


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
        from rest_framework.permissions import SAFE_METHODS

        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return False

        if request.method in SAFE_METHODS:
            return True

        # ViewSets con enforced mode manejan la verificacion internamente
        if hasattr(view, '_check_enforced_mode'):
            return True

        return IsTenantAdmin().has_permission(request, view)
