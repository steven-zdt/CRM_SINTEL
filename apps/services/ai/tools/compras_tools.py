"""
Fase AI-03.5: dominio `compras`, envuelve OrdenCompraSelector ya
existente -- primer tool que respeta alcance organizacional real
(sede/area), no solo empresa_id (Regla 4: "Toda accion debe respetar
Tenant/Empresa/Sede/Area cuando corresponda").

Nota de semantica real (verificada leyendo
apps/tenant/core/services/organizational_filters.py::filter_by_scope):
`sede_ids=None` significa "sin restriccion" en ESE eje;
`sede_ids=()` (tupla vacia, NO None) significa "restringir a nada" en
ESE eje (alcance SEDE sin ninguna sede asignada -- debe ver 0
resultados, nunca todos).

Bug real encontrado y corregido durante el desarrollo (no solo una
nota teorica -- fallaba en la practica): el alcance de un perfil es UN
solo eje a la vez (EMPRESA, SEDE o AREA, ver
AlcanceOrganizacional/apps/tenant/perfil/models.py), nunca ambos sede Y
area restringidos simultaneamente. Un usuario con alcance=SEDE tiene
`AIContext.area_ids == ()` (nunca se puebla, ver build_context) --
pasar ese `()` tal cual a `area_ids` de filter_by_scope lo interpreta
como "restringir a NINGUNA area", dejando al usuario sin resultados
aunque su sede si sea correcta. La traduccion debe ser POR EJE segun
cual sea el alcance real, no una regla global "EMPRESA=None,
cualquier-otra-cosa=tal-cual".
"""
from __future__ import annotations

from apps.services.ai.context import AIContext

from .base import BaseTool, ToolKind, ToolResult, ToolRisk


def _scope_kwargs(context: AIContext) -> dict:
    """
    Traduce AIContext a los kwargs reales de filter_by_scope, eje por eje:
    - alcance=EMPRESA  -> sede_ids=None,          area_ids=None          (sin restriccion en ningun eje)
    - alcance=SEDE     -> sede_ids=context.sede_ids (incluso vacia),  area_ids=None (no aplica ese eje)
    - alcance=AREA     -> sede_ids=None (no aplica ese eje),  area_ids=context.area_ids (incluso vacia)
    """
    if context.alcance == "SEDE":
        return {"sede_ids": context.sede_ids, "area_ids": None}
    if context.alcance == "AREA":
        return {"sede_ids": None, "area_ids": context.area_ids}
    return {"sede_ids": None, "area_ids": None}


class ConsultarCompraTool(BaseTool):
    name = "consultar_compra"
    description = (
        "Consulta ordenes de compra del tenant actual, opcionalmente "
        "filtradas por estado o por texto (proveedor, consecutivo, "
        "observaciones). Respeta el alcance organizacional (sede/area) "
        "del usuario. Solo lectura."
    )
    domain = "compras"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, search: str = "", estado: str = "", limit: int = 10) -> ToolResult:
        if limit < 1 or limit > 50:
            return ToolResult(status="VALIDATION_ERROR", message="limit debe estar entre 1 y 50.")

        from apps.tenant.compras.services.selectors import OrdenCompraSelector

        qs = OrdenCompraSelector.get_list(
            empresa_id=context.empresa_id,
            search=search or None,
            estado=estado or None,
            **_scope_kwargs(context),
        )[:limit]

        ordenes = [
            {
                "id": o.id,
                "uuid": str(o.uuid),
                "estado": o.estado,
                "consecutivo": o.consecutivo,
                "proveedor": o.proveedor.razon_social if o.proveedor_id else None,
                "sede": o.sede.nombre if o.sede_id else None,
            }
            for o in qs
        ]
        return ToolResult(status="OK", data=ordenes)
