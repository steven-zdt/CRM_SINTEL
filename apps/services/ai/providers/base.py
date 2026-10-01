"""
Contrato de proveedor de IA (Fase 5 original; ampliado Fase 1 del
PLAN_MAESTRO_LLM_PROVIDER_HUB_SINTEL_CONSOLE_20260924.md). El dominio
(engine, tools) nunca importa un SDK de proveedor directamente -- solo
este contrato.

Ampliacion 2026-09-24: se evoluciona el contrato EXISTENTE (AIProvider/
AIResponse) en vez de crear uno paralelo (LLMProvider/LLMResponse) --
mandato explicito del plan (Seccion 35: "buscar y reutilizar cualquier
estructura existente"), mismo principio ya aplicado con get_ai_provider()
(evoluciono get_embedding_provider(), no invento un segundo patron).

Los metodos nuevos (health/list_models/get_capabilities/validate_connection/
stream) tienen implementacion DEFAULT en la clase base -- no son
@abstractmethod. Los 3 providers existentes (AnthropicProvider,
OllamaProvider, OpenAICompatibleProvider) siguen funcionando sin cambios;
cada uno puede sobreescribir un metodo cuando tenga una forma real y mas
barata de resolverlo (ver ollama_provider.py::list_models/health, que usa
GET /api/tags real en vez del default generico). Los que no lo hacen
(Anthropic, OpenAICompatible) usan el default y quedan correctamente
marcados como "no verificado" -- coherente con "NO ASUMIR CAPACIDADES"
(Regla Absoluta del plan).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class AIResponse:
    """Respuesta normalizada, independiente del proveedor."""

    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    # Fase 1 (Hub): normalizacion adicional que pide el plan Seccion 15 --
    # opcionales porque no todo proveedor los reporta (ej. Anthropic via el
    # flujo actual de form_assistant.py no usa tool-calling nativo del SDK).
    tool_calls: list[dict] = field(default_factory=list)
    finish_reason: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class LLMCapabilities:
    """
    Capacidades de un modelo/provider (plan Seccion 22, matriz de la UI).

    `verified=False` por default a proposito -- Regla Absoluta del plan
    "NO ASUMIR CAPACIDADES". Solo True cuando vino de un capability probe
    real (Fase 2+ del plan, no implementado en esta fase) o de un campo
    real que el propio provider reporta (ej. Ollama /api/tags -- ver
    ollama_provider.py, que SI puebla esto desde datos reales, no
    supuestos).
    """

    chat: bool = False
    streaming: bool = False
    tool_calling: bool = False
    structured_output: bool = False
    vision: bool = False
    reasoning: bool = False
    verified: bool = False
    verified_at: datetime | None = None


@dataclass
class LLMHealth:
    """Estado de salud de un provider (plan Seccion 29). Nunca incluye secretos/stack traces."""

    reachable: bool
    latency_ms: float | None = None
    model_available: bool | None = None
    error: str | None = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class LLMModelDescriptor:
    """Modelo disponible en un provider (plan Seccion 6/21, LLMModel conceptual)."""

    model_id: str
    display_name: str = ""
    context_window: int | None = None
    max_output_tokens: int | None = None
    capabilities: LLMCapabilities = field(default_factory=LLMCapabilities)


@dataclass
class LLMResolution:
    """
    Resultado de resolve_active_llm() (plan Seccion 12) -- que provider/
    modelo/capacidades aplican a una llamada dada. `provider` es la
    instancia real (AIProvider), ya lista para llamar `.complete()`.
    """

    provider: AIProvider
    provider_name: str
    model: str
    capabilities: LLMCapabilities
    # Fase 10 (Fallback, plan Seccion 28): id del LLMModelConfig real que se
    # resolvio, cuando vino de la DB -- None si vino del fallback por env
    # (get_ai_provider(), sin fila real). Permite a un caller pedir
    # resolve_fallback_llm(exclude_model_config_id=...) sin reintentar el
    # mismo modelo que ya fallo.
    model_config_id: int | None = None


class AIProvider(ABC):
    """
    Contrato que todo proveedor (Anthropic, Ollama, OpenAI-compatible,
    local) debe cumplir.

    No expone tool-calling nativo del SDK como parte del contrato --
    el AIEngine decide que tool ejecutar a partir del texto/decision
    del modelo; esto evita acoplar el dominio a la forma exacta de
    function-calling de un proveedor especifico. Si un proveedor
    soporta tool-calling nativo, su implementacion puede usarlo
    internamente sin cambiar este contrato.
    """

    name: str

    @abstractmethod
    def complete(self, system: str, user_message: str, *, max_tokens: int = 1024) -> AIResponse:
        """Genera una respuesta de una sola llamada (sin streaming)."""
        raise NotImplementedError

    def stream(self, system: str, user_message: str, *, max_tokens: int = 1024):
        """
        Genera la respuesta incrementalmente (plan Seccion 8/15). Default:
        NO soportado -- ningun caller real lo usa todavia (form_assistant.py/
        adk_router.py son sincronos, sin streaming al frontend). Implementar
        solo cuando exista un caller real (mismo criterio ya documentado en
        AI_PROVIDER_MATRIX.md sobre por que OpenAIProvider/LocalProvider no
        se implementaron sin caso de uso).
        """
        raise NotImplementedError(f"{self.name} no soporta streaming todavia.")

    def health(self) -> LLMHealth:
        """
        Chequeo de salud barato (plan Seccion 29). Default generico: un
        complete() minimo, mide latencia real. Costoso (gasta tokens) --
        providers con un endpoint de salud propio mas barato (ej. Ollama
        GET /api/tags, sin tocar el modelo) DEBEN sobreescribir esto -- ver
        ollama_provider.py::health().
        """
        import time

        t0 = time.monotonic()
        try:
            self.complete("", "ping", max_tokens=1)
        except Exception as exc:  # nunca propagar traceback/secretos -- Regla Absoluta del plan.
            return LLMHealth(
                reachable=False,
                latency_ms=(time.monotonic() - t0) * 1000,
                model_available=False,
                error=str(exc)[:300],
            )
        return LLMHealth(
            reachable=True,
            latency_ms=(time.monotonic() - t0) * 1000,
            model_available=True,
        )

    def list_models(self) -> list[LLMModelDescriptor]:
        """Modelos disponibles en este provider (plan Seccion 21). Default: no soportado."""
        raise NotImplementedError(f"{self.name} no soporta list_models().")

    def get_capabilities(self) -> LLMCapabilities:
        """
        Capacidades del modelo actualmente configurado (plan Seccion 22).
        Default: capacidades vacias/no verificadas -- nunca asumir (Regla
        Absoluta del plan "NO ASUMIR CAPACIDADES"). Providers que puedan
        reportar esto desde datos reales deben sobreescribir.
        """
        return LLMCapabilities()

    def validate_connection(self) -> bool:
        """Prueba de conexion simple para la UI (plan Seccion 20, wizard paso 6)."""
        return self.health().reachable
