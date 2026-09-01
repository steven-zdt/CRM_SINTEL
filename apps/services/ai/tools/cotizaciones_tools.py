"""
Fase AI-03 (continuacion): dominio `cotizaciones`, envuelve
CotizacionSelector ya existente.

`CotizacionSelector.get_list(sede_ids=...)` ya es NULL-safe por diseno
(OSF Fase F7, apps/tenant/cotizaciones/services/selectors.py): con
`sede_ids=None` no restringe; con una tupla restringe a esas sedes MAS
los registros con `sede_id=NULL` (100% de las Cotizacion reales hoy,
el campo era puramente informativo). Cotizacion no tiene campo `area`
-- para alcance AREA no hay eje de area que aplicar en este modelo, asi
que se restringe por `context.sede_ids` igual que alcance SEDE (que
para un perfil AREA siempre es `()`, ver AIContext.build_context):
resultado NULL-safe correcto hoy (toda la data real es NULL) y
correctamente restrictivo el dia que existan Cotizacion con sede real
asignada.
"""
from __future__ import annotations

from apps.services.ai.context import AIContext

from .base import BaseTool, ToolKind, ToolResult, ToolRisk


def _sede_ids_or_none(context: AIContext) -> tuple[int, ...] | None:
    return None if context.alcance == "EMPRESA" else context.sede_ids


class ConsultarCotizacionTool(BaseTool):
    name = "consultar_cotizacion"
    description = (
        "Consulta cotizaciones del tenant actual, opcionalmente filtradas "
        "por estado o por texto (numero de cotizacion, cliente). Respeta "
        "el alcance organizacional de sede (NULL-safe: incluye tambien las "
        "cotizaciones sin sede asignada). Solo lectura."
    )
    domain = "cotizaciones"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, search: str = "", estado: str = "", limit: int = 10) -> ToolResult:
        if limit < 1 or limit > 50:
            return ToolResult(status="VALIDATION_ERROR", message="limit debe estar entre 1 y 50.")

        from apps.tenant.cotizaciones.services.selectors import CotizacionSelector

        qs = CotizacionSelector.get_list(
            empresa_id=context.empresa_id,
            search=search or None,
            estado=estado or None,
            sede_ids=_sede_ids_or_none(context),
        )[:limit]

        cotizaciones = [
            {
                "id": c.id,
                "uuid": str(c.uuid),
                "numero_cotizacion": c.numero_cotizacion,
                "estado": c.estado,
                "fecha_emision": c.fecha_emision.isoformat() if c.fecha_emision else None,
                "cliente": c.cliente.razon_social if c.cliente_id else None,
                "total_con_impuestos": str(c.total_con_impuestos),
                "sede": c.sede.nombre if c.sede_id else None,
            }
            for c in qs
        ]
        return ToolResult(status="OK", data=cotizaciones)
