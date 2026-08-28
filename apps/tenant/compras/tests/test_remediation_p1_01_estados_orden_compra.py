"""
REM P1-01 (docs/remediation/REM-P1-01.md): OrdenCompraCRUDService.
cambiar_estado() no validaba la maquina de estados -- permitia saltos
arbitrarios (ej. RECIBIDA -> BORRADOR). Se agrego
OrdenCompraBusinessService.TRANSICIONES_VALIDAS, con self-loops explicitos
para no romper el flujo real ya probado en test_sincronizacion_cuentas_
pagar.py (BORRADOR->APROBADA directo, re-aprobar idempotente).
"""
from datetime import date
from decimal import Decimal

from apps.tenant.compras.models import OrdenCompra, PlantillaOrdenCompra
from apps.tenant.compras.services.business_service import OrdenCompraBusinessService
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class OrdenCompraTransicionesP1_01Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa P1-01", nit="900000795", direccion="Calle P1-01",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede P1-01")
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor P1-01", numero_documento="P101-1",
            tipo_documento="NIT",
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa, nombre="Plantilla P1-01", prefijo="P101",
            rango_desde=1, rango_hasta=1000, consecutivo_actual=1, vigente=True,
        )

    def _crear_orden(self, estado):
        return OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede, proveedor=self.proveedor, plantilla=self.plantilla,
            fecha=date(2026, 6, 1), consecutivo=1, numero_documento=f"P101-{estado}", estado=estado,
            subtotal=Decimal("1000.00"), impuestos=Decimal("190.00"), total=Decimal("1190.00"),
        )

    def test_salto_de_recibida_a_borrador_es_rechazado(self):
        """Caso central del hallazgo: una orden ya RECIBIDA no puede
        retroceder a BORRADOR via cambiar_estado."""
        orden = self._crear_orden("RECIBIDA")
        ok, resultado, code = OrdenCompraBusinessService.cambiar_estado_orden_compra(
            str(orden.uuid), "BORRADOR", self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)
        orden.refresh_from_db()
        self.assertEqual(orden.estado, "RECIBIDA")

    def test_anular_orden_recibida_es_rechazado(self):
        """Una orden ya recibida no se anula por esta via -- necesitaria
        reversar CxP/inventario ya generados, fuera de alcance de esta
        correccion (ver REM-P1-01.md)."""
        orden = self._crear_orden("RECIBIDA")
        ok, resultado, code = OrdenCompraBusinessService.cambiar_estado_orden_compra(
            str(orden.uuid), "ANULADA", self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)

    def test_anular_orden_aprobada_sigue_permitido(self):
        orden = self._crear_orden("APROBADA")
        ok, resultado, code = OrdenCompraBusinessService.cambiar_estado_orden_compra(
            str(orden.uuid), "ANULADA", self.empresa.id,
        )
        self.assertTrue(ok, resultado)
        self.assertEqual(code, 200)

    def test_borrador_a_aprobada_directo_sigue_permitido(self):
        """No regresionar el flujo real ya probado en
        test_sincronizacion_cuentas_pagar.py."""
        orden = self._crear_orden("BORRADOR")
        ok, resultado, code = OrdenCompraBusinessService.cambiar_estado_orden_compra(
            str(orden.uuid), "APROBADA", self.empresa.id,
        )
        self.assertTrue(ok, resultado)
        self.assertEqual(code, 200)
