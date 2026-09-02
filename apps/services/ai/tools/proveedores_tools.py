"""Fase AI-03: dominio `proveedores`, mismo patron que clientes_tools.py."""
from __future__ import annotations

from apps.services.ai.context import AIContext

from ._validation import validar_via_serializer
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


class ValidarProveedorTool(BaseTool):
    """Fase AI-04. Envuelve ProveedorDetailSerializer.is_valid() -- misma
    validacion anti-duplicidad (FASE 4/Zero Trust) que ya corre en el
    endpoint real. Nunca escribe."""

    name = "validar_proveedor"
    description = (
        "Valida si los datos de un proveedor candidato (sin crearlo) "
        "cumplirian las reglas del formulario real: campos requeridos, "
        "formato, y unicidad de tipo+numero de documento en el tenant."
    )
    domain = "proveedores"
    kind = ToolKind.VALIDATE
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, data: dict) -> ToolResult:
        from apps.tenant.proveedores.api.serializers import ProveedorDetailSerializer

        return validar_via_serializer(ProveedorDetailSerializer, context, data)
