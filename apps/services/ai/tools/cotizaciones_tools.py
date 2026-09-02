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

from ._validation import validar_via_serializer
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


class ValidarCotizacionTool(BaseTool):
    """Fase AI-04. Envuelve CotizacionSerializer.is_valid() -- el
    serializer real de escritura. A diferencia de los demas dominios,
    su `__init__`/`validate()` leen `context['empresa']` (instancia real
    de `Empresa`, no `empresa_id`) para acotar los querysets de
    `cliente`/`configuracion`/`sede` y para el chequeo anti-IDOR de
    sede -- se resuelve aqui via una consulta minima (`Empresa` es
    singleton por schema tenant, `.only('id')` ya alcanza).

    Caveat real (verificado leyendo el codigo, mismo que gastos): el
    chequeo de alcance organizacional de sede
    (`sede_esta_en_alcance()`) requiere un `request` de Django real y
    degrada a "permitido" sin uno -- comportamiento documentado de esa
    funcion, no un bug de esta tool. Esta tool SI reproduce el chequeo
    anti-IDOR de "la sede pertenece a esta empresa"."""

    name = "validar_cotizacion"
    description = (
        "Valida si los datos de una cotizacion candidata (sin crearla) "
        "cumplirian las reglas del formulario real: campos requeridos, "
        "formato, y que cliente/configuracion/sede pertenezcan al "
        "tenant."
    )
    domain = "cotizaciones"
    kind = ToolKind.VALIDATE
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, data: dict) -> ToolResult:
        from apps.tenant.cotizaciones.api.serializers import CotizacionSerializer
        from apps.tenant.empresa.models import Empresa

        empresa = Empresa.objects.only("id").get(id=context.empresa_id)
        return validar_via_serializer(CotizacionSerializer, context, data, extra_context={"empresa": empresa})
