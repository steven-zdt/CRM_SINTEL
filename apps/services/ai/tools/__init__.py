from .bancos_tools import ConsultarCuentaBancariaTool
from .base import AUTO_APPROVED_KINDS, BaseTool, ToolKind, ToolResult, ToolRisk
from .clientes_tools import BuscarClienteTool, ValidarClienteTool
from .compras_tools import ConsultarCompraTool, ValidarCompraTool
from .contabilidad_tools import SugerirAsientoContableTool
from .cotizaciones_tools import ConsultarCotizacionTool, ValidarCotizacionTool
from .ekg_tools import ProjectMapTool
from .empleados_tools import BuscarEmpleadoTool
from .facturas_tools import ConsultarFacturaTool
from .gastos_tools import ConsultarGastoTool, ValidarGastoTool
from .inventario_tools import BuscarProductoTool, ValidarProductoTool
from .proveedores_tools import BuscarProveedorTool, ValidarProveedorTool
from .proyectos_tools import ConsultarProyectoTool
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
register_tool(ConsultarCotizacionTool())
register_tool(ConsultarGastoTool())
register_tool(ConsultarProyectoTool())
register_tool(ConsultarFacturaTool())
register_tool(BuscarEmpleadoTool())
register_tool(ConsultarCuentaBancariaTool())
register_tool(SugerirAsientoContableTool())

# Fase AI-04 -- Validation Engine (primer lote: dominios sin dependencia
# de un `request` de Django real en su Serializer.validate()).
register_tool(ValidarClienteTool())
register_tool(ValidarProveedorTool())
register_tool(ValidarProductoTool())
register_tool(ValidarCompraTool())
register_tool(ValidarCotizacionTool())
register_tool(ValidarGastoTool())

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
