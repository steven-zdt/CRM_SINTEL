from .base import AUTO_APPROVED_KINDS, BaseTool, ToolKind, ToolResult, ToolRisk
from .clientes_tools import BuscarClienteTool
from .ekg_tools import ProjectMapTool
from .inventario_tools import BuscarProductoTool
from .registry import get_tool, list_tools, register_tool, tool_metadata

# Registro real de tools implementadas. Ver docs/ai/AI_TOOL_REGISTRY.md
# para el resto de dominios (diseñados, no implementados todavia).
register_tool(BuscarClienteTool())
register_tool(ProjectMapTool())
register_tool(BuscarProductoTool())

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
