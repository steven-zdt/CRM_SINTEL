"""
Tests de Organizational Service Layer (Fase 8, proyecto OCF).

Prueba los helpers de resolucion y el adaptador de demostracion contra
OrdenCompraBusinessService real (compras, ADR-003) - no mocks.
"""
from apps.tenant.compras.models import PlantillaOrdenCompra
from apps.tenant.core.services.organizational_context import OrganizationalContext
from apps.tenant.core.services.organizational_service_layer import (
    crear_orden_compra_desde_contexto,
    resolve_empresa_and_sede,
    resolve_perfil,
)
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class OrganizationalServiceLayerTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase8", nit="900000888", direccion="Calle 1",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Principal")
        self.perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor Fase8", numero_documento="321", tipo_documento="NIT",
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa, nombre="Plantilla Fase8", prefijo="OC8",
            rango_desde=1, rango_hasta=100, consecutivo_actual=1, vigente=True,
        )

    def _context(self) -> OrganizationalContext:
        return OrganizationalContext(
            tenant_schema="test", tenant_id=1, empresa_id=self.empresa.id, sede_id=self.sede.id,
            area_id=None, user_id=self.user.id, perfil_id=self.perfil.id, rol="ADMIN",
            alcance="EMPRESA", timezone="UTC", configuracion={},
        )

    def test_resolve_empresa_and_sede_returns_real_instances(self):
        empresa, sede = resolve_empresa_and_sede(self._context())
        self.assertEqual(empresa.id, self.empresa.id)
        self.assertEqual(sede.id, self.sede.id)

    def test_resolve_empresa_and_sede_returns_none_sede_when_context_has_none(self):
        context = OrganizationalContext(
            tenant_schema="test", tenant_id=1, empresa_id=self.empresa.id, sede_id=None,
            area_id=None, user_id=self.user.id, perfil_id=None, rol="ADMIN",
            alcance="EMPRESA", timezone="UTC", configuracion={},
        )
        empresa, sede = resolve_empresa_and_sede(context)
        self.assertEqual(empresa.id, self.empresa.id)
        self.assertIsNone(sede)

    def test_resolve_perfil_returns_real_tenant_profile(self):
        perfil = resolve_perfil(self._context())
        self.assertEqual(perfil.id, self.perfil.id)
        self.assertEqual(perfil.rol, "ADMIN")

    def test_crear_orden_compra_desde_contexto_creates_real_order_via_existing_business_service(self):
        """Prueba end-to-end: el adaptador de Fase 8 llama al Business
        Service YA EXISTENTE de compras (ADR-003) sin modificarlo, y el
        resultado es una OrdenCompra real, indistinguible de una creada
        llamando directamente crear_orden_compra()."""
        order_data = {
            "plantilla_uuid": str(self.plantilla.uuid),
            "proveedor_uuid": str(self.proveedor.uuid),
            "fecha": "2026-08-07",
            "items": [{"descripcion": "Item Fase8", "cantidad": 2, "valor_unitario": 5000}],
        }
        success, orden, status_code = crear_orden_compra_desde_contexto(
            order_data, order_data["items"], self._context()
        )
        self.assertTrue(success, orden)
        self.assertEqual(status_code, 201)
        self.assertEqual(orden.empresa_id, self.empresa.id)
        self.assertEqual(orden.sede_id, self.sede.id)
