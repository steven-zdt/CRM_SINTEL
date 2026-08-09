"""
Organizational Service Layer (Fase 8, proyecto OCF).

Ver docs/ADR-004-organizational-context-framework-diseno.md y
documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md.

El pedido dice "Todos los BusinessService deberan aceptar OrganizationalContext.
Nunca empresa_id/sede_id/usuario por separado" - pero reescribir las firmas de
los Business Service ya existentes en las 17 apps romperia cada ViewSet, cada
test y cada llamador actual (Fase 0 confirmo que 14/17 ya reciben `empresa`/
`empresa_id` explicito de forma consistente - no es un problema a resolver
"reescribiendo", es un problema de FALTA de una via alternativa que acepte
el contexto empaquetado). Mismo criterio que Fase 7 (Bridges): contrato +
adaptador, no reescritura.

Este modulo provee:
  1. Helpers de resolucion (`resolve_empresa_and_sede`, `resolve_perfil`) -
     convierten un OrganizationalContext en las instancias reales
     (Empresa, Sede, TenantProfile) que un Business Service YA espera
     recibir como objetos, no como ids sueltos.
  2. UN adaptador concreto de demostracion sobre el Business Service ya
     migrado en ADR-003 (`OrdenCompraBusinessService.crear_orden_compra`,
     compras) - prueba que el patron funciona end-to-end contra codigo
     real, sin modificar ese Business Service.
Las otras 16 apps reciben el mismo tratamiento en Fase 9 (migracion app por
app), no aqui - construir 17 adaptadores sin que ninguna fase futura los
haya pedido todavia seria infraestructura especulativa.
"""
from __future__ import annotations

from typing import Any

from apps.tenant.core.services.organizational_context import OrganizationalContext


def resolve_empresa_and_sede(context: OrganizationalContext) -> tuple[Any, Any | None]:
    """Resuelve las instancias reales Empresa/Sede desde un
    OrganizationalContext. `sede` es None si `context.sede_id` es None
    (empresa aun sin ninguna Sede - mismo caso borde ya manejado desde
    ADR-003)."""
    from apps.tenant.empresa.models import Empresa, Sede

    empresa = Empresa.objects.get(id=context.empresa_id)
    sede = Sede.objects.filter(id=context.sede_id).first() if context.sede_id else None
    return empresa, sede


def resolve_perfil(context: OrganizationalContext):
    """Resuelve el TenantProfile ("usuario" en terminos del Service Layer,
    ver Fase 0: gastos.anular_gasto(..., usuario, ...) recibe un perfil, no
    un id suelto) desde un OrganizationalContext. Retorna None si el
    contexto no tiene perfil_id (ej. fallback DEBUG sin TenantProfile)."""
    if context.perfil_id is None:
        return None
    from apps.tenant.perfil.models import TenantProfile

    return TenantProfile.objects.filter(id=context.perfil_id).first()


def crear_orden_compra_desde_contexto(data: dict, items_data: list, context: OrganizationalContext):
    """Adaptador de demostracion (Fase 8) sobre
    OrdenCompraBusinessService.crear_orden_compra (apps/tenant/compras/
    services/business_service.py, ya existente desde ADR-003, sin
    modificar) - acepta OrganizationalContext en vez de empresa/sede
    sueltos, resolviendo las instancias reales con resolve_empresa_and_sede().
    """
    from apps.tenant.compras.services.business_service import OrdenCompraBusinessService

    empresa, sede = resolve_empresa_and_sede(context)
    return OrdenCompraBusinessService.crear_orden_compra(data, items_data, empresa, sede)
