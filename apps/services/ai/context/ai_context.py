"""
AI Context Engine (Fase 8/24).

Construye el contexto autorizado con el que el AIEngine ejecuta un
tool call -- SIEMPRE a partir del request real autenticado (SSoT:
request.user.tenant_profile), NUNCA inferido de lenguaje natural
(Regla Absoluta 24).

No incluye secretos ni datos de otro tenant -- build_context() lanza
PermissionDeniedError si el usuario no tiene un TenantProfile valido
en el schema actual, en vez de intentar adivinar una empresa_id.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class PermissionDeniedError(Exception):
    """El request no tiene contexto de tenant/empresa valido para usar el AI Engine."""


@dataclass(frozen=True)
class AIContext:
    """
    Contexto minimo y autorizado para un tool call. Inmutable -- un
    tool nunca puede "ampliar" su propio alcance modificando esto en
    tiempo de ejecucion.
    """
    user_id: int
    empresa_id: int
    schema_name: str
    rol: str
    alcance: str
    sede_ids: tuple[int, ...] = field(default_factory=tuple)
    area_ids: tuple[int, ...] = field(default_factory=tuple)
    # Contexto de pantalla opcional (Fase 23) -- provisto por el frontend,
    # nunca contiene secretos; solo orienta que herramientas son relevantes.
    screen_app: str | None = None
    screen_entity: str | None = None
    screen_entity_id: str | None = None
    screen_operation: str | None = None


def build_context(request, *, screen: dict | None = None) -> AIContext:
    """
    Construye AIContext desde un request Django/DRF ya autenticado.

    Args:
        request: HttpRequest/Request real, con request.user y
            request.tenant ya resueltos por el middleware existente
            (TenantMainMiddleware) -- este modulo no resuelve tenant
            por su cuenta, reutiliza la resolucion ya hecha.
        screen: dict opcional {"app", "entity", "entity_id", "operation"}
            enviado por el frontend (Fase 23) -- nunca password/token/secrets,
            eso es responsabilidad del caller, aqui solo se copian esas
            4 claves conocidas, cualquier otra clave se ignora.

    Raises:
        PermissionDeniedError: si el usuario no esta autenticado o no
            tiene un TenantProfile valido en el schema actual.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        raise PermissionDeniedError("Usuario no autenticado.")

    profile = getattr(user, "tenant_profile", None)
    if profile is None:
        raise PermissionDeniedError(
            "El usuario no tiene un TenantProfile valido en este tenant -- "
            "el AI Engine no puede operar sin contexto empresarial real."
        )

    tenant = getattr(request, "tenant", None)
    schema_name = getattr(tenant, "schema_name", "") if tenant else ""

    sede_ids = tuple(profile.sedes_asignadas.values_list("id", flat=True)) if profile.alcance == "SEDE" else ()
    area_ids = tuple(profile.areas_asignadas.values_list("id", flat=True)) if profile.alcance == "AREA" else ()

    screen = screen or {}
    return AIContext(
        user_id=user.id,
        empresa_id=profile.empresa_id,
        schema_name=schema_name,
        rol=profile.rol,
        alcance=profile.alcance,
        sede_ids=sede_ids,
        area_ids=area_ids,
        screen_app=screen.get("app"),
        screen_entity=screen.get("entity"),
        screen_entity_id=screen.get("entity_id"),
        screen_operation=screen.get("operation"),
    )
