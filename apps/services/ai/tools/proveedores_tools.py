"""Fase AI-03: dominio `proveedores`, mismo patron que clientes_tools.py."""
from __future__ import annotations

from apps.services.ai.context import AIContext

from .base import BaseTool, ToolKind, ToolResult, ToolRisk


class BuscarProveedorTool(BaseTool):
    name = "buscar_proveedor"
    description = (
        "Busca proveedores del tenant actual por razon social, numero de "
        "documento, email o nombre comercial. Solo lectura."
    )
    domain = "proveedores"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, search: str = "", limit: int = 10) -> ToolResult:
        if limit < 1 or limit > 50:
            return ToolResult(status="VALIDATION_ERROR", message="limit debe estar entre 1 y 50.")

        from apps.tenant.proveedores.services.selectors import ProveedorSelector

        qs = ProveedorSelector.get_list(empresa_id=context.empresa_id, search=search or None)[:limit]

        proveedores = [
            {
                "id": p.id,
                "uuid": str(p.uuid),
                "razon_social": p.razon_social,
                "numero_documento": p.numero_documento,
                "tipo_persona": p.tipo_persona,
                "activo": p.activo,
            }
            for p in qs
        ]
        return ToolResult(status="OK", data=proveedores)
