"""
Punto de entrada unico del AI Engine para HTTP (/api/v1/ai/ask/, ver
apps/services/ai/api/viewsets.py). Router (Fase 6, docs/adk/ADK_STATUS.md):
dispatcha al agente ADK (LM Studio local) cuando AI_ADK_ENABLED=true, o al
Form Assistant existente basado en Anthropic (form_assistant.py) en caso
contrario -- mismo contrato de respuesta en ambos casos
({"status", "tool_used", "data", "message"}), la vista no necesita saber
cual de los dos respondio.
"""

from __future__ import annotations

from django.conf import settings

from .form_assistant import ask as _ask_anthropic


def ask(request, message: str, *, screen: dict | None = None) -> dict:
    if bool(getattr(settings, "AI_ADK_ENABLED", False)):
        from .adk_router import ask as _ask_adk

        return _ask_adk(request, message, screen=screen)
    return _ask_anthropic(request, message, screen=screen)


__all__ = ["ask"]
