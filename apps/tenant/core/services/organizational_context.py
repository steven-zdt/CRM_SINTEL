"""
OrganizationalContext (Fase 2 del proyecto Organizational Context Framework).

Ver docs/ADR-004-organizational-context-framework-diseno.md para el diseño
completo (Fase 1) y documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md
para el estado del proyecto.

Objeto inmutable, resuelto una vez por request, que ENVUELVE (no reemplaza)
la resolucion ya existente:
  - empresa_id / sede_id: mismo algoritmo que SintelDSVMixin.get_empresa_id()/
    get_sede_id() (apps/tenant/api/mixins.py) - duplicado aqui a proposito en
    vez de refactorizar el mixin, por decision explicita de ADR-004 ("Fase 2
    ... sin tocar SintelDSVMixin existente"). Si alguno de los dos algoritmos
    cambia, el otro debe actualizarse a mano - ver test de paridad en
    tools/ekg o en los tests de este modulo.
  - alcance/rol: TenantProfile.rol/alcance (SSoT sin cambios, ADR-003).

Fase 2 es exclusivamente "implementar la clase" - NO esta conectada a ningun
ViewSet/vista todavia (eso es Fase 3 "Organizational Resolver" y Fase 9
"Migracion aplicacion por aplicacion"). Usarla hoy es opt-in y no afecta a
ninguna app existente.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("tenant.organizational_context")


class OrganizationalContextError(Exception):
    """No se pudo resolver un OrganizationalContext completo para el request.

    Excepcion propia (no DRFValidationError) porque OrganizationalContext
    debe poder resolverse tambien fuera de un ViewSet DRF (vistas HTML
    server-rendered, tareas, shell) - ver Fase 3 del proyecto OCF.
    """


@dataclass(frozen=True)
class OrganizationalContext:
    """Contexto Organizacional resuelto: Tenant -> Empresa -> Sede -> Area ->
    Usuario -> Perfil -> Rol -> Permisos (alcance) -> Timezone/Configuracion.

    `sede_id`/`area_id` pueden ser None (empresa aun sin ninguna Sede, o sin
    area activa - la mayoria de operaciones no la requieren). El resto de
    campos son siempre obligatorios una vez resuelto.
    """

    tenant_schema: str
    tenant_id: int | None
    empresa_id: int
    sede_id: int | None
    area_id: int | None
    user_id: int
    perfil_id: int | None
    rol: str
    alcance: str
    timezone: str
    configuracion: dict[str, Any] = field(default_factory=dict)

    def filter(self, model) -> Any:
        """[Fase 6, OCF "Organizational Selectors"] `context.filter(Model)`
        - resuelve automaticamente empresa (siempre) y sede/area (segun
        `self.alcance`) sin que el llamador repita la logica de "cuando
        aplica sede_id" en cada selector (Fase 0 confirmo que las 17 apps
        repiten `.filter(empresa_id=...)` cada una por su cuenta).

        Generaliza filter_by_context() (ADR-003, hoy usado explicitamente
        solo por compras) resolviendo sede_id/area_id DESDE el contexto en
        vez de recibirlos como parametro. Un modelo sin `sede`/`area`
        (SedeAwareModel no adoptado, la mayoria hoy - ver Fase 0) se filtra
        solo por empresa, exactamente igual que hoy - no se asume el campo,
        se verifica con `_meta.get_field()`.

        Retorna un QuerySet - el llamador sigue encadenando `.only()`/
        `.select_related()` como ya hace cada selector.
        """
        from django.core.exceptions import FieldDoesNotExist

        from apps.tenant.core.services.organizational_filters import filter_by_context

        def _has_field(field_name: str) -> bool:
            try:
                model._meta.get_field(field_name)
                return True
            except FieldDoesNotExist:
                return False

        sede_id = self.sede_id if (self.alcance in ("SEDE", "AREA") and _has_field("sede")) else None
        area_id = self.area_id if (self.alcance == "AREA" and _has_field("area")) else None
        return filter_by_context(model.objects.all(), self.empresa_id, sede_id=sede_id, area_id=area_id)

    def to_dict(self) -> dict[str, Any]:
        """Representacion serializable (JSON-safe) - usada por el endpoint
        de solo lectura de Fase 3 (apps/tenant/core/api/contexto.py)."""
        return {
            "tenant_schema": self.tenant_schema,
            "tenant_id": self.tenant_id,
            "empresa_id": self.empresa_id,
            "sede_id": self.sede_id,
            "area_id": self.area_id,
            "user_id": self.user_id,
            "perfil_id": self.perfil_id,
            "rol": self.rol,
            "alcance": self.alcance,
            "timezone": self.timezone,
            "configuracion": self.configuracion,
        }

    @classmethod
    def resolve(cls, request) -> "OrganizationalContext":
        """Resuelve el contexto completo desde un `request` autenticado.

        Unico punto de lectura de `request.user`/`request.tenant` dentro de
        este modulo - el llamador (Fase 9 en adelante) no deberia necesitar
        leerlos directamente una vez que adopte este objeto.

        Lanza OrganizationalContextError si el usuario no esta autenticado o
        no tiene TenantProfile en este tenant (sin fallback DEBUG propio -
        ver nota de paridad en el docstring del modulo: si se necesita ese
        fallback, debe replicarse aqui explicitamente, no asumirse).
        """
        from django.conf import settings

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            raise OrganizationalContextError("OrganizationalContext requiere un usuario autenticado.")

        tenant = getattr(request, "tenant", None)
        tenant_schema = getattr(tenant, "schema_name", "") if tenant else ""
        tenant_id = getattr(tenant, "id", None) if tenant else None

        perfil = getattr(user, "tenant_profile", None)
        empresa_id = None
        if perfil is not None:
            empresa_id = perfil.empresa_id
        elif settings.DEBUG:
            # Mismo fallback (y misma advertencia) que SintelDSVMixin.get_empresa_id() -
            # duplicado a proposito, ver docstring del modulo.
            from apps.tenant.empresa.models import Empresa

            empresa = Empresa.objects.only("id").first()
            if empresa:
                logger.warning(
                    "[OrganizationalContext:DEBUG] Fallback empresa_id=%s para user=%s sin tenant_profile",
                    empresa.id, user.id,
                )
                empresa_id = empresa.id

        if empresa_id is None:
            raise OrganizationalContextError("No se encontro configuracion de empresa para este tenant.")

        from apps.tenant.core.services.sede_context import resolve_sede_activa_id

        sede_id = resolve_sede_activa_id(request, empresa_id, perfil)

        return cls(
            tenant_schema=tenant_schema,
            tenant_id=tenant_id,
            empresa_id=empresa_id,
            sede_id=sede_id,
            # Ninguna app requiere hoy un "area activa" resuelta automaticamente
            # (ver Fase 0, documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md
            # seccion 2.7) - a diferencia de sede, no existe algoritmo de
            # resolucion de area que replicar sin inventarlo. Se deja en None
            # hasta que una fase futura defina uno con un caso de uso real.
            area_id=None,
            user_id=user.id,
            perfil_id=getattr(perfil, "id", None),
            rol=getattr(perfil, "rol", ""),
            alcance=getattr(perfil, "alcance", ""),
            # No existe hoy ninguna configuracion de timezone por empresa/perfil
            # (verificado: ningun modelo tiene un campo timezone) - se usa el
            # timezone global del proyecto en vez de inventar una fuente que no
            # existe.
            timezone=settings.TIME_ZONE,
            configuracion=dict(getattr(perfil, "configuracion", None) or {}),
        )


class OrganizationalContextMixin:
    """Mixin opt-in (Fase 3, "Organizational Resolver") que expone
    `self.get_organizational_context()` sobre `OrganizationalContext.resolve()`.

    Aditivo: no reemplaza SintelDSVMixin ni sus metodos - un ViewSet o vista
    puede heredar ambos sin conflicto (`get_empresa_id()` sigue funcionando
    igual). Deliberadamente agnostico de DRF: solo requiere `self.request`,
    por lo que sirve igual para un ViewSet DRF (autenticado por JWT o
    Session, ver apps/tenant/api/base.py's RelaxedJWTAuthentication +
    SessionAuthentication) que para una vista HTML server-rendered que sirve
    fragmentos HTMX (ej. apps/tenant/compras/views.py's OrdenCompraTableView,
    que ya usa SintelDSVMixin directamente sin heredar de nada DRF).

    Ningun ViewSet/vista existente hereda este mixin todavia - la adopcion
    real ocurre app por app en Fase 9.
    """

    _organizational_context: OrganizationalContext | None = None

    def get_organizational_context(self) -> OrganizationalContext:
        if self._organizational_context is None:
            self._organizational_context = OrganizationalContext.resolve(self.request)
        return self._organizational_context
