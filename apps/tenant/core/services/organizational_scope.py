"""
OrganizationalScope (Fase F2 del proyecto Organizational Scope Framework, OSF).

Ver documentacion/ORGANIZATIONAL_SCOPE_MASTER_PLAN.md para el estado del
proyecto y documentacion/ORGANIZATIONAL_SCOPE_BASELINE.md (Fase F0) para el
diagnostico que motiva este contrato.

Relacion con OrganizationalContext (apps/tenant/core/services/organizational_context.py,
proyecto OCF ya cerrado) - **decision explicita del usuario: NO renombrar, NO
fusionar, mantener como conceptos distintos y complementarios**:

  - OrganizationalContext responde "quien soy y donde estoy PARADO ahora":
    una posicion activa unica (sede_id = la sede activa resuelta via sesion/
    primera asignada/Principal, ver resolve_sede_activa_id) usada para
    DEFAULTEAR nuevos registros (ej. la sede que se le asigna a una
    OrdenCompra nueva) y para pintar el header de UI.

  - OrganizationalScope responde "que subconjunto TOTAL de datos tengo
    permitido tocar en esta operacion": el conjunto COMPLETO de sedes/areas
    asignadas a un perfil (perfil.sedes_asignadas/areas_asignadas), sin
    colapsar a una sola "activa". Es lo que un Selector necesita para listar
    (ver Fase F7) y lo que un Business Service/Bridge necesita para validar
    un write o un acceso cross-app (Fase F8/F9).

Hallazgo que justifica la distincion (no es teorico): `OrganizationalContext.
filter(Model)` (OCF Fase 6) filtra SOLO por `self.sede_id` (la sede activa,
un unico id) incluso para un perfil con alcance=SEDE asignado a varias sedes
- mientras que `HasOrganizationalScope` (apps/tenant/api/permissions.py,
ADR-003) SI verifica contra el conjunto completo `perfil.sedes_asignadas`
para permisos a nivel de objeto. Hoy esa asimetria no se nota porque ningun
selector real usa `OrganizationalContext.filter()` todavia (adopcion real es
Fase F7) - pero si se usara tal cual, un perfil asignado a 3 sedes veria en
listados solo 1 de las 3 aunque el permiso de objeto le permitiria las 3.
`OrganizationalScope` existe para que el listado (Selectors) y el permiso de
objeto (HasOrganizationalScope) razonen sobre el MISMO conjunto - la Fase F7
debe migrar los selectors a `OrganizationalScope.filter()`, no a
`OrganizationalContext.filter()`. No se corrige `OrganizationalContext.filter()`
en esta fase (F2 es solo "definir el contrato") - queda documentado aqui y en
el plan maestro para que F7 lo resuelva con codigo, no solo con nota.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("tenant.organizational_scope")


class OrganizationalScopeError(Exception):
    """No se pudo resolver un OrganizationalScope para el request.

    Excepcion propia (no DRFValidationError), misma razon que
    OrganizationalContextError: debe poder resolverse tambien fuera de un
    ViewSet DRF.
    """


@dataclass(frozen=True)
class OrganizationalScope:
    """Limite organizacional resuelto: el conjunto TOTAL de sedes/areas que
    un perfil puede tocar, no una posicion activa unica.

    `sede_ids`/`area_ids` en None significa "sin restriccion a ese nivel"
    (alcance EMPRESA, o perfil ausente/fallback DEBUG - mismo criterio que
    HasOrganizationalScope: sin perfil, no se restringe). Un conjunto vacio
    (`frozenset()`) es distinto de None: significa alcance SEDE/AREA sin
    ninguna sede/area asignada todavia - restringe a "nada", no a "todo".
    """

    empresa_id: int
    alcance: str
    sede_ids: frozenset[int] | None
    area_ids: frozenset[int] | None

    def permits_sede(self, sede_id: int | None) -> bool:
        """True si este scope permite operar sobre `sede_id`.

        `sede_id=None` (recurso sin sede asignada) solo se permite si el
        scope no restringe por sede - mismo criterio que
        HasOrganizationalScope.has_object_permission.
        """
        if self.sede_ids is None:
            return True
        return sede_id is not None and sede_id in self.sede_ids

    def permits_area(self, area_id: int | None) -> bool:
        if self.area_ids is None:
            return True
        return area_id is not None and area_id in self.area_ids

    def to_dict(self) -> dict[str, Any]:
        """Representacion serializable (JSON-safe) - `frozenset` no es
        serializable, se convierte a lista ordenada; `None` se preserva tal
        cual (distincion real: "sin restriccion" vs "restringe a nada").
        Usada por el endpoint de solo lectura de Fase F3
        (apps/tenant/core/api/contexto.py)."""
        return {
            "empresa_id": self.empresa_id,
            "alcance": self.alcance,
            "sede_ids": sorted(self.sede_ids) if self.sede_ids is not None else None,
            "area_ids": sorted(self.area_ids) if self.area_ids is not None else None,
        }

    def filter(self, model) -> Any:
        """`scope.filter(Model)` - filtra por empresa (siempre) y por el
        conjunto COMPLETO de sedes/areas permitidas (nunca una sola "activa").

        A diferencia de OrganizationalContext.filter()/filter_by_context()
        (que reciben/resuelven un unico sede_id), este metodo usa
        `sede_id__in`/`area_id__in` porque el scope es un conjunto - ver
        docstring del modulo. Un modelo sin campo `sede`/`area` (SedeAwareModel
        no adoptado) se filtra solo por empresa, igual que hoy.
        """
        from django.core.exceptions import FieldDoesNotExist

        def _has_field(field_name: str) -> bool:
            try:
                model._meta.get_field(field_name)
                return True
            except FieldDoesNotExist:
                return False

        queryset = model.objects.all().filter(empresa_id=self.empresa_id)
        if self.sede_ids is not None and _has_field("sede"):
            queryset = queryset.filter(sede_id__in=self.sede_ids)
        if self.area_ids is not None and _has_field("area"):
            queryset = queryset.filter(area_id__in=self.area_ids)
        return queryset

    @classmethod
    def resolve(cls, request) -> OrganizationalScope:
        """Resuelve el scope completo desde un `request` autenticado.

        Duplica deliberadamente la resolucion de `empresa_id` (mismo
        algoritmo y misma justificacion que OrganizationalContext.resolve() -
        ver docstring de ese modulo) en vez de llamar a
        OrganizationalContext.resolve() y leerle `empresa_id` - decision
        explicita del usuario de mantener ambos conceptos sin acoplarlos
        entre si (ninguno debe depender de que el otro exista o se resuelva
        primero).
        """
        from django.conf import settings

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            raise OrganizationalScopeError("OrganizationalScope requiere un usuario autenticado.")

        perfil = getattr(user, "tenant_profile", None)
        empresa_id = None
        if perfil is not None:
            empresa_id = perfil.empresa_id
        elif settings.DEBUG:
            from apps.tenant.empresa.models import Empresa

            empresa = Empresa.objects.only("id").first()
            if empresa:
                logger.warning(
                    "[OrganizationalScope:DEBUG] Fallback empresa_id=%s para user=%s sin tenant_profile",
                    empresa.id, user.id,
                )
                empresa_id = empresa.id

        if empresa_id is None:
            raise OrganizationalScopeError("No se encontro configuracion de empresa para este tenant.")

        alcance = getattr(perfil, "alcance", "") or "EMPRESA"

        sede_ids: frozenset[int] | None = None
        area_ids: frozenset[int] | None = None
        if perfil is not None and alcance in ("SEDE", "AREA"):
            sede_ids = frozenset(perfil.sedes_asignadas.values_list("id", flat=True))
        if perfil is not None and alcance == "AREA":
            area_ids = frozenset(perfil.areas_asignadas.values_list("id", flat=True))

        return cls(
            empresa_id=empresa_id,
            alcance=alcance,
            sede_ids=sede_ids,
            area_ids=area_ids,
        )


class OrganizationalScopeMixin:
    """Mixin opt-in que expone `self.get_organizational_scope()`.

    Deliberadamente independiente de OrganizationalContextMixin - un
    ViewSet/vista puede heredar uno, otro, o ambos sin conflicto (no
    comparten estado ni cache). Mismo criterio "agnostico de DRF" que
    OrganizationalContextMixin: solo requiere `self.request`.
    """

    _organizational_scope: OrganizationalScope | None = None

    def get_organizational_scope(self) -> OrganizationalScope:
        if self._organizational_scope is None:
            self._organizational_scope = OrganizationalScope.resolve(self.request)
        return self._organizational_scope


def sede_esta_en_alcance(sede_id: int, request) -> bool:
    """[OSF Fase F8] Helper reusable para `validate()` de serializers: True si
    el `request` actual puede escribir sobre `sede_id`, segun su
    OrganizationalScope.

    Degrada a True (permite) si no se puede resolver un scope (sin
    request, sin usuario autenticado, sin perfil fuera de DEBUG) - mismo
    criterio de degradacion ya usado en F5/F7: no bloquear un flujo que hoy
    funciona por falta de un scope resoluble. La responsabilidad de esta
    funcion es solo el alcance organizacional (sede vs. perfil.
    sedes_asignadas) - la verificacion de que `sede` pertenece a la empresa
    (anti-IDOR) sigue siendo responsabilidad de cada serializer, como ya
    hacian antes de esta fase.
    """
    if request is None:
        return True
    try:
        return OrganizationalScope.resolve(request).permits_sede(sede_id)
    except OrganizationalScopeError:
        return True


def area_esta_en_alcance(area_id: int, request) -> bool:
    """[OSF Fase F8] Equivalente a sede_esta_en_alcance() para 'area'. Mismo
    criterio de degradacion (sin request/scope resoluble, permite)."""
    if request is None:
        return True
    try:
        return OrganizationalScope.resolve(request).permits_area(area_id)
    except OrganizationalScopeError:
        return True
