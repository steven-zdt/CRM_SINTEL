"""
Tests de Organizational Bridges (Fase 7, proyecto OCF).

Prueba los 3 adaptadores contra los bridges REALES de facturas
(apps/tenant/facturas/services/selectors.py, sin modificar) y contra
entidades reales de clientes/proveedores/cotizaciones - no mocks.
"""
from apps.tenant.clientes.models import Cliente
from apps.tenant.core.services.organizational_bridges import (
    ClienteOrganizationalBridge,
    ProveedorOrganizationalBridge,
)
from apps.tenant.core.services.organizational_context import OrganizationalContext
from apps.tenant.empresa.models import Empresa
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


def _context(empresa_id) -> OrganizationalContext:
    return OrganizationalContext(
        tenant_schema="test", tenant_id=1, empresa_id=empresa_id, sede_id=None, area_id=None,
        user_id=1, perfil_id=1, rol="OPERADOR", alcance="EMPRESA", timezone="UTC", configuracion={},
    )


class OrganizationalBridgesTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase7", nit="900000777", direccion="Calle 1",
        )
        self.otra_empresa_id = self.empresa.id + 999_999
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="800111222", razon_social="Cliente Bridges S.A.S.", regimen_tributario="ORDINARIO",
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor Bridges", numero_documento="789", tipo_documento="NIT",
        )

    def test_cliente_organizational_bridge_finds_real_cliente(self):
        bridge = ClienteOrganizationalBridge()
        context = _context(self.empresa.id)
        data = bridge.get_by_uuid(str(self.cliente.uuid), context)
        self.assertIsNotNone(data)
        self.assertEqual(data["razon_social"], "Cliente Bridges S.A.S.")
        self.assertTrue(bridge.exists(str(self.cliente.uuid), context))

    def test_cliente_organizational_bridge_respects_empresa_dsv(self):
        """El adaptador debe seguir aplicando el mismo DSV que ya hace
        ClienteBridge - un context de otra empresa no debe encontrar nada."""
        bridge = ClienteOrganizationalBridge()
        context_otra_empresa = _context(self.otra_empresa_id)
        self.assertIsNone(bridge.get_by_uuid(str(self.cliente.uuid), context_otra_empresa))
        self.assertFalse(bridge.exists(str(self.cliente.uuid), context_otra_empresa))

    def test_proveedor_organizational_bridge_finds_real_proveedor(self):
        bridge = ProveedorOrganizationalBridge()
        context = _context(self.empresa.id)
        data = bridge.get_by_uuid(str(self.proveedor.uuid), context)
        self.assertIsNotNone(data)
        self.assertTrue(bridge.exists(str(self.proveedor.uuid), context))

    def test_underlying_facturas_bridges_are_untouched(self):
        """El adaptador no debe reemplazar ni envolver de forma destructiva
        los bridges reales - siguen siendo llamables exactamente igual que
        antes de esta fase (mismo import, misma firma con empresa_id)."""
        from apps.tenant.facturas.services.selectors import ClienteBridge

        data = ClienteBridge.obtener_cliente_por_uuid(str(self.cliente.uuid), empresa_id=self.empresa.id)
        self.assertIsNotNone(data)
        self.assertEqual(data["razon_social"], "Cliente Bridges S.A.S.")
