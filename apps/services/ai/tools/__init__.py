from .base import AUTO_APPROVED_KINDS, BaseTool, ToolKind, ToolResult, ToolRisk
from .clientes_tools import BuscarClienteTool
from .registry import get_tool, list_tools, register_tool, tool_metadata

# Registro real de tools implementadas (Fase 12-13). Deliberadamente
# UNA sola tool por ahora -- ver docs/ai/AI_TOOL_REGISTRY.md para el
# resto de dominios (diseñados, no implementados todavia).
register_tool(BuscarClienteTool())

__all__ = [
    "AUTO_APPROVED_KINDS",
    "BaseTool",
    "ToolKind",
    "ToolResult",
    "ToolRisk",
    "get_tool",
    "list_tools",
    "register_tool",
    "tool_metadata",
]
