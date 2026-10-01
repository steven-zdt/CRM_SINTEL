"""
Implementacion Ollama del contrato AIProvider (Fase 3,
documentacion/PLAN_MAESTRO_OLLAMA_QWEN35_SINTEL_AI_ENGINE_RAG_20260924.md).

Mismo patron que anthropic_provider.py -- sin SDK propio (Ollama expone una
API REST simple), usando `requests` (ya en requirements.txt, sin dependencia
nueva). Decision de diseno GAP-4 original (docs/ai/OLLAMA_MIGRATION_GAPS.md):
este provider sirve al camino AIProvider/form_assistant.py. ADK usa Ollama
por una via DISTINTA (google.adk.models.lite_llm.LiteLlm, configurado con
ADK_LLM_MODEL=ollama_chat/... -- ver apps/services/ai/adk/agent.py y
docs/ai/OLLAMA_STATUS.md Fase 5) -- ambos hablan con el MISMO servicio
Ollama, por caminos de codigo distintos (decision GAP-4 del Hub de
providers, docs/ai/LLM_PROVIDER_DEPENDENCY_MAP.md: unificarlos es Fase 5
de ese plan, no hecho todavia).

DEFAULT_MODEL = qwen3.5:4b, no 9b -- ver docs/ai/OLLAMA_STATUS.md (incidente
real de saturacion de host con el modelo 9b, resuelto bajando a 4b + limites
de recursos en el contenedor).

Fase 1 del PLAN_MAESTRO_LLM_PROVIDER_HUB_SINTEL_CONSOLE_20260924.md:
health()/list_models()/get_capabilities() sobreescritos con datos REALES de
GET /api/tags (barato, no gasta tokens ni carga el modelo) -- no el default
generico de AIProvider (que llamaria complete(), caro en este hardware).
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime

from .base import AIProvider, AIResponse, LLMCapabilities, LLMHealth, LLMModelDescriptor

DEFAULT_MODEL = "qwen3.5:4b"
DEFAULT_BASE_URL = "http://ollama:11434"
# docs/ai/OLLAMA_STATUS.md: latencia real observada CPU-only en este
# hardware fue 5m26s (326s) para una respuesta trivial de una palabra --
# el default del plan (120s, seccion 6) hubiera cortado esa misma llamada
# real. 300s como default honesto hasta que Fase 8 (benchmark) mida un
# numero mejor o se confirme GPU passthrough.
DEFAULT_TIMEOUT_S = 300
DEFAULT_MAX_RETRIES = 1


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        *,
        timeout_s: float | None = None,
        max_retries: int | None = None,
    ):
        self.base_url = (base_url or os.environ.get("AI_OLLAMA_BASE_URL", DEFAULT_BASE_URL)).rstrip(
            "/"
        )
        self.model = model or os.environ.get("AI_OLLAMA_MODEL", DEFAULT_MODEL)
        self.timeout_s = float(
            timeout_s
            if timeout_s is not None
            else os.environ.get("AI_PROVIDER_TIMEOUT_S", DEFAULT_TIMEOUT_S)
        )
        self.max_retries = int(
            max_retries
            if max_retries is not None
            else os.environ.get("AI_PROVIDER_MAX_RETRIES", DEFAULT_MAX_RETRIES)
        )

    def complete(self, system: str, user_message: str, *, max_tokens: int = 1024) -> AIResponse:
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("Paquete 'requests' no instalado.") from exc

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
            "options": {"num_predict": max_tokens},
        }

        last_error: Exception | None = None
        for _attempt in range(self.max_retries + 1):
            try:
                resp = requests.post(
                    f"{self.base_url}/api/chat", json=payload, timeout=self.timeout_s
                )
            except requests.exceptions.RequestException as exc:
                last_error = exc
                continue

            if resp.status_code == 404:
                raise RuntimeError(
                    f"Modelo '{self.model}' no encontrado en Ollama ({self.base_url}) -- "
                    f"correr 'ollama pull {self.model}' primero."
                )
            if not resp.ok:
                last_error = RuntimeError(f"Ollama respondio {resp.status_code}: {resp.text[:300]}")
                continue

            data = resp.json()
            # `message.content` es SIEMPRE la respuesta final -- Ollama
            # separa el razonamiento de modelos "thinking" (Qwen3.5, ver
            # docs/adk/ADK_STATUS.md Fase 5) en un campo aparte
            # (`message.thinking`) que este provider NUNCA lee ni reenvia
            # (Regla Absoluta 18/22 del plan: "NO EXPONER reasoning_content").
            text = (data.get("message") or {}).get("content", "")
            return AIResponse(
                text=text,
                model=data.get("model", self.model),
                provider=self.name,
                input_tokens=data.get("prompt_eval_count", 0) or 0,
                output_tokens=data.get("eval_count", 0) or 0,
                raw={
                    "done_reason": data.get("done_reason"),
                    "total_duration_ns": data.get("total_duration"),
                },
            )

        raise RuntimeError(
            f"Ollama no disponible en {self.base_url} tras {self.max_retries + 1} intento(s): {last_error}"
        )

    def _tags(self):
        """GET /api/tags real -- barato, no carga el modelo ni gasta tokens.
        Usado por health()/list_models()/get_capabilities() en vez del
        default generico de AIProvider (que gastaria una llamada real a
        complete(), cara en este hardware -- ver docs/ai/OLLAMA_STATUS.md)."""
        import requests

        resp = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout_s)
        resp.raise_for_status()
        return resp.json().get("models", [])

    def health(self) -> LLMHealth:
        t0 = time.monotonic()
        try:
            models = self._tags()
        except Exception as exc:
            return LLMHealth(
                reachable=False,
                latency_ms=(time.monotonic() - t0) * 1000,
                model_available=False,
                error=str(exc)[:300],
            )
        available = any(m.get("name") == self.model or m.get("model") == self.model for m in models)
        return LLMHealth(
            reachable=True,
            latency_ms=(time.monotonic() - t0) * 1000,
            model_available=available,
            error=None
            if available
            else f"Modelo '{self.model}' no esta instalado en este servidor Ollama.",
        )

    def _capabilities_from_tags(self, entry: dict) -> LLMCapabilities:
        # Mapeo desde el campo real "capabilities" que Ollama reporta por
        # modelo en /api/tags (verificado en vivo: ["completion","vision",
        # "tools","thinking"] para qwen3.5:4b) -- metadata declarada por el
        # servidor, no un capability probe conductual (eso es Fase 2 del
        # plan, no implementado aqui). streaming/structured_output quedan
        # False: son soportados a nivel de PROTOCOLO por Ollama pero este
        # provider todavia no implementa stream() ni structured output real
        # (Regla Absoluta "NO ASUMIR CAPACIDADES" -- no marcar True algo que
        # el codigo no ejercita de verdad).
        caps = entry.get("capabilities") or []
        return LLMCapabilities(
            chat="completion" in caps,
            streaming=False,
            tool_calling="tools" in caps,
            structured_output=False,
            vision="vision" in caps,
            reasoning="thinking" in caps,
            verified=True,
            verified_at=datetime.now(UTC),
        )

    def list_models(self) -> list[LLMModelDescriptor]:
        models = self._tags()
        result = []
        for m in models:
            details = m.get("details") or {}
            result.append(
                LLMModelDescriptor(
                    model_id=m.get("name") or m.get("model") or "",
                    display_name=m.get("name") or "",
                    context_window=details.get("context_length"),
                    max_output_tokens=None,  # Ollama no reporta un limite de salida por modelo.
                    capabilities=self._capabilities_from_tags(m),
                )
            )
        return result

    def get_capabilities(self) -> LLMCapabilities:
        for m in self._tags():
            if m.get("name") == self.model or m.get("model") == self.model:
                return self._capabilities_from_tags(m)
        return LLMCapabilities()  # modelo no instalado -- capacidades vacias, no asumidas.
