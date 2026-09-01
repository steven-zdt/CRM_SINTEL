"""
Fase AI-03 (continuacion): dominio `facturas`, READ-only de forma
explicita y permanente -- nunca se agregara aqui crear/editar/anular ni
transmitir a la DIAN. Esa escritura debe seguir pasando siempre por el
pipeline propietario existente (`FacturaBusinessService.guardar_desde_dto()`
/ `crear_factura_desde_venta()`), nunca por el AI Engine (regla
explicita de la mision, "FASE 21").

Envuelve `FacturaSelectors.qs_list` ya existente. Mismo patron
NULL-safe de sede que `cotizaciones_tools.py`/`gastos_tools.py`/
`proyectos_tools.py` -- `Factura` tampoco tiene campo `area`.
"""
from __future__ import annotations

from apps.services.ai.context import AIContext

from .base import BaseTool, ToolKind, ToolResult, ToolRisk


def _sede_ids_or_none(context: AIContext) -> tuple[int, ...] | None:
    return None if context.alcance == "EMPRESA" else context.sede_ids


class ConsultarFacturaTool(BaseTool):
    name = "consultar_factura"
    description = (
        "Consulta facturas (emitidas o recibidas) del tenant actual, "
        "opcionalmente filtradas por texto (numero, CUFE, razon social "
        "emisor/receptor). Respeta el alcance organizacional de sede "
        "(NULL-safe). Solo lectura -- nunca crea, modifica, anula ni "
        "transmite facturas; esa escritura vive exclusivamente en el "
        "pipeline propietario de Facturas."
    )
    domain = "facturas"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, search: str = "", limit: int = 10) -> ToolResult:
        if limit < 1 or limit > 50:
            return ToolResult(status="VALIDATION_ERROR", message="limit debe estar entre 1 y 50.")

        from apps.tenant.facturas.services.selectors import FacturaSelectors

        qs = FacturaSelectors.qs_list(
            empresa_id=context.empresa_id,
            search=search or None,
            sede_ids=_sede_ids_or_none(context),
        )[:limit]

        facturas = [
            {
                "id": f.id,
                "uuid": str(f.uuid),
                "numero": f.numero,
                "naturaleza": f.naturaleza,
                "estado": f.estado,
                "estado_pago": f.estado_pago,
                "fecha_emision": f.fecha_emision.isoformat() if f.fecha_emision else None,
                "emisor_razon_social": f.emisor_razon_social,
                "receptor_razon_social": f.receptor_razon_social,
                "total": str(f.total),
                "cufe": f.cufe,
                "sede": f.sede.nombre if f.sede_id else None,
            }
            for f in qs
        ]
        return ToolResult(status="OK", data=facturas)
