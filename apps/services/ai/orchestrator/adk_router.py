"""
Router ADK (Fase 6, docs/adk/ADK_STATUS.md) -- dispatcha /api/v1/ai/ask/ al
agente ADK (LM Studio local via LiteLlm, apps/services/ai/adk/agent.py) en
vez del flujo Anthropic existente (form_assistant.py) cuando
AI_ADK_ENABLED=true.

Reutiliza el patron ya probado en
test_adk_agent_live_llm.py::_run_turn -- mismo Runner/InMemorySessionService
con session.state poblado con sintel_schema_name/sintel_user_id (el
contrato que ya exigen las tools en apps/services/ai/adk/tools.py), nunca
inventa un segundo camino.

Bridging sync->async: la vista Django (WSGI, sync) invoca esta funcion de
forma sincrona -- asgiref.async_to_sync ejecuta el Runner async (requisito
de la libreria ADK) sin bloquear el ORM (las tools ya aislan su parte
sincrona via sync_to_async, ver apps/services/ai/adk/tools.py).

`build_root_agent()` se construye AQUI, en `ask()` (sync, antes de entrar
al bridge), y se pasa ya armado a `_run_turn()` -- NUNCA importarlo/llamarlo
dentro de la funcion async. Motivo (bug real, Fase 8 del PLAN_MAESTRO_
LLM_PROVIDER_HUB_SINTEL_CONSOLE_20260924.md): `build_root_agent()` ->
`_build_model()` -> `resolve_active_llm()` hace una consulta ORM sincrona
real (lee `LLMActiveConfig`) -- llamada desde dentro de una funcion async
(aunque sea antes de cualquier `await`), Django la bloquea con
`SynchronousOnlyOperation`. Como `_load_active_provider_from_db()` atrapa
`Exception` a proposito (no debe tumbar el AI Engine si la consola falla),
ese error quedaba SILENCIADO y el resolver caia al fallback por env
(`AI_PROVIDER`) sin que nadie lo notara -- la consola podia activar
cualquier modelo y el agente real seguia usando el de siempre. Verificado
real: reproducido con `SynchronousOnlyOperation` explicito llamando
`resolve_active_llm()` dentro de `async_to_sync`, y confirmado que
resolver ANTES del bridge (este fix) produce `agent.model.model` con el
proveedor/modelo correcto.
"""

from __future__ import annotations

import logging

from asgiref.sync import async_to_sync
from django.conf import settings

from apps.services.ai.context import PermissionDeniedError, build_context

logger = logging.getLogger("ai_engine")


async def _run_turn(*, agent, schema_name: str, user_id: int, message: str):
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="sintel_ai_ask",
        user_id=str(user_id),
        state={"sintel_schema_name": schema_name, "sintel_user_id": user_id},
    )
    runner = Runner(agent=agent, app_name="sintel_ai_ask", session_service=session_service)

    eventos = []
    async for event in runner.run_async(
        user_id=str(user_id),
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=message)]),
    ):
        eventos.append(event)
    return eventos


def ask(request, message: str, *, screen: dict | None = None) -> dict:
    """Equivalente a form_assistant.ask(), pero via el agente ADK (Router, Fase 6)."""
    if not bool(getattr(settings, "AI_ENABLED", False)):
        return {
            "status": "PERMISSION_DENIED",
            "message": "AI Engine deshabilitado en este entorno.",
        }

    try:
        context = build_context(request, screen=screen)
    except PermissionDeniedError as exc:
        return {"status": "PERMISSION_DENIED", "message": str(exc)}

    try:
        # Sincrono, ANTES del bridge async -- ver docstring del modulo (bug
        # real de SynchronousOnlyOperation evitado a proposito aqui).
        from apps.services.ai.adk.agent import build_root_agent

        agent = build_root_agent()
        eventos = async_to_sync(_run_turn)(
            agent=agent,
            schema_name=context.schema_name,
            user_id=context.user_id,
            message=message,
        )
    except Exception as exc:  # LM Studio caido, error de red/LiteLLM, etc. -- entorno, no negocio.
        logger.error("ai_orchestrator.adk_run_failed error=%s", exc)
        return {"status": "INTERNAL_ERROR", "message": f"El agente ADK fallo: {exc}"}

    tool_used = next(
        (
            part.function_call.name
            for e in eventos
            if e.content
            for part in (e.content.parts or [])
            if getattr(part, "function_call", None)
        ),
        None,
    )
    # Los eventos de ADK/LiteLlm ya separan reasoning_content de content --
    # solo se lee `part.text` (contenido real), nunca el campo de
    # razonamiento (regla del plan de evolucion Seccion 26, ver agent.py).
    textos = [
        part.text
        for e in eventos
        if e.content
        for part in (e.content.parts or [])
        if getattr(part, "text", None)
    ]
    mensaje = next((t.strip() for t in reversed(textos) if t.strip()), None)

    if not mensaje:
        return {"status": "INTERNAL_ERROR", "message": "El agente ADK no genero una respuesta."}

    return {"status": "OK", "tool_used": tool_used, "data": None, "message": mensaje}
