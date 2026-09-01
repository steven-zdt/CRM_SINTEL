"""
Fase AI-03 (continuacion, BLOCKED BY DESIGN -> desbloqueado): dominio
`empleados`, primer dominio sensible del AI Engine. Solo se implementa
despues de que `docs/ai/AI_SECURITY_MODEL.md` §"AI-03 BLOCKED BY DESIGN
-- empleados y bancos" define la clasificacion de campos -- esta tool
DEBE cumplirla, no al reves:

- SAFE (cualquier alcance): nombre completo, cargo, estado, fecha de
  ingreso, sede, area.
- SAFE solo si `context.rol == "ADMIN"`: numero_documento, email,
  telefono (PII identificable).
- FORBIDDEN siempre, sin excepcion de rol: eps/afp/arl/nivel_riesgo_arl
  (dato de salud/afiliacion, sensible bajo Ley 1581 CO), foto
  (archivo binario, fuera de alcance de un ToolResult estructurado).
- Salario/nomina (Contrato/Devengo) NO se expone en esta tool -- fuera
  de alcance deliberado (ver AI_SECURITY_MODEL.md), otra tool si algun
  dia se necesita, nunca mezclada con la busqueda basica de empleados.

`limit` maximo 10 (no 50 como las tools SAFE_READ) -- el radio de
exposicion de un dato sensible en lote es mayor (ver
AI_SECURITY_MODEL.md "Limites de agregacion/busqueda").

Envuelve `EmpleadoSelector.get_list` ya existente (NULL-safe en sede Y
area de forma independiente -- ambos campos existen en el modelo, a
diferencia de cotizaciones/gastos/proyectos/facturas que solo tienen
sede). Usa el mismo patron axis-aware que `compras_tools.py`
(`_scope_kwargs`) en vez del de un solo eje: aplicar la tupla real de
`context.sede_ids`/`area_ids` a AMBOS ejes simultaneamente repetiria el
bug ya encontrado y corregido en `compras_tools.py` (un perfil alcance
SEDE tiene `area_ids=()` por diseno de AIContext, y aplicar eso al eje
de area lo restringiria a "sin area" en vez de dejarlo sin restringir).
"""
from __future__ import annotations

from apps.services.ai.context import AIContext

from .base import BaseTool, ToolKind, ToolResult, ToolRisk


def _scope_kwargs(context: AIContext) -> dict:
    if context.alcance == "SEDE":
        return {"sede_ids": context.sede_ids, "area_ids": None}
    if context.alcance == "AREA":
        return {"sede_ids": None, "area_ids": context.area_ids}
    return {"sede_ids": None, "area_ids": None}


class BuscarEmpleadoTool(BaseTool):
    name = "buscar_empleado"
    description = (
        "Busca empleados del tenant actual por nombre o numero de "
        "documento. Solo lectura. Dato sensible: numero de documento, "
        "email y telefono solo se incluyen si el usuario tiene rol "
        "ADMIN; datos de salud/afiliacion (EPS/AFP/ARL) y salario nunca "
        "se exponen a traves de esta tool."
    )
    domain = "empleados"
    kind = ToolKind.READ
    risk = ToolRisk.SENSITIVE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, search: str = "", limit: int = 10) -> ToolResult:
        if limit < 1 or limit > 10:
            return ToolResult(status="VALIDATION_ERROR", message="limit debe estar entre 1 y 10.")

        from apps.tenant.empleados.services.selectors import EmpleadoSelector

        qs = EmpleadoSelector.get_list(
            empresa_id=context.empresa_id,
            search=search or None,
            **_scope_kwargs(context),
        )[:limit]

        es_admin = context.rol == "ADMIN"
        empleados = []
        for e in qs:
            item = {
                "id": e.id,
                "uuid": str(e.uuid),
                "nombre_completo": " ".join(
                    p for p in (e.primer_nombre, e.segundo_nombre, e.primer_apellido, e.segundo_apellido) if p
                ),
                "cargo": e.cargo,
                "estado": e.estado,
                "fecha_ingreso": e.fecha_ingreso.isoformat() if e.fecha_ingreso else None,
                "sede": e.sede.nombre if e.sede_id else None,
                "area": e.area.nombre if e.area_id else None,
            }
            if es_admin:
                item["numero_documento"] = e.numero_documento
                item["email"] = e.email
                item["telefono"] = e.telefono
            empleados.append(item)

        return ToolResult(status="OK", data=empleados)
