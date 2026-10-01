import os

from .anthropic_provider import AnthropicProvider
from .base import (
    AIProvider,
    AIResponse,
    LLMCapabilities,
    LLMHealth,
    LLMModelDescriptor,
    LLMResolution,
)
from .embedding_base import AIEmbeddingProvider, EmbeddingProviderError, EmbeddingResult
from .fastembed_provider import FastEmbedProvider
from .ollama_provider import OllamaProvider
from .openai_compatible_provider import OpenAICompatibleProvider

__all__ = [
    "AIProvider",
    "AIResponse",
    "AnthropicProvider",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "LLMCapabilities",
    "LLMHealth",
    "LLMModelDescriptor",
    "LLMResolution",
    "AIEmbeddingProvider",
    "EmbeddingProviderError",
    "EmbeddingResult",
    "FastEmbedProvider",
    "get_embedding_provider",
    "get_ai_provider",
    "resolve_active_llm",
    "resolve_fallback_llm",
]

_EMBEDDING_PROVIDERS = {
    "fastembed": FastEmbedProvider,
}


def get_embedding_provider(name: str | None = None) -> AIEmbeddingProvider:
    """Devuelve el proveedor de embeddings configurado (default: fastembed).

    Mismo patron directo que `AnthropicProvider()` en el orquestador -- sin
    registro dinamico ni plugins, solo un dict explicito.
    """
    key = (name or os.environ.get("AI_EMBEDDING_PROVIDER", "fastembed")).lower()
    try:
        return _EMBEDDING_PROVIDERS[key]()
    except KeyError as exc:
        raise ValueError(
            f"Proveedor de embeddings desconocido: '{key}'. "
            f"Opciones: {sorted(_EMBEDDING_PROVIDERS)}"
        ) from exc


# Fase 4, documentacion/PLAN_MAESTRO_OLLAMA_QWEN35_SINTEL_AI_ENGINE_RAG_20260924.md.
# Mismo patron exacto que get_embedding_provider() arriba (dict explicito,
# sin registro dinamico). Default "anthropic" -- preserva el comportamiento
# actual de cualquier entorno sin AI_PROVIDER seteado (nunca cambiar el
# default antes de la Fase 9/Cutover del plan, que es la que decide cuando
# Ollama pasa a ser el default real).
#
# GARANTIA de portabilidad (pedido explicito del usuario, 2026-09-24): este
# dict es el UNICO lugar que hay que tocar para agregar un proveedor de LLM
# nuevo -- ni AIEngine, ni AIToolRegistry, ni form_assistant.py, ni ningun
# tool conocen que proveedor esta activo. "openai_compatible" cubre CUALQUIER
# endpoint REST que hable el formato de OpenAI Chat Completions (Gemini,
# Groq, OpenRouter, Together.ai, vLLM, LM Studio, etc.) sin escribir codigo
# nuevo -- solo AI_OPENAI_COMPAT_BASE_URL/API_KEY/MODEL. Ver
# docs/ai/AI_PROVIDER_MATRIX.md para el contrato de extension completo.
_AI_PROVIDERS = {
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
    "openai_compatible": OpenAICompatibleProvider,
}


def get_ai_provider(name: str | None = None) -> AIProvider:
    """Devuelve el proveedor de IA (LLM/completion) configurado (default: anthropic)."""
    key = (name or os.environ.get("AI_PROVIDER", "anthropic")).lower()
    try:
        return _AI_PROVIDERS[key]()
    except KeyError as exc:
        raise ValueError(
            f"Proveedor de IA desconocido: '{key}'. Opciones: {sorted(_AI_PROVIDERS)}"
        ) from exc


def _build_runtime_provider_from_db(model_config) -> AIProvider:
    """Construye un AIProvider real a partir de una fila LLMModelConfig
    (Fase 8, consola). Descifra el secreto solo en memoria, nunca lo loguea."""
    from apps.services.security.crypto import decrypt_password

    pc = model_config.provider
    secret = ""
    if pc.secret_encrypted:
        try:
            secret = decrypt_password(pc.secret_encrypted)
        except Exception:
            secret = ""  # secreto corrupto/clave rotada -- degradar a "sin key", nunca crashear el resolver.

    kwargs: dict = {"model": model_config.model_identifier}
    if pc.provider_type == "anthropic":
        if secret:
            kwargs["api_key"] = secret
        return AnthropicProvider(**kwargs)
    if pc.provider_type == "ollama":
        if pc.base_url:
            kwargs["base_url"] = pc.base_url
        return OllamaProvider(**kwargs)
    if pc.provider_type == "openai_compatible":
        if pc.base_url:
            kwargs["base_url"] = pc.base_url
        if secret:
            kwargs["api_key"] = secret
        return OpenAICompatibleProvider(**kwargs)
    raise ValueError(f"Tipo de provider desconocido en DB: '{pc.provider_type}'.")


