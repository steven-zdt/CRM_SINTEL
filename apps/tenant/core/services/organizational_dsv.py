"""
Organizational DSV (Fase 5, proyecto OCF): evoluciona Double Semantic
Verification de `empresa -> modelo` a `empresa -> sede -> area -> modelo`.

Ver docs/ADR-004-organizational-context-framework-diseno.md y
documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md.

Generaliza el patron anti-IDOR que ya usan las 17 apps (`if obj.empresa_id
!= empresa_id: raise ...`, ver Fase 0 Anexo A) y el que ya construyo ADR-003
para objetos (`HasOrganizationalScope.has_object_permission()`), como una
funcion pura reutilizable tanto desde un permiso DRF como desde dentro de un
Business Service (Fase 8) - a diferencia de un permission class, no depende
de estar dentro de un ViewSet.

Alcance honesto de esta fase (lo que pide validar "automaticamente:
empresa, sede, area, rol, tenant, usuario"):
  - empresa: NUEVO aqui, generaliza el patron ya existente en las 17 apps.
  - sede / area: NUEVO aqui - la extension real que pide esta fase.
  - tenant: ya garantizado por el aislamiento de esquema de django-tenants
    + porque `empresa_id` solo tiene sentido dentro del schema correcto -
    no se agrega una verificacion redundante que no aporta nada nuevo.
  - usuario: ya resuelto por OrganizationalContext.resolve() (Fase 2) - si
    el usuario no esta autenticado, el contexto ni siquiera se construye.
  - rol: ya cubierto por HasTenantRole/OrganizationalPermission (Fase 4) -
    esta funcion NO reimplementa ese chequeo; compone con el, no lo duplica.
No se inventan verificaciones redundantes de tenant/usuario/rol solo para
"completar la lista" - ya existen y funcionan; esta fase se enfoca en la
unica pieza genuinamente nueva: sede/area.
"""
from __future__ import annotations

from apps.tenant.core.services.organizational_context import OrganizationalContext


class OrganizationalDSVError(Exception):
    """El objeto no pertenece al Contexto Organizacional activo (empresa,
    o sede/area segun el alcance del perfil) - equivalente organizacional
    del patron `raise ValidationError("... no pertenece a la empresa")` ya
    usado en las 17 apps (ver Fase 0), pero sin atarse a DRF."""

    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(message)


def verify_organizational_dsv(
    obj,
    context: OrganizationalContext,
    *,
    sedes_asignadas: list[int] | None = None,
    areas_asignadas: list[int] | None = None,
) -> None:
    """Verifica que `obj` pertenezca al Contexto Organizacional activo.

    - `obj.empresa_id` debe coincidir siempre con `context.empresa_id`
      (mismo chequeo que ya hacen las 17 apps, generalizado aqui).
    - Si `obj` tiene `sede_id` (SedeAwareModel, ADR-003) y
      `context.alcance` es SEDE o AREA, `obj.sede_id` debe estar en
      `sedes_asignadas` (las sedes que el perfil tiene concedidas, ver
      TenantProfile.sedes_asignadas) - si `sedes_asignadas` no se paso,
      se asume ninguna sede permitida (fail-closed).
    - Si `obj` tiene `area_id` y `context.alcance` es AREA, analogo con
      `areas_asignadas`.
    - Un objeto sin `sede_id`/`area_id` (la mayoria de modelos hoy, que
      todavia no adoptaron SedeAwareModel - ver Fase 0) solo se valida por
      `empresa_id`, igual que today.

    Lanza OrganizationalDSVError si alguna verificacion falla. No retorna
    nada si todas pasan.
    """
    obj_empresa_id = getattr(obj, "empresa_id", None)
    if obj_empresa_id != context.empresa_id:
        raise OrganizationalDSVError(
            "empresa", f"El objeto pertenece a otra empresa (esperado {context.empresa_id}, obtenido {obj_empresa_id})."
        )

    if context.alcance in ("SEDE", "AREA") and hasattr(obj, "sede_id"):
        obj_sede_id = getattr(obj, "sede_id", None)
        permitido = sedes_asignadas or []
        if obj_sede_id is not None and obj_sede_id not in permitido:
            raise OrganizationalDSVError(
                "sede", f"El objeto pertenece a una sede fuera del alcance del perfil (sede_id={obj_sede_id})."
            )

    if context.alcance == "AREA" and hasattr(obj, "area_id"):
        obj_area_id = getattr(obj, "area_id", None)
        permitido = areas_asignadas or []
        if obj_area_id is not None and obj_area_id not in permitido:
            raise OrganizationalDSVError(
                "area", f"El objeto pertenece a un area fuera del alcance del perfil (area_id={obj_area_id})."
            )


def is_organizationally_consistent(
    obj,
    context: OrganizationalContext,
    *,
    sedes_asignadas: list[int] | None = None,
    areas_asignadas: list[int] | None = None,
) -> bool:
    """Variante booleana de verify_organizational_dsv(), para llamadores que
    prefieren un `if` en vez de try/except (ej. filtrar una lista en
    memoria)."""
    try:
        verify_organizational_dsv(obj, context, sedes_asignadas=sedes_asignadas, areas_asignadas=areas_asignadas)
        return True
    except OrganizationalDSVError:
        return False
