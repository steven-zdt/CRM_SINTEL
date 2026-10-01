"""
Puente ADK -> AIContext (Fase 4, mismo proceso que Django -- decision
explicita del usuario, 2026-09-22: sin servicio/HTTP aparte).

Regla igual a la de `apps/services/ai/context/ai_context.py::build_context()`
(Regla Absoluta 24): el contexto de tenant/usuario SIEMPRE se re-deriva de
BD, nunca se confia en lo que una tool "decide" pasar. La unica diferencia
frente al camino HTTP normal es la fuente: aqui no hay `request.user`
(el agente ADK no vive dentro del ciclo de un request Django), la fuente es
el `session.state` de ADK, que quien INICIA la sesion (un endpoint/vista
Django real, ya autenticado) debe poblar explicitamente con
`sintel_schema_name`/`sintel_user_id` -- nunca con rol/alcance/empresa_id
(esos se re-derivan aqui, igual que build_context()).
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context

from apps.services.ai.context import AIContext, PermissionDeniedError


def build_context_from_session(*, schema_name: str, user_id: int) -> AIContext:
    """Equivalente a build_context(request), pero desde una sesion ADK en vez de un HttpRequest."""
    if not schema_name or not user_id:
        raise PermissionDeniedError("Sesion ADK sin contexto de tenant real (schema_name/user_id).")

    User = get_user_model()
    with schema_context(schema_name):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist as exc:
            raise PermissionDeniedError("Usuario no encontrado.") from exc

        profile = getattr(user, "tenant_profile", None)
        if profile is None:
            raise PermissionDeniedError(
                "El usuario no tiene un TenantProfile valido en este tenant."
            )

        sede_ids = (
            tuple(profile.sedes_asignadas.values_list("id", flat=True))
            if profile.alcance == "SEDE"
            else ()
        )
        area_ids = (
            tuple(profile.areas_asignadas.values_list("id", flat=True))
            if profile.alcance == "AREA"
            else ()
        )

        return AIContext(
            user_id=user.id,
            empresa_id=profile.empresa_id,
            schema_name=schema_name,
            rol=profile.rol,
            alcance=profile.alcance,
            sede_ids=sede_ids,
            area_ids=area_ids,
        )
