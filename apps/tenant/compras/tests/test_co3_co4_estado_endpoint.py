"""
Regresion (2026-09-12, hallazgos CO-3 y CO-4, docs/remediation/AUDIT_BASELINE_20260912.md).

CO-3: OrdenCompraCreateUpdateSerializer no marcaba 'estado' como
read_only -- un PATCH directo con {"estado": "APROBADA"} sobre una orden
BORRADOR/PENDIENTE tenia exito SIN pasar por
cambiar_estado_orden_compra()/TRANSICIONES_VALIDAS, saltandose
_sincronizar_cuenta_por_pagar() (una orden podia llegar a APROBADA sin
generar su Cuenta por Pagar). Fix: 'estado' en read_only_fields.

CO-4: OrdenCompraCRUDService.cambiar_estado() hacia
orden.save(update_fields=['estado']) -- Django solo refresca un campo
auto_now=True si esta en update_fields, asi que 'updated_at' nunca
avanzaba en una transicion real (Aprobar/Anular). Fix:
update_fields=['estado', 'updated_at'].
"""
from datetime import date
from decimal import Decimal

from apps.tenant.compras.models import OrdenCompra, PlantillaOrdenCompra
from apps.tenant.compras.services.business_service import OrdenCompraBusinessService
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import CuentasPagar, Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class CO3EstadoNoEditableViaPatchGenericoTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa CO3-CO4", nit="900000963", direccion="Calle CO3-CO4",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN")
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede CO3-CO4")
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor CO3-CO4", numero_documento="CO3-1",
            tipo_documento="NIT",
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa, nombre="Plantilla CO3-CO4", prefijo="CO3",
            rango_desde=1, rango_hasta=1000, consecutivo_actual=1, vigente=True,
        )
        self.orden = OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede, proveedor=self.proveedor, plantilla=self.plantilla,
            fecha=date(2026, 6, 1), consecutivo=1, numero_documento="CO3-1", estado="BORRADOR",
            subtotal=Decimal("1000.00"), impuestos=Decimal("190.00"), total=Decimal("1190.00"),
        )

    def test_patch_generico_con_estado_no_lo_cambia_ni_genera_cxp(self):
        """
        Antes del fix: este PATCH tenia 200 OK, la orden quedaba en
        estado=APROBADA en BD, y NUNCA se generaba su CuentasPagar (bypass
        de _sincronizar_cuenta_por_pagar()).
        """
        resp = self.api_client.patch(
            f"/api/v1/compras/{self.orden.uuid}/",
            {"estado": "APROBADA"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        self.orden.refresh_from_db()
        self.assertEqual(
            self.orden.estado, "BORRADOR",
            "estado cambio via PATCH generico -- el bypass de la maquina de estados sigue abierto.",
        )
        self.assertEqual(
            CuentasPagar.objects.filter(empresa=self.empresa, numero_factura="CO3-1").count(), 0,
            "Se genero una CuentasPagar sin pasar por cambiar_estado_orden_compra().",
        )

    def test_transicion_real_si_aprueba_y_genera_cxp(self):
        """Control positivo: el endpoint de transicion dedicado sigue
        funcionando exactamente igual tras el fix de CO-3."""
        resp = self.api_client.post(f"/api/v1/compras/{self.orden.uuid}/cambiar-estado/", {"estado": "APROBADA"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, "APROBADA")
        self.assertTrue(CuentasPagar.objects.filter(empresa=self.empresa, numero_factura="CO3-1").exists())


class CO4UpdatedAtEnTransicionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa CO4", nit="900000964", direccion="Calle CO4",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede CO4")
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor CO4", numero_documento="CO4-1",
            tipo_documento="NIT",
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa, nombre="Plantilla CO4", prefijo="CO4",
            rango_desde=1, rango_hasta=1000, consecutivo_actual=1, vigente=True,
        )
        self.orden = OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede, proveedor=self.proveedor, plantilla=self.plantilla,
            fecha=date(2026, 6, 1), consecutivo=1, numero_documento="CO4-1", estado="BORRADOR",
            subtotal=Decimal("1000.00"), impuestos=Decimal("190.00"), total=Decimal("1190.00"),
        )

    def test_aprobar_actualiza_updated_at(self):
        updated_at_antes = self.orden.updated_at

        ok, orden, code = OrdenCompraBusinessService.cambiar_estado_orden_compra(
            str(self.orden.uuid), "APROBADA", self.empresa.id,
        )
        self.assertTrue(ok, orden)

        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, "APROBADA")
        self.assertGreater(
            self.orden.updated_at, updated_at_antes,
            "updated_at no avanzo tras la transicion -- update_fields no incluia 'updated_at'.",
        )
