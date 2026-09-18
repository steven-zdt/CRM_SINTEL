"""
FACTURAS-UI-CRONO-01: vinculacion MANUAL de una Factura ya existente
(naturaleza VENTA) a una Venta -- nunca crea/emite una Factura, la
barrera fiscal (EMISION_FISCAL_VENTA_AUTORIZADA) es ortogonal a esto.
"""
from decimal import Decimal

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.ventas.models import Venta
from apps.tenant.ventas.services.business_service import VentaBusinessService
from tests.tenant.base_test import SintelTenantTestCase


class VincularFacturaManualTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Vincular Factura", nit="900000960", direccion="Calle VF",
        )
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="VF-CLI-1", razon_social="Cliente VF SAS",
            regimen_tributario="ORDINARIO",
        )
        self.venta = Venta.objects.create(
            empresa=self.empresa, cliente=self.cliente, fecha_emision="2026-06-01",
            numero_factura="VF-VENTA-1", subtotal=Decimal("100.00"), total_neto=Decimal("100.00"),
        )
        self.factura_venta = Factura.objects.create(
            empresa=self.empresa, numero="VF-FE-1", consecutivo=1,
            fecha_emision="2026-06-01",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="900123456", receptor_razon_social="Cliente Externo",
            naturaleza=Factura.Naturaleza.VENTA, estado=Factura.Estado.ACEPTADA,
        )
        self.factura_compra = Factura.objects.create(
            empresa=self.empresa, numero="VF-FC-1", consecutivo=2,
            fecha_emision="2026-06-01",
            emisor_nit="900999888", emisor_razon_social="Proveedor Externo",
            receptor_nit=self.empresa.nit, receptor_razon_social=self.empresa.razon_social,
            naturaleza=Factura.Naturaleza.COMPRA, estado=Factura.Estado.ACEPTADA,
        )

    def test_vincula_factura_venta_real(self):
        ok, venta, code = VentaBusinessService.vincular_factura_existente(
            self.venta, str(self.factura_venta.uuid), self.empresa.id,
        )
        self.assertTrue(ok, venta)
        self.assertEqual(code, 200)
        venta.refresh_from_db()
        self.assertEqual(venta.factura_asociada_id, self.factura_venta.id)
        self.assertEqual(venta.estado, Venta.Estado.FACTURADA_DIAN)

    def test_rechaza_factura_de_naturaleza_compra(self):
        ok, result, code = VentaBusinessService.vincular_factura_existente(
            self.venta, str(self.factura_compra.uuid), self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 422)
        self.venta.refresh_from_db()
        self.assertIsNone(self.venta.factura_asociada_id)

    def test_rechaza_factura_inexistente(self):
        ok, result, code = VentaBusinessService.vincular_factura_existente(
            self.venta, "00000000-0000-0000-0000-000000000000", self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 404)

    def test_rechaza_sin_factura_uuid(self):
        ok, result, code = VentaBusinessService.vincular_factura_existente(
            self.venta, "", self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)

    def test_rechaza_si_venta_ya_esta_vinculada(self):
        VentaBusinessService.vincular_factura_existente(
            self.venta, str(self.factura_venta.uuid), self.empresa.id,
        )
        otra_factura = Factura.objects.create(
            empresa=self.empresa, numero="VF-FE-2", consecutivo=3,
            fecha_emision="2026-06-02",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="900123457", receptor_razon_social="Otro Cliente",
            naturaleza=Factura.Naturaleza.VENTA, estado=Factura.Estado.ACEPTADA,
        )
        self.venta.refresh_from_db()
        ok, result, code = VentaBusinessService.vincular_factura_existente(
            self.venta, str(otra_factura.uuid), self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 409)

    def test_dsv_factura_de_otra_empresa_no_se_puede_vincular(self):
        """Anti-IDOR: una Factura de otra empresa no debe resolverse aunque
        el uuid sea correcto (FacturaSelectors.qs_detail filtra por
        empresa_id)."""
        otra_empresa = Empresa.objects.exclude(id=self.empresa.id).first()
        if otra_empresa is None:
            self.skipTest("Requiere una segunda Empresa en el mismo schema para probar DSV cross-empresa.")
        ok, result, code = VentaBusinessService.vincular_factura_existente(
            self.venta, str(self.factura_venta.uuid), otra_empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 404)
