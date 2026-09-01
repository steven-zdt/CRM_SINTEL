"""
Fase AI-03.2: segundo dominio READ real (`inventario`), mismo patron
exacto que `clientes_tools.py` -- envuelve `ProductoSelector` ya
existente, no reimplementa la consulta. `stock_actual` ya viene en
`PRODUCTO_LIST_FIELDS` (sin N+1), asi que una sola tool cubre tanto
`buscar_producto` como `consultar_stock` (AI-03.2 las lista como 2
capacidades, no necesariamente 2 tools separadas -- una lista con
stock incluido responde ambas preguntas sin duplicar la query).
"""
from __future__ import annotations

from apps.services.ai.context import AIContext

from .base import BaseTool, ToolKind, ToolResult, ToolRisk


class BuscarProductoTool(BaseTool):
    name = "buscar_producto"
    description = (
        "Busca productos del tenant actual por codigo, nombre o categoria. "
        "Incluye stock_actual (consulta de stock). Solo lectura."
    )
    domain = "inventario"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, search: str = "", limit: int = 10) -> ToolResult:
        if limit < 1 or limit > 50:
            return ToolResult(status="VALIDATION_ERROR", message="limit debe estar entre 1 y 50.")

        from apps.tenant.inventario.services.selectors import ProductoSelector

        qs = ProductoSelector.get_list(empresa_id=context.empresa_id, search=search or None)[:limit]

        productos = [
            {
                "id": p.id,
                "uuid": str(p.uuid),
                "codigo": p.codigo,
                "nombre": p.nombre,
                "categoria": p.categoria.nombre if p.categoria_id else None,
                "stock_actual": str(p.stock_actual),
                "stock_minimo": str(p.stock_minimo),
                "precio_venta": str(p.precio_venta) if p.precio_venta is not None else None,
                "activo": p.activo,
            }
            for p in qs
        ]
        return ToolResult(status="OK", data=productos)