def _load_active_provider_from_db() -> AIProvider | None:
    """
    Fase 8 (consola, LLMActiveConfig) -- si un STAFF activo una
    configuracion real desde /console/, usarla. `None` si nadie activo
    nada todavia (tabla vacia) O si la activacion mas reciente quedo
    deshabilitada (ver abajo) -- el caller cae al camino historico (env
    vars, get_ai_provider()) sin ningun cambio de comportamiento.

    Filtra por `model_config__enabled=True` y
    `model_config__provider__enabled=True` (correccion 2026-09-24,
    pedido explicito del usuario: "permiteme desactivarlo o activarlo a
    conviccion" -- deshabilitar el modelo/provider ACTUALMENTE activo
    debe dejar de usarse de inmediato, no solo bloquear activaciones
    FUTURAS via LLMActivateModelView). Recorre el historial hacia atras:
    si la activacion mas reciente ya no esta habilitada, usa la
    siguiente mas reciente que si lo este -- asi rehabilitar el mismo
    modelo despues lo vuelve a poner activo automaticamente sin que el
    usuario tenga que "re-activarlo" a mano.

    Import diferido + try/except amplio A PROPOSITO: apps/services/ai/ no
    debe fallar ni tumbar el AI Engine si apps.public.console no esta
    disponible en algun contexto (management command aislado, un test que
    no carga esa app, un problema transitorio de DB) -- degradar
    silenciosamente al camino historico es el comportamiento correcto
    aqui (Regla Absoluta del plan "NO BLOQUEAR" -- un fallo del Hub de
    providers nunca debe bloquear el AI Engine completo).
    """
    try:
        from django_tenants.utils import schema_context

        from apps.public.console.models import LLMActiveConfig

        with schema_context("public"):
            active = (
                LLMActiveConfig.objects.select_related("model_config__provider")
                .filter(model_config__enabled=True, model_config__provider__enabled=True)
                .order_by("-activated_at")
                .first()
            )
            if active is None:
                return None, None
            return _build_runtime_provider_from_db(active.model_config), active.model_config_id
    except Exception:
        return None, None


def resolve_active_llm(*, tenant_context=None, agent_context=None, workload=None) -> LLMResolution:
    """
    Resolver central (plan Seccion 12). Orden real de resolucion:
    1. Configuracion activada desde /console/ (Fase 8, LLMActiveConfig en
       DB) -- permite "cambiar de modelo sin reiniciar" (plan Seccion 25).
    2. Fallback: get_ai_provider() / AI_PROVIDER (env var, comportamiento
       historico) -- nunca se rompe para quien no usa la consola todavia.

    `tenant_context`/`agent_context`/`workload` se ACEPTAN (fijan la firma
    que pide el plan) pero se IGNORAN todavia -- GAP-6 de
    docs/ai/LLM_PROVIDER_MIGRATION_GAPS.md: el provider activo sigue
    siendo SYSTEM-wide, ninguna decision de producto tomada sobre
    overrides por tenant/workload.
    """
    provider, model_config_id = _load_active_provider_from_db()
    if provider is None:
        provider = get_ai_provider()
    return LLMResolution(
        provider=provider,
        provider_name=provider.name,
        model=getattr(provider, "model", ""),
        capabilities=provider.get_capabilities(),
        model_config_id=model_config_id,
    )


def resolve_fallback_llm(*, exclude_model_config_id: int | None = None) -> LLMResolution | None:
    """
    Fase 10 (Fallback, plan Seccion 28/45) -- "definir una policy, no una
    cadena hardcoded": el SIGUIENTE candidato habilitado con
    `fallback_priority` mas bajo (numero menor = mas prioridad), excluyendo
    el modelo que ya fallo (`exclude_model_config_id`, evita reintentar el
    mismo). `None` si no hay ningun candidato configurado -- el caller debe
    tratar eso como "sin fallback disponible", nunca inventar uno.

    Regla Absoluta "NO FALLBACK AUTOMATICO DURANTE WRITE": esta funcion NO
    decide eso -- el caller (`form_assistant.py::ask()`) solo debe invocarla
    para la llamada de "decidir que tool usar" (antes de que exista
    cualquier escritura real -- `AIEngine.run_tool()` se llama UNA sola vez
    despues, sin importar que provider tomo la decision). No usar para
    reintentar una operacion que ya escribio datos.

    Import diferido + try/except amplio A PROPOSITO, mismo criterio que
    `_load_active_provider_from_db()` (Regla Absoluta "NO BLOQUEAR").
    """
    try:
        from django_tenants.utils import schema_context

        from apps.public.console.models import LLMModelConfig

        with schema_context("public"):
            qs = (
                LLMModelConfig.objects.select_related("provider")
                .filter(enabled=True, provider__enabled=True, fallback_priority__isnull=False)
                .order_by("fallback_priority", "-verified_at")
            )
            if exclude_model_config_id is not None:
                qs = qs.exclude(pk=exclude_model_config_id)
            candidate = qs.first()
            if candidate is None:
                return None
            provider = _build_runtime_provider_from_db(candidate)
            return LLMResolution(
                provider=provider,
                provider_name=provider.name,
                model=getattr(provider, "model", ""),
                capabilities=provider.get_capabilities(),
                model_config_id=candidate.pk,
            )
    except Exception:
        return None
