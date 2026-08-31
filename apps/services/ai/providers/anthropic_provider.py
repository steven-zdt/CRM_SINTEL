"""
Implementacion Anthropic del contrato AIProvider (Fase 5/6).

Reutiliza el mismo patron ya usado en produccion por el Asistente
Contable (apps/tenant/contabilidad/services/business_service.py::
sugerir_lineas_asiento_ia) -- mismo SDK, misma forma de leer la API
key -- en vez de reinventar una segunda forma de llamar a Anthropic.
"""
from __future__ import annotations

import os

from .base import AIProvider, AIResponse

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        # AI_API_KEY es el nombre generico (Fase 6); ANTHROPIC_API_KEY se
        # mantiene como fallback porque el Asistente Contable ya lo usa --
        # no se pide reconfigurar un despliegue existente para adoptar esto.
        self.api_key = api_key or os.environ.get("AI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model or os.environ.get("AI_MODEL", DEFAULT_MODEL)

    def complete(self, system: str, user_message: str, *, max_tokens: int = 1024) -> AIResponse:
        if not self.api_key:
            raise RuntimeError(
                "AI_API_KEY / ANTHROPIC_API_KEY no configurada en el entorno del servidor."
            )
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError("Paquete 'anthropic' no instalado.") from exc

        client = anthropic.Anthropic(api_key=self.api_key)
        message = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        text = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        )
        usage = getattr(message, "usage", None)
        return AIResponse(
            text=text,
            model=self.model,
            provider=self.name,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
            raw={"id": getattr(message, "id", None), "stop_reason": getattr(message, "stop_reason", None)},
        )
