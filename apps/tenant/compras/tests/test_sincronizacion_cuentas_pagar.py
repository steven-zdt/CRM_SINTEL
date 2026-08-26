"""
Sincronizacion Compras -> Proveedores: al aprobar una Orden de Compra se
genera automaticamente su Cuenta por Pagar (bug real reportado en vivo:
tenant `home` tenia una OrdenCompra sin ninguna CuentasPagar asociada,
porque ningun flujo del sistema llamaba a
CuentasPagarBusinessService.registrar_cuenta_pagar() salvo el endpoint
manual). Decision explicita del usuario: el trigger es la transicion a
estado APROBADA.
"""
from datetime import date, timedelta
from decimal import Decimal

from apps.tenant.compras.models import OrdenCompra, PlantillaOrdenCompra
from apps.tenant.compras.services.business_service import OrdenCompraBusinessService
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.proveedores.models import CuentasPagar, Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class SincronizacionCuentasPagarTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Sync CxP", nit="900000940", direccion="Calle Sync CxP",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede Sync CxP")
        # plazo_pago_dias distinto del default (30) para que el test no
        # pase "por casualidad" si la fecha_vencimiento se calculara mal.
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor Sync CxP", numero_documento="SYNC-CXP-1",
            tipo_documento="NIT", plazo_pago_dias=45,
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa, nombre="Plantilla Sync CxP", prefijo="SYNCCXP",
            rango_desde=1, rango_hasta=1000, consecutivo_actual=1, vigente=True,
        )
        self.orden = OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede, proveedor=self.proveedor, plantilla=self.plantilla,
            fecha=date(2026, 6, 1), consecutivo=1, numero_documento="SYNCCXP-1", estado="BORRADOR",
            subtotal=Decimal("10000.00"), impuestos=Decimal("1900.00"), total=Decimal("11900.00"),
        )

    def test_aprobar_orden_genera_cuenta_por_pagar(self):
        self.assertEqual(CuentasPagar.objects.filter(empresa=self.empresa).count(), 0)

        ok, orden, code = OrdenCompraBusinessService.cambiar_estado_orden_compra(
            str(self.orden.uuid), "APROBADA", self.empresa.id,
        )
        self.assertTrue(ok, orden)
        self.assertEqual(code, 200)

        cxp = CuentasPagar.objects.get(empresa=self.empresa, numero_factura="SYNCCXP-1")
        self.assertEqual(cxp.proveedor_id, self.proveedor.id)
        self.assertEqual(cxp.valor_total, Decimal("11900.00"))
        self.assertEqual(cxp.saldo, Decimal("11900.00"))
        self.assertEqual(cxp.estado_pago, "SIN_PAGO")
        self.assertEqual(cxp.fecha_emision, date(2026, 6, 1))
        self.assertEqual(cxp.fecha_vencimiento, date(2026, 6, 1) + timedelta(days=45))
        self.assertEqual(cxp.orden_compra_uuid, self.orden.uuid)

    def test_reaprobar_es_idempotente_no_duplica(self):
        OrdenCompraBusinessService.cambiar_estado_orden_compra(str(self.orden.uuid), "APROBADA", self.empresa.id)
        OrdenCompraBusinessService.cambiar_estado_orden_compra(str(self.orden.uuid), "APROBADA", self.empresa.id)

        self.assertEqual(
            CuentasPagar.objects.filter(empresa=self.empresa, numero_factura="SYNCCXP-1").count(), 1,
        )

    def test_transicion_a_pendiente_no_genera_cuenta_por_pagar(self):
        ok, orden, code = OrdenCompraBusinessService.cambiar_estado_orden_compra(
            str(self.orden.uuid), "PENDIENTE", self.empresa.id,
        )
        self.assertTrue(ok, orden)
        self.assertEqual(CuentasPagar.objects.filter(empresa=self.empresa).count(), 0)
