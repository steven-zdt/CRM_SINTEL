"""
AI Engine orquestador (Fase 4). Punto unico por el que se ejecuta
cualquier tool -- ni las vistas ni un futuro handler de chat deben
llamar a una tool directamente, siempre pasan por aqui, para que los
feature flags (Fase 63) y el enforcement WRITE (Regla Absoluta 6/26)
sean estructurales y no una convencion que alguien puede olvidar.
"""
from __future__ import annotations

import logging

from django.conf import settings

from apps.services.ai.context import AIContext, PermissionDeniedError, build_context

from ..tools.base import AUTO_APPROVED_KINDS, ToolKind, ToolResult
from ..tools.registry import get_tool

logger = logging.getLogger("ai_engine")


def _flag(name: str, default: bool = False) -> bool:
    """Feature flag server-side (Fase 63) -- nunca controlable desde el request/cliente."""
    return bool(getattr(settings, name, default))


class AIEngine:
    """
    Fachada minima. `run_tool` es la unica forma soportada de ejecutar
    una tool -- construye el contexto real desde el request (nunca
    confia en un empresa_id/tenant que venga en el payload del
    request de IA), verifica flags, y devuelve un ToolResult
    normalizado (nunca un traceback).
    """

    @staticmethod
    def run_tool(tool_name: str, request, *, screen: dict | None = None, **kwargs) -> ToolResult:
        if not _flag("AI_ENABLED"):
            return ToolResult(status="PERMISSION_DENIED", message="AI Engine deshabilitado en este entorno.")

        tool = get_tool(tool_name)
        if tool is None:
            return ToolResult(status="NOT_FOUND", message=f"Tool desconocida: '{tool_name}'.")

        kind_flag = {
            ToolKind.READ: "AI_READ_ENABLED",
            ToolKind.SUGGEST: "AI_SUGGEST_ENABLED",
            ToolKind.VALIDATE: "AI_VALIDATE_ENABLED",
            ToolKind.WRITE: "AI_WRITE_ENABLED",
        }[tool.kind]
        if not _flag(kind_flag):
            return ToolResult(
                status="PERMISSION_DENIED",
                message=f"Herramientas de tipo {tool.kind.value} deshabilitadas en este entorno.",
            )

        # Regla Absoluta 6/7/26: WRITE nunca se auto-aprueba solo porque
        # el flag este activo -- requiere ademas un flujo de aprobacion
        # explicito que hoy NO existe (no hay tools WRITE registradas
        # todavia). Esto es deliberadamente estructural, no una nota en
        # un doc: si alguien registra una tool WRITE en el futuro sin
        # implementar ese flujo, esta linea la bloquea igual.
        if tool.kind not in AUTO_APPROVED_KINDS:
            return ToolResult(
                status="PERMISSION_DENIED",
                message="Las herramientas WRITE requieren un flujo de aprobacion aun no implementado.",
            )

        try:
            context = build_context(request, screen=screen)
        except PermissionDeniedError as exc:
            return ToolResult(status="PERMISSION_DENIED", message=str(exc))

        try:
            result = tool.run(context, **kwargs)
        except Exception:
            # Nunca propagar traceback/SQL/secretos al modelo (Fase 34).
            logger.exception("ai_engine.tool_error tool=%s user=%s empresa=%s", tool_name, context.user_id, context.empresa_id)
            return ToolResult(status="INTERNAL_ERROR", message="Error interno ejecutando la herramienta.")

        logger.info(
            "ai_engine.tool_call tool=%s kind=%s status=%s user=%s empresa=%s",
            tool_name, tool.kind.value, result.status, context.user_id, context.empresa_id,
        )
        return result


def run_tool(tool_name: str, request, **kwargs) -> ToolResult:
    """Atajo funcional -- equivalente a AIEngine.run_tool."""
    return AIEngine.run_tool(tool_name, request, **kwargs)
