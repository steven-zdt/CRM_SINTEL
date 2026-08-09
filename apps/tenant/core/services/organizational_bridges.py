"""
Organizational Bridges (Fase 7, proyecto OCF).

Ver docs/ADR-004-organizational-context-framework-diseno.md ("OrganizationalBridge")
y documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md.

El pedido original de esta fase dice "Migrar todos los Bridges... No deberan
recibir empresa_id" - pero el proyecto tambien exige explicitamente "Nunca
romper compatibilidad" y "Nunca modificar logica funcional existente". Los 5
bridges reales de facturas (CotizacionBridge, ClienteBridge, ProveedorBridge,
InventarioItemBridge, BancosBridge) tienen 6 consumidores reales hoy
(bancos, proyectos, gastos, empleados, proveedores, contabilidad - ver Fase
0 Anexo A.9) que los llaman con `empresa_id` explicito. Reescribirlos para
que reciban solo OrganizationalContext seria un cambio incompatible para
esos 6 consumidores - exactamente lo que el riesgo de diseno D-2 (ADR-004)
ya advirtio.

Resolucion aplicada, consistente con cada fase anterior de este proyecto:
se construye el contrato `OrganizationalBridge` + ADAPTADORES que envuelven
los bridges reales sin tocarlos - un consumidor nuevo (Fase 9 en adelante)
puede usar `ClienteOrganizationalBridge().get_by_uuid(uuid, context)` sin
pasar empresa_id suelto, mientras los 6 consumidores actuales siguen
llamando `ClienteBridge.obtener_cliente_por_uuid(uuid, empresa_id=X)`
exactamente igual que hoy.

Cobertura honesta:
  - CotizacionBridge, ClienteBridge, ProveedorBridge: adaptados aqui - los
    3 comparten la forma (uuid) -> dict | None + exists_by_uuid(uuid), que
    es exactamente lo que el contrato Protocol pide.
  - InventarioItemBridge (buscar_catalogo/resolver_item) y BancosBridge
    (obtener_total_conciliado, un agregado, no un lookup por uuid) tienen
    una forma distinta - NO encajan en el contrato get_by_uuid/exists sin
    forzarlo. No se adaptan en esta fase; declarados explicitamente en
    _BRIDGES_SIN_ADAPTAR para que quede visible, no oculto.
  - VentasBridge / ComprasBridge: NO existen hoy (Fase 0 confirmo que
    ventas y compras leen otras apps por FK directa + DSV, no por bridge).
    No se fabrican aqui sin una necesidad real que los justifique - ver
    Fase 0 Anexo A.3/A.16. Quedan para cuando Fase 9 migre esas apps y de
    verdad necesiten una lectura inter-app equivalente a un bridge.
"""
from __future__ import annotations

from typing import Any, Protocol

from apps.tenant.core.services.organizational_context import OrganizationalContext


class OrganizationalBridge(Protocol):
    """Contrato (ADR-004) para lectura inter-app via OrganizationalContext."""

    def get_by_uuid(self, uuid: str, context: OrganizationalContext) -> Any | None: ...

    def exists(self, uuid: str, context: OrganizationalContext) -> bool: ...


class CotizacionOrganizationalBridge:
    """Adaptador sobre CotizacionBridge (apps/tenant/facturas/services/selectors.py,
    ya existente, sin modificar)."""

    def get_by_uuid(self, uuid: str, context: OrganizationalContext) -> dict | None:
        from apps.tenant.facturas.services.selectors import CotizacionBridge

        return CotizacionBridge.obtener_cotizacion_por_uuid(uuid, empresa_id=context.empresa_id)

    def exists(self, uuid: str, context: OrganizationalContext) -> bool:
        from apps.tenant.facturas.services.selectors import CotizacionBridge

        return CotizacionBridge.exists_by_uuid(uuid, empresa_id=context.empresa_id)


class ClienteOrganizationalBridge:
    """Adaptador sobre ClienteBridge (apps/tenant/facturas/services/selectors.py,
    ya existente, sin modificar)."""

    def get_by_uuid(self, uuid: str, context: OrganizationalContext) -> dict | None:
        from apps.tenant.facturas.services.selectors import ClienteBridge

        return ClienteBridge.obtener_cliente_por_uuid(uuid, empresa_id=context.empresa_id)

    def exists(self, uuid: str, context: OrganizationalContext) -> bool:
        from apps.tenant.facturas.services.selectors import ClienteBridge

        return ClienteBridge.exists_by_uuid(uuid, empresa_id=context.empresa_id)


class ProveedorOrganizationalBridge:
    """Adaptador sobre ProveedorBridge (apps/tenant/facturas/services/selectors.py,
    ya existente, sin modificar)."""

    def get_by_uuid(self, uuid: str, context: OrganizationalContext) -> dict | None:
        from apps.tenant.facturas.services.selectors import ProveedorBridge

        return ProveedorBridge.obtener_proveedor_por_uuid(uuid, empresa_id=context.empresa_id)

    def exists(self, uuid: str, context: OrganizationalContext) -> bool:
        from apps.tenant.facturas.services.selectors import ProveedorBridge

        return ProveedorBridge.exists_by_uuid(uuid, empresa_id=context.empresa_id)


# Bridges reales que existen pero NO encajan en el contrato get_by_uuid/exists
# sin forzarlo (ver docstring del modulo) - documentados, no adaptados.
_BRIDGES_SIN_ADAPTAR = {
    "InventarioItemBridge": "catalogo/busqueda (buscar_catalogo, resolver_item), no un lookup simple por uuid",
    "BancosBridge": "agregado numerico (obtener_total_conciliado), no un lookup de entidad por uuid",
}

# Bridges pedidos por el nombre en el proyecto original que no existen hoy -
# ver Fase 0 Anexo A.3 (compras) y A.16 (ventas). No fabricados sin una
# necesidad real (Karpathy: no crear infraestructura especulativa).
_BRIDGES_INEXISTENTES = ("VentasBridge", "ComprasBridge")
