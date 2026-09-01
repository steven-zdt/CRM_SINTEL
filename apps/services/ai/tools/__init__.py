from .base import AUTO_APPROVED_KINDS, BaseTool, ToolKind, ToolResult, ToolRisk
from .clientes_tools import BuscarClienteTool
from .compras_tools import ConsultarCompraTool
from .ekg_tools import ProjectMapTool
from .inventario_tools import BuscarProductoTool
from .proveedores_tools import BuscarProveedorTool
from .registry import get_tool, list_tools, register_tool, tool_metadata
from .ventas_tools import ConsultarVentaTool

# Registro real de tools implementadas. Ver docs/ai/AI_TOOL_REGISTRY.md
# para el resto de dominios (diseñados, no implementados todavia).
register_tool(BuscarClienteTool())
register_tool(ProjectMapTool())
register_tool(BuscarProductoTool())
register_tool(BuscarProveedorTool())
register_tool(ConsultarVentaTool())
register_tool(ConsultarCompraTool())

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
