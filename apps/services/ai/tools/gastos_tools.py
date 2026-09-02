"""
Fase AI-03 (continuacion): dominio `gastos`, envuelve DocumentoSelector
ya existente (DocumentoSoporte -- unifica lo que el usuario final llama
"gastos"). Mismo patron NULL-safe de sede que `cotizaciones_tools.py` --
ver esa nota para el detalle de por que alcance AREA se traduce como
`context.sede_ids` (siempre `()` para un perfil AREA, restringe a solo
NULL hoy, correctamente restrictivo cuando existan registros con sede
real).
"""
from __future__ import annotations

from apps.services.ai.context import AIContext

from ._validation import validar_via_serializer
from .base import BaseTool, ToolKind, ToolResult, ToolRisk


def _sede_ids_or_none(context: AIContext) -> tuple[int, ...] | None:
    return None if context.alcance == "EMPRESA" else context.sede_ids


class ConsultarGastoTool(BaseTool):
    name = "consultar_gasto"
    description = (
        "Consulta documentos soporte (gastos) del tenant actual, "
        "opcionalmente filtrados por texto (proveedor, descripcion, "
        "numero de documento). Respeta el alcance organizacional de sede "
        "(NULL-safe). Solo lectura."
    )
    domain = "gastos"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, search: str = "", limit: int = 10) -> ToolResult:
        if limit < 1 or limit > 50:
            return ToolResult(status="VALIDATION_ERROR", message="limit debe estar entre 1 y 50.")

        from apps.tenant.gastos.services.selectors import DocumentoSelector

        qs = DocumentoSelector.get_list(
            empresa_id=context.empresa_id,
            search=search or None,
            sede_ids=_sede_ids_or_none(context),
        )[:limit]

        documentos = [
            {
                "id": d.id,
                "uuid": str(d.uuid),
                "consecutivo": d.consecutivo,
                "fecha": d.fecha.isoformat() if d.fecha else None,
                "categoria_contable": d.categoria_contable,
                "descripcion": d.descripcion,
                "total": str(d.total),
                "proveedor": d.proveedor.razon_social if d.proveedor_id else None,
                "sede": d.sede.nombre if d.sede_id else None,
            }
            for d in qs
        ]
        return ToolResult(status="OK", data=documentos)


class ValidarGastoTool(BaseTool):
    """Fase AI-04. Envuelve GastoDetailSerializer.is_valid() (alias real
    de DocumentoSoporteDetailSerializer, usado tal cual por el endpoint
    real de creacion -- verificado en el ViewSet). Valida que, si se
    incluye `sede`, pertenezca a la empresa del tenant.

    Caveat real e IMPORTANTE (verificado leyendo `Meta.read_only_fields`
    de `DocumentoSoporteDetailSerializer`): `resolucion_dian`,
    `subtotal`, `total` y varios campos financieros mas son
    `read_only` en este serializer -- el endpoint real los calcula/
    asigna en `business_service.py`, nunca los recibe directo del
    payload. Esto significa que "valid: True" de esta tool NO garantiza
    que esos campos financieros sean correctos ni que existan --
    solo valida lo que el serializer realmente controla: `proveedor`
    (requerido) y, si se incluye, que `sede` pertenezca al tenant.

    Caveat adicional (mismo patron que cotizaciones -- ver
    cotizaciones_tools.py): la verificacion de alcance organizacional
    de sede (`sede_esta_en_alcance()`) requiere un `request` de Django
    real y degrada a "permitido" sin uno (comportamiento documentado
    de la funcion, no un bug) -- esta tool no la reproduce, solo la
    verificacion anti-IDOR de que la sede pertenece a la empresa."""

    name = "validar_gasto"
    description = (
        "Valida si los datos de un documento soporte (gasto) candidato "
        "(sin crearlo) cumplirian las reglas del formulario real. "
        "NOTA: subtotal/total/resolucion_dian son read-only en este "
        "serializer (los calcula el business service, no esta tool) -- "
        "solo valida proveedor (requerido) y que la sede (si se "
        "incluye) pertenezca al tenant."
    )
    domain = "gastos"
    kind = ToolKind.VALIDATE
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, data: dict) -> ToolResult:
        from apps.tenant.gastos.api.serializers import GastoDetailSerializer

        return validar_via_serializer(GastoDetailSerializer, context, data)
