"""
Primera familia READ real (Fase 13), dominio `clientes`.

Reutiliza ClienteSelector ya existente (apps/tenant/clientes/services/
selectors.py) -- no se reimplementa la consulta, se envuelve. Confirma
el patron Tool -> Selector -> SSoT end-to-end con una sola tool antes
de replicarlo a los demas dominios (ver docs/ai/AI_TOOL_REGISTRY.md
para el resto, deliberadamente no implementado aun).
"""
from __future__ import annotations

from apps.services.ai.context import AIContext

from ._validation import validar_via_serializer
from .base import BaseTool, ToolKind, ToolResult, ToolRisk


class BuscarClienteTool(BaseTool):
    name = "buscar_cliente"
    description = (
        "Busca clientes del tenant actual por razon social, numero de "
        "documento, email o nombre comercial. Solo lectura."
    )
    domain = "clientes"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, search: str = "", limit: int = 10) -> ToolResult:
        if limit < 1 or limit > 50:
            return ToolResult(
                status="VALIDATION_ERROR",
                message="limit debe estar entre 1 y 50.",
            )

        # Import diferido -- evita que apps.services.ai (importable en
        # el proceso de management commands, tests unitarios, etc.)
        # arrastre el arbol completo de apps tenant en modulos que
        # no lo necesitan.
        from apps.tenant.clientes.services.selectors import ClienteSelector

        qs = ClienteSelector.get_cliente_list(
            empresa_id=context.empresa_id,
            search=search or None,
        )[:limit]

        clientes = [
            {
                "id": c.id,
                "uuid": str(c.uuid),
                "razon_social": c.razon_social,
                "numero_documento": c.numero_documento,
                "tipo_persona": c.tipo_persona,
                "activo": c.activo,
            }
            for c in qs
        ]
        return ToolResult(status="OK", data=clientes)


class ValidarClienteTool(BaseTool):
    """Fase AI-04. Envuelve ClienteDetailSerializer.is_valid() -- misma
    validacion (incluida la regla de duplicidad de documento) que ya
    corre en el endpoint real de creacion/edicion. Nunca escribe."""

    name = "validar_cliente"
    description = (
        "Valida si los datos de un cliente candidato (sin crearlo) "
        "cumplirian las reglas del formulario real: campos requeridos, "
        "formato, y unicidad de tipo+numero de documento en el tenant."
    )
    domain = "clientes"
    kind = ToolKind.VALIDATE
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, data: dict) -> ToolResult:
        from apps.tenant.clientes.api.serializers import ClienteDetailSerializer

        return validar_via_serializer(ClienteDetailSerializer, context, data)
