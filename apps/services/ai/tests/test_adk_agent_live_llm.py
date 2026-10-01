"""
Test de extremo a extremo REAL con LLM real (Fase 5, docs/adk/ADK_STATUS.md).

Marcado `slow` (pytest.ini: "tests that download models or hit slow
external resources, opt-in: -m slow") -- requiere un LLM real accesible
por el provider que `AI_PROVIDER` tenga activo (Ollama por defecto en
este entorno, ver docs/ai/OLLAMA_STATUS.md), no corre en la suite por
defecto. Ejecutar con:

    pytest apps/services/ai/tests/test_adk_agent_live_llm.py -m slow -q -s

Hallazgo real de esta sesion (verificado con litellm.completion() directo
antes de escribir este test): Qwen3.5 es un modelo de razonamiento -- una
consulta trivial ya tarda ~90s y consume ~170 tokens de "pensamiento"
antes de emitir la respuesta real. Este test por tanto usa timeouts
generosos y no se ejecuta en CI/la suite normal.

2026-09-24 (Fase 5, PLAN_MAESTRO_LLM_PROVIDER_HUB_SINTEL_CONSOLE_20260924.md):
el gate de "esta configurado" paso de leer ADK_LLM_API_BASE directo (ya no
existe ese camino, ver apps/services/ai/adk/agent.py) a usar
resolve_active_llm() -- el mismo resolver que ahora usa agent.py.
"""

import asyncio

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django_tenants.utils import schema_context

from apps.public.tenants.models import Client, Domain
from apps.services.ai.providers import resolve_active_llm
from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile

User = get_user_model()

pytestmark = pytest.mark.slow

AI_FLAGS_ON = {"AI_ENABLED": True, "AI_READ_ENABLED": True}


def _lm_studio_configurado() -> bool:
    """Nombre historico -- hoy verifica cualquier provider real resuelto
    (Ollama por defecto), no solo LM Studio. bool(resolution.model)
    alcanza: los 3 providers reales siempre tienen un modelo default no
    vacio (ver AnthropicProvider/OllamaProvider/OpenAICompatibleProvider)."""
    return bool(resolve_active_llm().model)


@pytest.fixture
def adk_tenant(db):
    schema = "adk_live_llm_test"
    tenant_obj = Client.objects.filter(schema_name=schema).first()
    if not tenant_obj:
        with schema_context("public"):
            tenant_obj = Client.objects.create(schema_name=schema, nombre="ADK Live LLM Test")
            Domain.objects.create(
                tenant=tenant_obj, domain=f"{schema}.sintel.net.co", is_primary=True
            )
    return tenant_obj


@pytest.fixture
def adk_user_y_cliente(adk_tenant):
    with schema_context(adk_tenant.schema_name):
        empresa, _ = Empresa.objects.get_or_create(
            nit="900777888",
            defaults={"razon_social": "EMPRESA ADK LIVE LLM S.A.S.", "direccion": "Calle Live LLM"},
        )
        user, created = User.objects.get_or_create(
            email="adk_live_llm_user@test.local",
            defaults={"username": "adk_live_llm_user@test.local", "password": "testpass123"},
        )
        if created:
            user.set_password("testpass123")
            user.save(update_fields=["password"])
        TenantProfile.objects.get_or_create(
            user=user, defaults={"empresa": empresa, "rol": "ADMIN"}
        )
        Cliente.objects.get_or_create(
            numero_documento="900333444",
            defaults={
                "empresa": empresa,
                "tipo_persona": "JURIDICA",
                "tipo_documento": "NIT",
                "razon_social": "Acme Distribuciones Bogota",
            },
        )
    return user


async def _run_turn(*, agent, schema_name: str, user_id: int, message: str):
    """`agent` se construye FUERA (sync, antes de asyncio.run) -- si
    `build_root_agent()` se llama aqui dentro, `resolve_active_llm()`
    dispara `SynchronousOnlyOperation` al leer `LLMActiveConfig` (Django
    bloquea ORM sincrono en contexto async) y el error queda silenciado
    por el except amplio de `_load_active_provider_from_db()`, cayendo al
    fallback por env sin avisar. Ver docstring de
    apps/services/ai/orchestrator/adk_router.py (mismo bug, mismo fix)."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="sintel_test",
        user_id=str(user_id),
        state={"sintel_schema_name": schema_name, "sintel_user_id": user_id},
    )
    runner = Runner(agent=agent, app_name="sintel_test", session_service=session_service)

    eventos = []
    async for event in runner.run_async(
        user_id=str(user_id),
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=message)]),
    ):
        eventos.append(event)
    return eventos


@pytest.mark.django_db(transaction=True)
def test_lm_studio_configurado():
    """Gate previo -- si esto falla, el resto de este archivo no tiene sentido correrlo."""
    assert (
        _lm_studio_configurado()
    ), "ADK_LLM_API_BASE vacio -- configura LM Studio antes de correr estos tests."


@pytest.mark.django_db(transaction=True)
@override_settings(**AI_FLAGS_ON)
def test_agente_responde_un_saludo_con_llm_real(adk_tenant, adk_user_y_cliente):
    """
    Prueba real de extremo a extremo: ADK -> LiteLlm -> LM Studio (Qwen3.5)
    -> respuesta real. No fuerza que tool se elige -- solo confirma que el
    LLM real procesa el turno y el Runner produce al menos un evento con
    contenido (nunca vacio/error).
    """
    if not _lm_studio_configurado():
        pytest.skip("ADK_LLM_API_BASE no configurado.")

    from apps.services.ai.adk.agent import build_root_agent

    agent = build_root_agent()
    eventos = asyncio.run(
        _run_turn(
            agent=agent,
            schema_name=adk_tenant.schema_name,
            user_id=adk_user_y_cliente.id,
            message="Hola, ¿quién eres?",
        )
    )

    assert eventos, "El Runner no produjo ningun evento -- LLM no respondio."
    textos = [
        part.text
        for e in eventos
        if e.content
        for part in (e.content.parts or [])
        if getattr(part, "text", None)
    ]
    assert any(t.strip() for t in textos), f"Ningun evento trajo texto real. Eventos: {eventos}"


@pytest.mark.django_db(transaction=True)
@override_settings(**AI_FLAGS_ON)
def test_agente_usa_buscar_cliente_con_llm_real(adk_tenant, adk_user_y_cliente):
    """
    Prueba real de que el LLM, sin que se le diga explicitamente que tool
    usar, decide invocar `buscar_cliente` para una peticion en lenguaje
    natural -- y que el resultado (via AIEngine.run_tool -> BD real) llega
    de vuelta a la conversacion.
    """
    if not _lm_studio_configurado():
        pytest.skip("ADK_LLM_API_BASE no configurado.")

    from apps.services.ai.adk.agent import build_root_agent

    agent = build_root_agent()
    eventos = asyncio.run(
        _run_turn(
            agent=agent,
            schema_name=adk_tenant.schema_name,
            user_id=adk_user_y_cliente.id,
            message="Busca el cliente Acme en el sistema.",
        )
    )

    llamadas_tool = [
        part.function_call.name
        for e in eventos
        if e.content
        for part in (e.content.parts or [])
        if getattr(part, "function_call", None)
    ]
    assert (
        "buscar_cliente" in llamadas_tool
    ), f"El LLM no invoco buscar_cliente. Tool calls vistas: {llamadas_tool}"
