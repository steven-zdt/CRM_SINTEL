"""
Integracion Facturas<->Ventas: Gestion Manual de Pago.

`Factura` sigue siendo el SSoT de estado_pago/forma_pago/medio_pago_codigo/
payment_due_date/fecha_pago -- `VentaBusinessService.actualizar_gestion_pago()`
es un pass-through fino hacia `FacturaBusinessService.actualizar_factura_limitado()`,
nunca escribe directamente sobre Factura ni crea campos duplicados en Venta.
"""
import datetime
from decimal import Decimal

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.ventas.models import Venta
from apps.tenant.ventas.services.business_service import VentaBusinessService
from tests.tenant.base_test import SintelTenantTestCase


class GestionPagoManualTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Gestion Pago", nit="900000961", direccion="Calle GP",
        )
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="GP-CLI-1", razon_social="Cliente GP SAS",
            regimen_tributario="ORDINARIO",
        )
        self.venta = Venta.objects.create(
            empresa=self.empresa, cliente=self.cliente, fecha_emision="2026-06-01",
            numero_factura="GP-VENTA-1", subtotal=Decimal("100.00"), total_neto=Decimal("100.00"),
        )
        self.factura = Factura.objects.create(
            empresa=self.empresa, numero="GP-FE-1", consecutivo=1,
            fecha_emision="2026-06-01T10:00:00Z",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="900123456", receptor_razon_social="Cliente Externo",
            naturaleza=Factura.Naturaleza.VENTA, estado=Factura.Estado.ACEPTADA,
        )
        ok, venta, code = VentaBusinessService.vincular_factura_existente(
            self.venta, str(self.factura.uuid), self.empresa.id,
        )
        assert ok and code == 200, (venta, code)
        self.venta.refresh_from_db()

    def test_actualiza_estado_pago_y_fecha_pago(self):
        ok, result, code = VentaBusinessService.actualizar_gestion_pago(
            self.venta, {"estado_pago": "PAGADA", "fecha_pago": "2026-06-05"}, self.empresa.id,
        )
        self.assertTrue(ok, result)
        self.assertEqual(code, 200)
        self.factura.refresh_from_db()
        self.assertEqual(self.factura.estado_pago, "PAGADA")
        self.assertEqual(self.factura.fecha_pago, datetime.date(2026, 6, 5))

    def test_actualiza_forma_pago_y_medio_pago_sin_tocar_lo_demas(self):
        ok, result, code = VentaBusinessService.actualizar_gestion_pago(
            self.venta, {"forma_pago": "Credito", "medio_pago_codigo": "10"}, self.empresa.id,
        )
        self.assertTrue(ok, result)
        self.factura.refresh_from_db()
        self.assertEqual(self.factura.forma_pago, "Credito")
        self.assertEqual(self.factura.medio_pago_codigo, "10")
        self.assertEqual(self.factura.estado_pago, "NO_PAGADA")

    def test_rechaza_pagada_sin_fecha_pago(self):
        ok, result, code = VentaBusinessService.actualizar_gestion_pago(
            self.venta, {"estado_pago": "PAGADA"}, self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)
        self.assertIn("fecha_pago", result)
        self.factura.refresh_from_db()
        self.assertEqual(self.factura.estado_pago, "NO_PAGADA")

    def test_rechaza_fecha_pago_anterior_a_fecha_emision(self):
        ok, result, code = VentaBusinessService.actualizar_gestion_pago(
            self.venta, {"fecha_pago": "2020-01-01"}, self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)
        self.factura.refresh_from_db()
        self.assertIsNone(self.factura.fecha_pago)

    def test_rechaza_fecha_pago_futura(self):
        futuro = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
        ok, result, code = VentaBusinessService.actualizar_gestion_pago(
            self.venta, {"fecha_pago": futuro}, self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)

    def test_sin_campos_validos_devuelve_400(self):
        ok, result, code = VentaBusinessService.actualizar_gestion_pago(
            self.venta, {"campo_invalido": "x"}, self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)
        self.assertEqual(result.get("error"), "sin_campos")

    def test_venta_sin_factura_vinculada_devuelve_404(self):
        venta_sin_factura = Venta.objects.create(
            empresa=self.empresa, cliente=self.cliente, fecha_emision="2026-06-02",
            numero_factura="GP-VENTA-2", subtotal=Decimal("50.00"), total_neto=Decimal("50.00"),
        )
        ok, result, code = VentaBusinessService.actualizar_gestion_pago(
            venta_sin_factura, {"estado_pago": "PAGADA", "fecha_pago": "2026-06-05"}, self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 404)
        self.assertEqual(result.get("error"), "sin_factura_vinculada")

    def test_nunca_toca_campos_fiscales(self):
        """La whitelist de FacturaBusinessService.actualizar_factura_limitado()
        ya rechaza XML_IMMUTABLE_FIELDS -- este test confirma que el
        pass-through de Ventas no logra colar un campo fiscal por error
        (GESTION_PAGO_FIELDS es una whitelist mas estrecha, no solo confia
        en la de Facturas)."""
        numero_original = self.factura.numero
        ok, result, code = VentaBusinessService.actualizar_gestion_pago(
            self.venta, {"numero": "FALSIFICADO-999", "estado_pago": "PAGO_PARCIAL"}, self.empresa.id,
        )
        self.assertTrue(ok, result)
        self.factura.refresh_from_db()
        self.assertEqual(self.factura.numero, numero_original)
        self.assertEqual(self.factura.estado_pago, "PAGO_PARCIAL")
