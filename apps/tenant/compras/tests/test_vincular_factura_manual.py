"""
FACTURAS-UI-CRONO-01: vinculacion MANUAL de una Factura ya existente
(naturaleza COMPRA) a una Orden de Compra -- nunca crea/emite una
Factura. Compras no tenia NINGUN mecanismo de vinculo antes de esta
mision (hallazgo real de la auditoria, 0 campos relacionados a Factura
en OrdenCompra) -- decision explicita del usuario: 1:1 via
OrdenCompra.factura_asociada, mismo patron que Venta.factura_asociada.
"""

from datetime import date
from decimal import Decimal

from apps.tenant.compras.models import OrdenCompra, PlantillaOrdenCompra
from apps.tenant.compras.services.business_service import OrdenCompraBusinessService
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.facturas.models import Factura
from apps.tenant.proveedores.models import CuentasPagar, Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class VincularFacturaManualComprasTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Vincular Factura Compras",
            nit="900000970",
            direccion="Calle VFC",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede VFC")
        # PLAN_VINCULAR_FACTURA_COMPRA_COMPRAS Fase 10: numero_documento debe
        # coincidir (via same_nit()) con el emisor_nit de self.factura_compra
        # para que los tests de vinculacion exitosa pasen la validacion nueva
        # de proveedor -- antes de esta mision no existia ese chequeo.
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa,
            razon_social="Proveedor VFC",
            numero_documento="900999888",
            tipo_documento="NIT",
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa,
            nombre="Plantilla VFC",
            prefijo="VFC",
            rango_desde=1,
            rango_hasta=1000,
            consecutivo_actual=1,
            vigente=True,
        )
        self.orden = OrdenCompra.objects.create(
            empresa=self.empresa,
            sede=self.sede,
            proveedor=self.proveedor,
            plantilla=self.plantilla,
            fecha=date(2026, 6, 1),
            consecutivo=1,
            numero_documento="VFC-1",
            estado="BORRADOR",
            subtotal=Decimal("10000.00"),
            impuestos=Decimal("1900.00"),
            total=Decimal("11900.00"),
        )
        self.factura_compra = Factura.objects.create(
            empresa=self.empresa,
            numero="VFC-FC-1",
            consecutivo=1,
            fecha_emision="2026-06-01",
            emisor_nit="900999888",
            emisor_razon_social="Proveedor Externo VFC",
            receptor_nit=self.empresa.nit,
            receptor_razon_social=self.empresa.razon_social,
            naturaleza=Factura.Naturaleza.COMPRA,
            estado=Factura.Estado.ACEPTADA,
        )
        self.factura_venta = Factura.objects.create(
            empresa=self.empresa,
            numero="VFC-FE-1",
            consecutivo=2,
            fecha_emision="2026-06-01",
            emisor_nit=self.empresa.nit,
            emisor_razon_social=self.empresa.razon_social,
            receptor_nit="900123456",
            receptor_razon_social="Cliente Externo VFC",
            naturaleza=Factura.Naturaleza.VENTA,
            estado=Factura.Estado.ACEPTADA,
        )

    def test_vincula_factura_compra_real(self):
        ok, orden, code = OrdenCompraBusinessService.vincular_factura_existente(
            str(self.orden.uuid),
            str(self.factura_compra.uuid),
            self.empresa.id,
        )
        self.assertTrue(ok, orden)
        self.assertEqual(code, 200)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.factura_asociada_id, self.factura_compra.id)
        # No existe un estado equivalente a FACTURADA_DIAN en OrdenCompra
        # (regla explicita de la mision: no inventar uno nuevo) -- el
        # estado no debe cambiar por este vinculo.
        self.assertEqual(self.orden.estado, "BORRADOR")

    def test_rechaza_factura_de_naturaleza_venta(self):
        ok, result, code = OrdenCompraBusinessService.vincular_factura_existente(
            str(self.orden.uuid),
            str(self.factura_venta.uuid),
            self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 422)
        self.orden.refresh_from_db()
        self.assertIsNone(self.orden.factura_asociada_id)

    def test_rechaza_orden_inexistente(self):
        ok, result, code = OrdenCompraBusinessService.vincular_factura_existente(
            "00000000-0000-0000-0000-000000000000",
            str(self.factura_compra.uuid),
            self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 404)

    def test_rechaza_factura_inexistente(self):
        ok, result, code = OrdenCompraBusinessService.vincular_factura_existente(
            str(self.orden.uuid),
            "00000000-0000-0000-0000-000000000000",
            self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 404)

    def test_rechaza_si_orden_ya_esta_vinculada(self):
        OrdenCompraBusinessService.vincular_factura_existente(
            str(self.orden.uuid),
            str(self.factura_compra.uuid),
            self.empresa.id,
        )
        otra_factura = Factura.objects.create(
            empresa=self.empresa,
            numero="VFC-FC-2",
            consecutivo=3,
            fecha_emision="2026-06-02",
            emisor_nit="900999889",
            emisor_razon_social="Otro Proveedor VFC",
            receptor_nit=self.empresa.nit,
            receptor_razon_social=self.empresa.razon_social,
            naturaleza=Factura.Naturaleza.COMPRA,
            estado=Factura.Estado.ACEPTADA,
        )
        ok, result, code = OrdenCompraBusinessService.vincular_factura_existente(
            str(self.orden.uuid),
            str(otra_factura.uuid),
            self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 409)

    def test_rechaza_proveedor_incompatible(self):
        """PLAN_VINCULAR_FACTURA_COMPRA_COMPRAS Fase 10: una Factura COMPRA
        real pero de un tercero distinto al proveedor de la Orden nunca se
        vincula silenciosamente."""
        factura_otro_proveedor = Factura.objects.create(
            empresa=self.empresa,
            numero="VFC-FC-3",
            consecutivo=4,
            fecha_emision="2026-06-03",
            emisor_nit="800555444",
            emisor_razon_social="Proveedor Ajeno VFC",
            receptor_nit=self.empresa.nit,
            receptor_razon_social=self.empresa.razon_social,
            naturaleza=Factura.Naturaleza.COMPRA,
            estado=Factura.Estado.ACEPTADA,
        )
        ok, result, code = OrdenCompraBusinessService.vincular_factura_existente(
            str(self.orden.uuid),
            str(factura_otro_proveedor.uuid),
            self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 422)
        self.assertEqual(result.get("error"), "proveedor_incompatible")
        self.orden.refresh_from_db()
        self.assertIsNone(self.orden.factura_asociada_id)

    def test_desvincula_factura_correctamente(self):
        OrdenCompraBusinessService.vincular_factura_existente(
            str(self.orden.uuid),
            str(self.factura_compra.uuid),
            self.empresa.id,
        )
        ok, orden, code = OrdenCompraBusinessService.desvincular_factura_existente(
            str(self.orden.uuid),
            self.empresa.id,
        )
        self.assertTrue(ok, orden)
        self.assertEqual(code, 200)
        self.orden.refresh_from_db()
        self.assertIsNone(self.orden.factura_asociada_id)
        # La Factura fiscal sigue existiendo intacta -- solo se borra el vinculo.
        self.assertTrue(Factura.objects.filter(pk=self.factura_compra.id).exists())

    def test_desvincular_sin_factura_vinculada_falla(self):
        ok, result, code = OrdenCompraBusinessService.desvincular_factura_existente(
            str(self.orden.uuid),
            self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 404)
        self.assertEqual(result.get("error"), "sin_factura_vinculada")

    def test_desvincular_bloqueado_por_pagos_aplicados(self):
        """PLAN_VINCULAR_FACTURA_COMPRA_COMPRAS Fase 17: no se puede perder
        la trazabilidad de un pago real ya aplicado sobre la CxP de la
        Factura vinculada."""
        OrdenCompraBusinessService.vincular_factura_existente(
            str(self.orden.uuid),
            str(self.factura_compra.uuid),
            self.empresa.id,
        )
        CuentasPagar.objects.create(
            empresa=self.empresa,
            proveedor=self.proveedor,
            numero_factura=self.factura_compra.numero,
            factura_uuid=self.factura_compra.uuid,
            fecha_emision=date(2026, 6, 1),
            fecha_vencimiento=date(2026, 7, 1),
            valor_total=Decimal("11900.00"),
            valor_pagado=Decimal("5000.00"),
        )
        ok, result, code = OrdenCompraBusinessService.desvincular_factura_existente(
            str(self.orden.uuid),
            self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 409)
        self.assertEqual(result.get("error"), "vinculo_bloqueado_pagos")
        self.orden.refresh_from_db()
        self.assertIsNotNone(self.orden.factura_asociada_id)

    def test_vincular_sincroniza_factura_uuid_en_cuenta_pagar_existente(self):
        """PLAN_VINCULAR_FACTURA_COMPRA_COMPRAS Fase 20: si la Orden ya
        habia generado una CxP (ej. al Aprobar) antes de vincular la
        Factura, vincular_factura_existente() completa su factura_uuid en
        vez de dejarla huerfana o crear una segunda CxP."""
        cuenta = CuentasPagar.objects.create(
            empresa=self.empresa,
            proveedor=self.proveedor,
            numero_factura=self.orden.numero_documento,
            orden_compra_uuid=self.orden.uuid,
            fecha_emision=date(2026, 6, 1),
            fecha_vencimiento=date(2026, 7, 1),
            valor_total=Decimal("11900.00"),
        )
        OrdenCompraBusinessService.vincular_factura_existente(
            str(self.orden.uuid),
            str(self.factura_compra.uuid),
            self.empresa.id,
        )
        cuenta.refresh_from_db()
        self.assertEqual(cuenta.factura_uuid, self.factura_compra.uuid)
        self.assertEqual(CuentasPagar.objects.filter(empresa=self.empresa).count(), 1)
