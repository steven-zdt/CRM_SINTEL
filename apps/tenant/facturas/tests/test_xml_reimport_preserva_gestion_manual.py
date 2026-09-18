"""
Integracion Facturas<->Ventas, Fase 20/34 de la mision: "XML no destruye
Gestion Manual". Fija con un test real la garantia que ya existia en el
codigo (guardar_desde_dto() retorna temprano por CUFE duplicado sin tocar
ningun campo salvo cliente_uuid/proveedor_uuid si estaban vacios) para los
6 campos de Gestion Manual (estado_pago, forma_pago, medio_pago_codigo,
payment_due_date, fecha_pago, fecha_vencimiento).
"""
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.facturas.services.business_service import FacturaBusinessService
from tests.tenant.base_test import SintelTenantTestCase


class XmlReimportPreservaGestionManualTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Reimport XML", nit="900000962", direccion="Calle RX",
        )
        self.dto = {
            "numero": "FE-RX-1",
            "identificadores": {"cufe": "CUFE-RX-0001"},
            "emisor": {"nit": self.empresa.nit, "razon_social": self.empresa.razon_social},
            "receptor": {"nit": "900123456", "razon_social": "Cliente Externo RX"},
            "totales": {"subtotal": "100", "impuestos": "19", "total": "119"},
            "fecha_emision": "2026-06-01",
        }

    def test_reimportar_mismo_cufe_no_sobrescribe_gestion_manual(self):
        resultado, code = FacturaBusinessService.guardar_desde_dto(self.dto, empresa_id=self.empresa.id)
        self.assertEqual(code, 201, resultado)
        factura = Factura.objects.get(cufe="CUFE-RX-0001")

        # Gestion manual editada DESPUES de la importacion original.
        FacturaBusinessService.actualizar_factura_limitado(
            factura,
            {
                "estado_pago": "PAGADA",
                "fecha_pago": "2026-06-10",
                "forma_pago": "Credito",
                "medio_pago_codigo": "10",
                "payment_due_date": "2026-07-01",
                "fecha_vencimiento": "2026-07-01",
            },
            self.empresa.id,
        )
        factura.refresh_from_db()
        self.assertEqual(factura.estado_pago, "PAGADA")
        self.assertEqual(str(factura.fecha_pago), "2026-06-10")

        # Reimportacion del MISMO XML/CUFE (ej. el usuario vuelve a subir el
        # mismo archivo por error, o un reproceso automatico del pipeline).
        resultado2, code2 = FacturaBusinessService.guardar_desde_dto(self.dto, empresa_id=self.empresa.id)
        self.assertEqual(code2, 200, resultado2)
        self.assertFalse(resultado2.get("created", True))

        factura.refresh_from_db()
        self.assertEqual(factura.estado_pago, "PAGADA", "estado_pago no debe resetearse en un re-import.")
        self.assertEqual(str(factura.fecha_pago), "2026-06-10", "fecha_pago no debe borrarse en un re-import.")
        self.assertEqual(factura.forma_pago, "Credito")
        self.assertEqual(factura.medio_pago_codigo, "10")
        self.assertEqual(str(factura.payment_due_date), "2026-07-01")
        self.assertEqual(str(factura.fecha_vencimiento), "2026-07-01")

    def test_reimportar_no_duplica_la_factura(self):
        FacturaBusinessService.guardar_desde_dto(self.dto, empresa_id=self.empresa.id)
        FacturaBusinessService.guardar_desde_dto(self.dto, empresa_id=self.empresa.id)
        self.assertEqual(Factura.objects.filter(cufe="CUFE-RX-0001").count(), 1)
