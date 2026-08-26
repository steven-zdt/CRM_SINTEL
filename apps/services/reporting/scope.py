"""
Scope Engine del Reporting Hub -- FASE 10/11 (mision Reporting Hub).

WARNING: Regla Absoluta #6: NO se crea un RBAC nuevo. Este modulo es un
envoltorio delgado sobre apps.tenant.core.services.organizational_scope.
OrganizationalScope, que ya resuelve "el conjunto TOTAL de sedes/areas que un
perfil puede tocar" (ver docstring de ese modulo). La unica logica propia de
Reporting aqui es la INTERSECCION descrita en FASE 11: el filtro que el
usuario solicita (`sede=X`) nunca puede superar lo que su OrganizationalScope
permite -- si lo supera, se rechaza con 403 en vez de devolver datos.
"""
from __future__ import annotations

from typing import Any


class ScopeViolationError(Exception):
    """El filtro solicitado excede el alcance organizacional del usuario
    (FASE 11). Se mapea a HTTP 403 en la capa API -- nunca se devuelven
    datos parciales silenciosamente cuando el usuario pidio explicitamente
    un sede_id/area_id fuera de su alcance."""

    def __init__(self, message: str, field: str, requested_value: Any) -> None:
        super().__init__(message)
        self.field = field
        self.requested_value = requested_value


def resolve_effective_scope(django_request):
    """Resuelve el OrganizationalScope real del usuario autenticado.
    Lazy import deliberado (mismo criterio que el resto del codebase, ver
    organizational_context.py) -- apps/services/ no debe importar
    apps.tenant.* a nivel de modulo."""
    from apps.tenant.core.services.organizational_scope import OrganizationalScope

    return OrganizationalScope.resolve(django_request)


def enforce_requested_filters(scope, filters: dict[str, Any]) -> None:
    """Valida que los filtros `sede`/`area` solicitados en un ReportRequest
    esten dentro de `scope` (FASE 11). No modifica `filters` -- solo lanza
    ScopeViolationError si el usuario pidio explicitamente algo que su
    alcance no permite. Filtros que no son 'sede'/'area' (fecha, cliente,
    etc.) son responsabilidad del Provider, no del Scope Engine.

    Un usuario con alcance EMPRESA (scope.sede_ids is None) puede solicitar
    cualquier sede -- sin restriccion adicional, igual que hoy en
    HasOrganizationalScope.
    """
    sede_value = filters.get("sede")
    if sede_value is not None and not scope.permits_sede(int(sede_value)):
        raise ScopeViolationError(
            f"No tiene acceso a la sede {sede_value} (alcance organizacional).",
            field="sede",
            requested_value=sede_value,
        )

    area_value = filters.get("area")
    if area_value is not None and not scope.permits_area(int(area_value)):
        raise ScopeViolationError(
            f"No tiene acceso al area {area_value} (alcance organizacional).",
            field="area",
            requested_value=area_value,
        )
