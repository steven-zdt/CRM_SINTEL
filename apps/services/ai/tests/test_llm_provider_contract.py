"""
Fase 1, PLAN_MAESTRO_LLM_PROVIDER_HUB_SINTEL_CONSOLE_20260924.md -- tests
unitarios y de contrato del AIProvider ampliado (stream/health/list_models/
get_capabilities/validate_connection) + get_ai_provider()/resolve_active_llm().

Sin red real ni DB -- mismo criterio que test_embedding_provider.py (fakes/
monkeypatch, nunca golpear Ollama/Anthropic de verdad en la suite normal).
"""

from __future__ import annotations

import pytest

from apps.services.ai.providers import (
    AIProvider,
    AIResponse,
    AnthropicProvider,
    LLMCapabilities,
    LLMHealth,
    LLMResolution,
    OllamaProvider,
    OpenAICompatibleProvider,
    get_ai_provider,
    resolve_active_llm,
)


class _FakeProvider(AIProvider):
    """Implementacion minima -- solo complete(), para probar los defaults de AIProvider."""

    name = "fake"

    def __init__(self, *, fail: bool = False):
        self._fail = fail

    def complete(self, system, user_message, *, max_tokens=1024):
        if self._fail:
            raise RuntimeError("fallo simulado")
        return AIResponse(text="ok", model="fake-model", provider=self.name)


# ---------------------------------------------------------------------------
# Contratos normalizados (dataclasses)
# ---------------------------------------------------------------------------


def test_airesponse_tool_calls_finish_reason_default_vacios():
    r = AIResponse(text="hola", model="m", provider="p")
    assert r.tool_calls == []
    assert r.finish_reason is None


def test_llmcapabilities_default_no_verificado():
    caps = LLMCapabilities()
    assert caps.verified is False
    assert caps.chat is False
    assert caps.tool_calling is False


# ---------------------------------------------------------------------------
# Defaults de AIProvider (stream/health/list_models/get_capabilities/validate_connection)
# ---------------------------------------------------------------------------


def test_stream_default_no_implementado():
    p = _FakeProvider()
    with pytest.raises(NotImplementedError):
        p.stream("sys", "msg")


def test_health_default_ok_cuando_complete_funciona():
    p = _FakeProvider(fail=False)
    health = p.health()
    assert isinstance(health, LLMHealth)
    assert health.reachable is True
    assert health.model_available is True
    assert health.error is None
    assert health.latency_ms is not None


def test_health_default_falla_sin_propagar_excepcion():
    p = _FakeProvider(fail=True)
    health = p.health()
    assert health.reachable is False
    assert health.model_available is False
    assert "fallo simulado" in health.error


def test_get_capabilities_default_vacio_no_asumido():
    p = _FakeProvider()
    caps = p.get_capabilities()
    assert caps == LLMCapabilities()


def test_validate_connection_delega_en_health():
    assert _FakeProvider(fail=False).validate_connection() is True
    assert _FakeProvider(fail=True).validate_connection() is False


def test_list_models_default_no_implementado():
    with pytest.raises(NotImplementedError):
        _FakeProvider().list_models()


# ---------------------------------------------------------------------------
# get_ai_provider() -- factory (mismo patron que get_embedding_provider())
# ---------------------------------------------------------------------------


def test_get_ai_provider_anthropic_explicito():
    assert isinstance(get_ai_provider("anthropic"), AnthropicProvider)


def test_get_ai_provider_ollama_explicito():
    assert isinstance(get_ai_provider("ollama"), OllamaProvider)


def test_get_ai_provider_openai_compatible_explicito():
    assert isinstance(get_ai_provider("openai_compatible"), OpenAICompatibleProvider)


