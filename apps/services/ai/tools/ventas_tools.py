"""Fase AI-03.4: dominio `ventas`, envuelve VentaSelector ya existente."""
from __future__ import annotations

from apps.services.ai.context import AIContext

from .base import BaseTool, ToolKind, ToolResult, ToolRisk


class ConsultarVentaTool(BaseTool):
    name = "consultar_venta"
    description = (
        "Consulta ventas del tenant actual, opcionalmente filtradas por "
        "estado o por texto (cliente, numero de factura, observaciones). "
        "Solo lectura."
    )
    domain = "ventas"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, search: str = "", estado: str = "", limit: int = 10) -> ToolResult:
        if limit < 1 or limit > 50:
            return ToolResult(status="VALIDATION_ERROR", message="limit debe estar entre 1 y 50.")

        from apps.tenant.ventas.services.selectors import VentaSelector

        qs = VentaSelector.get_list(
            empresa_id=context.empresa_id, search=search or None, estado=estado or None,
        )[:limit]

        ventas = [
            {
                "id": v.id,
                "uuid": str(v.uuid),
                "estado": v.estado,
                "fecha_emision": v.fecha_emision.isoformat() if v.fecha_emision else None,
                "cliente": v.cliente.razon_social if v.cliente_id else None,
                "subtotal": str(v.subtotal),
                "total_neto": str(v.total_neto),
                "numero_factura": v.numero_factura,
            }
            for v in qs
        ]
        return ToolResult(status="OK", data=ventas)
