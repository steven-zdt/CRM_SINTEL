"""
Fase AI-03 (continuacion): dominio `proyectos`, envuelve
`apps.tenant.proyectos.services.selectors.qs_list` ya existente. Mismo
patron NULL-safe de sede que `cotizaciones_tools.py`/`gastos_tools.py`.
"""
from __future__ import annotations

from apps.services.ai.context import AIContext

from .base import BaseTool, ToolKind, ToolResult, ToolRisk


def _sede_ids_or_none(context: AIContext) -> tuple[int, ...] | None:
    return None if context.alcance == "EMPRESA" else context.sede_ids


class ConsultarProyectoTool(BaseTool):
    name = "consultar_proyecto"
    description = (
        "Consulta proyectos del tenant actual, opcionalmente filtrados "
        "por fase o por texto (nombre, codigo, cliente, responsable). "
        "Respeta el alcance organizacional de sede (NULL-safe). Solo "
        "lectura."
    )
    domain = "proyectos"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, search: str = "", fase: str = "", limit: int = 10) -> ToolResult:
        if limit < 1 or limit > 50:
            return ToolResult(status="VALIDATION_ERROR", message="limit debe estar entre 1 y 50.")

        from apps.tenant.proyectos.services.selectors import qs_list

        qs = qs_list(
            empresa_id=context.empresa_id,
            search=search or None,
            fase=fase or None,
            sede_ids=_sede_ids_or_none(context),
        )[:limit]

        proyectos = [
            {
                "id": p.id,
                "uuid": str(p.uuid),
                "codigo": p.codigo,
                "nombre": p.nombre,
                "fase_actual": p.fase_actual,
                "estado_tarea": p.estado_tarea,
                "cliente": p.cliente_nombre,
                "responsable": p.responsable_actual_nombre,
                "porcentaje_avance": str(p.porcentaje_avance) if p.porcentaje_avance is not None else None,
                "sede": p.sede.nombre if p.sede_id else None,
            }
            for p in qs
        ]
        return ToolResult(status="OK", data=proyectos)
