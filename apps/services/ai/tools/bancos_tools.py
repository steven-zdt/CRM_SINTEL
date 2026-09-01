"""
Fase AI-03 (continuacion, BLOCKED BY DESIGN -> desbloqueado): dominio
`bancos`, segundo dominio sensible del AI Engine. Aplica la
clasificacion ya escrita en `docs/ai/AI_SECURITY_MODEL.md` §"AI-03
BLOCKED BY DESIGN -- empleados y bancos":

- SAFE: nombre, banco, tipo.
- MASKED siempre (sin excepcion de rol): `numero` -- nunca el numero
  completo de cuenta, solo los ultimos 4 digitos (`****1234`), igual
  que un extracto o recibo normal muestra al usuario final.
- FORBIDDEN en esta tool: saldos y movimientos (`ExtractoBancario`/
  `TransaccionBancaria`) -- fuera de alcance deliberado, mismo
  criterio que `empleados_tools.py` dejo fuera Contrato/Devengo. Si
  algun dia se necesita, sera otra tool dedicada con su propia
  clasificacion (saldo/valor son FORBIDDEN salvo rol ADMIN segun
  AI_SECURITY_MODEL.md), nunca mezclada con la busqueda basica de
  cuentas.

`CuentaBancaria` no tiene campo sede/area -- el unico filtro real es
`empresa_id` (Zero Trust ya aplicado por el selector).
"""
from __future__ import annotations

from apps.services.ai.context import AIContext

from .base import BaseTool, ToolKind, ToolResult, ToolRisk


def _mask_numero(numero: str) -> str:
    if not numero:
        return numero
    return f"****{numero[-4:]}" if len(numero) > 4 else "****"


class ConsultarCuentaBancariaTool(BaseTool):
    name = "consultar_cuenta_bancaria"
    description = (
        "Consulta cuentas bancarias del tenant actual por nombre, banco "
        "o numero. Solo lectura. El numero de cuenta siempre se "
        "enmascara (solo ultimos 4 digitos); saldos y movimientos no "
        "se exponen a traves de esta tool."
    )
    domain = "bancos"
    kind = ToolKind.READ
    risk = ToolRisk.SENSITIVE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, search: str = "", limit: int = 10) -> ToolResult:
        if limit < 1 or limit > 10:
            return ToolResult(status="VALIDATION_ERROR", message="limit debe estar entre 1 y 10.")

        from apps.tenant.bancos.services.selectors import CuentaBancariaSelector

        qs = CuentaBancariaSelector.get_list(
            empresa_id=context.empresa_id,
            search=search or None,
        )[:limit]

        cuentas = [
            {
                "id": c.id,
                "uuid": str(c.uuid),
                "nombre": c.nombre,
                "banco": c.banco,
                "tipo": c.tipo,
                "numero": _mask_numero(c.numero),
            }
            for c in qs
        ]
        return ToolResult(status="OK", data=cuentas)
