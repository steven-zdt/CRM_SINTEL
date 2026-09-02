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

from ._validation import validar_via_serializer
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


class ValidarProductoTool(BaseTool):
    """Fase AI-04. Envuelve ProductoDetailSerializer.is_valid() -- valida
    campos requeridos/formato y que `categoria` pertenezca al tenant y
    sea aplicable a productos (`validate_categoria`, ya existente).

    Limitacion real, verificada leyendo el modelo (no asumida): la
    unicidad de `codigo` por empresa usa un `UniqueConstraint` sobre
    `Lower('codigo')` (`apps/tenant/inventario/models.py`, constraint
    `unique_producto_codigo_per_empresa`) -- DRF no genera un
    validador automatico para constraints con expresiones (`Lower()`),
    solo para campos simples. Esta tool NO detecta un codigo duplicado
    de antemano -- eso solo se descubre en el `.save()` real (fuera de
    alcance de una tool VALIDATE, que nunca escribe)."""

    name = "validar_producto"
    description = (
        "Valida si los datos de un producto candidato (sin crearlo) "
        "cumplirian las reglas del formulario real: campos requeridos, "
        "formato, y que la categoria pertenezca al tenant. No detecta "
        "codigo duplicado (esa constraint solo se verifica al guardar)."
    )
    domain = "inventario"
    kind = ToolKind.VALIDATE
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, data: dict) -> ToolResult:
        from apps.tenant.inventario.api.serializers import ProductoDetailSerializer

        return validar_via_serializer(ProductoDetailSerializer, context, data)
