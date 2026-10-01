"""
Definicion de que campos necesita REALMENTE cada `provider_type` (Fase 8,
correccion 2026-09-24: "el formulario de la consola no puede inventar
campos que el adapter no usa").

Esta es la UNICA fuente de verdad que el frontend consulta para saber que
mostrar -- `llm_providers_manager.js` NUNCA debe hardcodear reglas de
"que campo va con que tipo" por su cuenta (evita una segunda copia de esta
logica desincronizandose del backend real).

Cada entrada esta AUDITADA linea por linea contra el `__init__()` real del
adapter (no es una suposicion de que "normalmente" necesita un proveedor):

- ollama -> apps/services/ai/providers/ollama_provider.py
    `__init__(self, base_url=None, model=None, *, timeout_s=None, max_retries=None)`
    Sin api_key -- Ollama no implementa autenticacion. Discovery real via
    GET /api/tags (`list_models()` sobreescrito, ver ese archivo).
- anthropic -> apps/services/ai/providers/anthropic_provider.py
    `__init__(self, api_key=None, model=None)`
    Sin base_url -- usa el SDK oficial `anthropic`, resuelve su propio
    endpoint. `list_models()` NO esta sobreescrito -> hereda
    NotImplementedError de AIProvider (base.py) -- sin discovery real.
- openai_compatible -> apps/services/ai/providers/openai_compatible_provider.py
    `__init__(self, base_url=None, api_key=None, model=None, ...)`
    api_key opcional (el header Authorization solo se agrega si hay valor,
    ver openai_compatible_provider.py linea ~66). `list_models()` tampoco
    esta sobreescrito -> mismo NotImplementedError, sin discovery real.

MCP deliberadamente NO aparece aqui: `/mcp/` en este proyecto es un
SERVIDOR (SINTEL expone sus propios ViewSets como tools via
django-rest-framework-mcp, ver docs/ai/AI_MCP_POLICY.md) -- lo inverso de
"conectar a un LLM externo via MCP". No existe ningun AIProvider basado en
MCP en `apps/services/ai/providers/__init__.py::_AI_PROVIDERS` -- agregar
esa opcion en el formulario seria un campo/tipo inventado que el backend
no puede ejecutar.

`health()`/`validate_connection()`: solo ollama sobreescribe `health()`
con un chequeo barato (GET /api/tags, no gasta tokens). anthropic y
openai_compatible heredan el default generico de AIProvider (base.py):
una llamada real a `complete()` con max_tokens=1 -- es decir, "Probar
conexion" para esos dos tipos SI gasta un token/credito real del
proveedor (causa real observada en esta sesion: un "Probar conexion"
contra OpenRouter agoto parte del credito disponible antes de la llamada
de activacion real). El campo `cheap_health` de abajo documenta esto para
que la UI pueda avisarlo, no para ocultarlo.
"""

from __future__ import annotations

CONNECTION_SCHEMAS: dict[str, dict] = {
    "ollama": {
        "label": "Ollama (servidor local, sin autenticacion)",
        "requires_base_url": True,
        "base_url_label": "URL de Ollama",
        "base_url_placeholder": "http://ollama:11434",
        "base_url_default": "http://ollama:11434",
        "requires_secret": False,
        "secret_optional": False,
        "secret_label": None,
        "supports_model_discovery": True,
        "cheap_health": True,
        "notes": (
            "Ollama no soporta autenticacion -- no hay campo de API Key. "
            "Los modelos disponibles se descubren automaticamente contra "
            "el propio servidor (GET /api/tags), no se escriben a mano."
        ),
    },
    "anthropic": {
        "label": "API Key (Anthropic)",
        "requires_base_url": False,
        "base_url_label": None,
        "base_url_placeholder": None,
        "base_url_default": None,
        "requires_secret": True,
        "secret_optional": False,
        "secret_label": "API Key de Anthropic",
        "supports_model_discovery": False,
        "cheap_health": False,
        "notes": (
            "Usa el SDK oficial de Anthropic -- no hay campo de URL, el "
            "SDK resuelve su propio endpoint. Este proveedor no expone un "
            "endpoint de descubrimiento de modelos: escribe el identificador "
            "exacto (ej. claude-haiku-4-5-20251001). "
            "'Probar conexion' hace una llamada real minima -- consume un "
            "token/credito real de tu cuenta."
        ),
    },
    "openai_compatible": {
        "label": "REST OpenAI-compatible (OpenRouter, Groq, LM Studio, Gemini, vLLM, etc.)",
        "requires_base_url": True,
        "base_url_label": "Base URL",
        "base_url_placeholder": "https://openrouter.ai/api/v1",
        "base_url_default": None,
        "requires_secret": False,
        "secret_optional": True,
        "secret_label": "API Key (opcional -- segun si el endpoint la exige)",
        "supports_model_discovery": False,
        "cheap_health": False,
        "notes": (
            "Cubre cualquier endpoint que hable el formato Chat Completions "
            "de OpenAI (el sistema agrega /chat/completions solo, no lo "
            "incluyas en la Base URL). Este proveedor no expone un endpoint "
            "de descubrimiento de modelos todavia: escribe el identificador "
            "exacto tal como lo espera el proveedor (ej. openai/gpt-4o para "
            "OpenRouter). "
            "'Probar conexion' hace una llamada real minima -- si el "
            "proveedor cobra por uso, consume credito real de tu cuenta."
        ),
    },
}


def list_connection_schemas() -> list[dict]:
    return [{"provider_type": key, **value} for key, value in CONNECTION_SCHEMAS.items()]
