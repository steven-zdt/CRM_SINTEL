"""
Implementacion GENERICA del contrato AIProvider para cualquier endpoint REST
que hable el formato de OpenAI Chat Completions -- la convencion de facto
que usan Gemini (endpoint OpenAI-compat oficial de Google), Groq, OpenRouter,
Together.ai, vLLM, llama.cpp server, LM Studio, y practicamente cualquier
proveedor nuevo que aparezca en el futuro.

Garantia real (no solo documentada) de que este proyecto nunca queda atado
a un solo proveedor de LLM: agregar un proveedor REST/API-key nuevo NO
requiere escribir codigo -- solo 3 variables de entorno
(AI_OPENAI_COMPAT_BASE_URL/API_KEY/MODEL). Solo si un proveedor nuevo habla
un protocolo genuinamente distinto (no OpenAI-compat, ej. el /api/chat nativo
de Ollama) hace falta un provider propio -- ver ollama_provider.py como
ejemplo de ese caso.

Ver docs/ai/AI_PROVIDER_MATRIX.md para la lista de proveedores reales y el
contrato de extension completo.
"""

from __future__ import annotations

import os

from .base import AIProvider, AIResponse

DEFAULT_TIMEOUT_S = 120
DEFAULT_MAX_RETRIES = 1


class OpenAICompatibleProvider(AIProvider):
    name = "openai_compatible"

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        *,
        timeout_s: float | None = None,
        max_retries: int | None = None,
    ):
        self.base_url = (base_url or os.environ.get("AI_OPENAI_COMPAT_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("AI_OPENAI_COMPAT_API_KEY", "")
        self.model = model or os.environ.get("AI_OPENAI_COMPAT_MODEL", "")
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
        if not self.base_url:
            raise RuntimeError(
                "AI_OPENAI_COMPAT_BASE_URL no configurada en el entorno del servidor."
            )
        if not self.model:
            raise RuntimeError("AI_OPENAI_COMPAT_MODEL no configurado en el entorno del servidor.")
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("Paquete 'requests' no instalado.") from exc

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens,
        }

        last_error: Exception | None = None
        for _attempt in range(self.max_retries + 1):
            try:
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout_s,
                )
            except requests.exceptions.RequestException as exc:
                last_error = exc
                continue

            if not resp.ok:
                last_error = RuntimeError(
                    f"{self.base_url} respondio {resp.status_code}: {resp.text[:300]}"
                )
                continue

            data = resp.json()
            choice = (data.get("choices") or [{}])[0]
            text = (choice.get("message") or {}).get("content", "")
            usage = data.get("usage") or {}
            return AIResponse(
                text=text,
                model=data.get("model", self.model),
                provider=self.name,
                input_tokens=usage.get("prompt_tokens", 0) or 0,
                output_tokens=usage.get("completion_tokens", 0) or 0,
                raw={"finish_reason": choice.get("finish_reason")},
            )

        raise RuntimeError(
            f"{self.base_url} no disponible tras {self.max_retries + 1} intento(s): {last_error}"
        )