def test_get_ai_provider_default_es_anthropic_sin_env(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    assert isinstance(get_ai_provider(), AnthropicProvider)


def test_get_ai_provider_desconocido_lanza_error_claro():
    with pytest.raises(ValueError, match="Proveedor de IA desconocido"):
        get_ai_provider("inventado")


# ---------------------------------------------------------------------------
# resolve_active_llm() -- forma del resolver central (Fase 1, sin wiring a ADK todavia)
# ---------------------------------------------------------------------------


def test_resolve_active_llm_devuelve_llmresolution(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    resolution = resolve_active_llm()
    assert isinstance(resolution, LLMResolution)
    assert resolution.provider_name == "anthropic"
    assert isinstance(resolution.provider, AnthropicProvider)


def test_resolve_active_llm_acepta_parametros_del_plan_sin_usarlos(monkeypatch):
    # tenant_context/agent_context/workload se aceptan (fijan la firma que
    # pide el plan) pero no cambian el resultado todavia -- ver GAP-6.
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    r1 = resolve_active_llm()
    r2 = resolve_active_llm(
        tenant_context="cualquiera", agent_context="cualquiera", workload="erp_assistant"
    )
    assert r1.provider_name == r2.provider_name == "anthropic"


# ---------------------------------------------------------------------------
# OllamaProvider -- capacidades reales desde /api/tags (mapeo puro, sin red)
# ---------------------------------------------------------------------------


def test_ollama_capacidades_desde_tags_mapeo_real():
    provider = OllamaProvider(base_url="http://fake:11434", model="qwen3.5:4b")
    entry = {
        "name": "qwen3.5:4b",
        "capabilities": ["completion", "vision", "tools", "thinking"],
    }
    caps = provider._capabilities_from_tags(entry)
    assert caps.chat is True
    assert caps.tool_calling is True
    assert caps.vision is True
    assert caps.reasoning is True
    assert caps.verified is True
    assert caps.verified_at is not None
    # No asumidas -- este provider no implementa streaming/structured output real todavia.
    assert caps.streaming is False
    assert caps.structured_output is False


def test_ollama_capacidades_modelo_sin_capabilities_declaradas():
    provider = OllamaProvider(base_url="http://fake:11434", model="x")
    caps = provider._capabilities_from_tags({"name": "x"})
    assert caps == LLMCapabilities(verified=True, verified_at=caps.verified_at)


def test_ollama_health_usa_tags_no_complete(monkeypatch):
    """health() debe ser barato (GET /api/tags) -- nunca debe llamar a complete()."""
    provider = OllamaProvider(base_url="http://fake:11434", model="qwen3.5:4b")

    def _fake_complete(*a, **kw):
        raise AssertionError("health() no debe llamar a complete() -- debe usar /api/tags")

    monkeypatch.setattr(provider, "complete", _fake_complete)
    monkeypatch.setattr(
        provider, "_tags", lambda: [{"name": "qwen3.5:4b", "capabilities": ["completion"]}]
    )

    health = provider.health()
    assert health.reachable is True
    assert health.model_available is True


def test_ollama_health_modelo_no_instalado(monkeypatch):
    provider = OllamaProvider(base_url="http://fake:11434", model="no-instalado:1b")
    monkeypatch.setattr(provider, "_tags", lambda: [{"name": "qwen3.5:4b"}])

    health = provider.health()
    assert health.reachable is True
    assert health.model_available is False
    assert "no-instalado:1b" in health.error


def test_ollama_health_servidor_no_alcanzable(monkeypatch):
    provider = OllamaProvider(base_url="http://fake:11434", model="qwen3.5:4b")

    def _fake_tags():
        raise ConnectionError("no se pudo conectar")

    monkeypatch.setattr(provider, "_tags", _fake_tags)
    health = provider.health()
    assert health.reachable is False
    assert health.model_available is False


def test_ollama_list_models(monkeypatch):
    provider = OllamaProvider(base_url="http://fake:11434", model="qwen3.5:4b")
    monkeypatch.setattr(
        provider,
        "_tags",
        lambda: [
            {
                "name": "qwen3.5:4b",
                "capabilities": ["completion", "tools"],
                "details": {"context_length": 262144},
            }
        ],
    )
    models = provider.list_models()
    assert len(models) == 1
    assert models[0].model_id == "qwen3.5:4b"
    assert models[0].context_window == 262144
    assert models[0].capabilities.tool_calling is True
