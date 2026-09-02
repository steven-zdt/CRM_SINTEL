"""
Fase AI-03 (continuacion, BLOCKED BY DESIGN -> desbloqueado): dominio
`contabilidad`. Implementa el diseno ya escrito en
`docs/ai/AI_CONTABILIDAD_INTEGRATION.md` (STEP 6) -- ESTA tool NO
reimplementa logica contable: envuelve
`ContabilidadBusinessService.sugerir_lineas_asiento_ia()`, el
Asistente Contable que YA existe en produccion (llama a Anthropic con
su propio cliente/prompt, independiente del AI Engine), expuesto hoy
via `POST /api/v1/contabilidad/pendientes/asistente-ia/`.

"Orquestar, no duplicar" (regla del diseno) significa que esta tool
solo aporta: contexto de tenant real (AIContext, nunca del payload),
el chequeo de rol=ADMIN (que el ViewSet real ya exige via
IsTenantAdminOrReadOnly -- AIEngine.run_tool() no lo aplica
estructuralmente, ver AI_SECURITY_MODEL.md), y traduccion de
ValidationError a ToolResult. El prompt, la validacion de cuentas
nivel-6 activas y la validacion debe==haber quedan intactas dentro de
business_service.py, sin tocarlas.

kind=SUGGEST (nunca escribe un AsientoContable -- esa persistencia
sigue perteneciendo exclusivamente a contabilizar_documento_manual(),
un flujo de confirmacion humana fuera de alcance de esta tool).
"""
from __future__ import annotations

from apps.services.ai.context import AIContext

from .base import BaseTool, ToolKind, ToolResult, ToolRisk

_APP_LABELS_VALIDOS = {"facturas", "gastos", "empleados", "inventario"}


class SugerirAsientoContableTool(BaseTool):
    name = "sugerir_asiento_contable"
    description = (
        "Sugiere las lineas de un asiento contable en partida doble para "
        "un documento pendiente (factura, gasto, nomina o movimiento de "
        "inventario), usando el Asistente Contable ya existente. Nunca "
        "escribe el asiento -- solo sugiere, requiere confirmacion humana "
        "en el flujo contable real. Requiere rol ADMIN."
    )
    domain = "contabilidad"
    kind = ToolKind.SUGGEST
    risk = ToolRisk.SENSITIVE_READ
    confirmation_required = True
    idempotent = True

    def run(
        self,
        context: AIContext,
        *,
        app_label: str,
        subtotal: str,
        total: str,
        numero: str = "",
        impuestos: str = "0",
        tercero_nit: str = "",
        tercero_nombre: str = "",
    ) -> ToolResult:
        if context.rol != "ADMIN":
            return ToolResult(
                status="PERMISSION_DENIED",
                message="Sugerir asientos contables requiere rol ADMIN.",
            )

        if app_label not in _APP_LABELS_VALIDOS:
            return ToolResult(
                status="VALIDATION_ERROR",
                message=f"app_label debe ser uno de: {sorted(_APP_LABELS_VALIDOS)}.",
            )

        from rest_framework.exceptions import ValidationError as DRFValidationError

        from apps.tenant.contabilidad.services.business_service import ContabilidadBusinessService

        ctx = {
            "numero": numero,
            "subtotal": subtotal,
            "impuestos": impuestos,
            "total": total,
            "tercero_nit": tercero_nit,
            "tercero_nombre": tercero_nombre,
        }

        try:
            lineas = ContabilidadBusinessService().sugerir_lineas_asiento_ia(
                empresa_id=context.empresa_id, app_label=app_label, ctx=ctx,
            )
        except DRFValidationError as exc:
            detail = exc.detail
            message = "; ".join(str(v) for v in detail.values()) if isinstance(detail, dict) else str(detail)
            return ToolResult(status="VALIDATION_ERROR", message=message)

        return ToolResult(status="OK", data=lineas)
