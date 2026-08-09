"""
Fase F9 (proyecto OSF), "Migrar Bridges a scope-aware": de los 5 bridges
reales (Cotizacion/Cliente/Proveedor/InventarioItem/Bancos, todos en
apps/tenant/facturas/services/selectors.py), auditoria confirmo que
Cliente/Proveedor/InventarioItem(catalogo)/Bancos resuelven entidades SIN
concepto de sede (confirmado en F6: Cliente/Proveedor "no recomendado",
Producto/Servicio/TransaccionBancaria no tienen el campo) - nada que
migrar ahi. Unicamente `CotizacionBridge` referencia una entidad
(Cotizacion) con sede real (DT-SEDE-04).

Hallazgo real: `FacturaViewSet.partial_update()` permite vincular una
Factura a una Cotizacion via el campo editable `cotizacion_uuid`
(MANUAL_EDITABLE_FIELDS) - la DSV existente solo verificaba "pertenece a
la empresa", nunca "esta dentro del alcance organizacional del usuario".
Un perfil alcance=SEDE asignado solo a Sede A podia vincular su Factura a
una Cotizacion de Sede B (misma empresa). Corregido propagando
`OrganizationalScope.sede_ids` hasta `CotizacionBridge`.
"""
from rest_framework import status

from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.facturas.models import Factura
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class FacturaCotizacionBridgeScopeF9Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F9", nit="900000783", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F9")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F9")
        self.factura = Factura.objects.create(
            empresa=self.empresa, numero="FA-F9-1", consecutivo=1,
            fecha_emision="2026-06-01T00:00:00Z",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="123", receptor_razon_social="Cliente F9",
        )

    def _crear_cotizacion(self, numero, sede=None):
        return Cotizacion.objects.create(
            empresa=self.empresa, numero_cotizacion=numero, fecha_vencimiento="2026-12-31", sede=sede,
        )

    def test_alcance_sede_no_puede_vincular_cotizacion_de_otra_sede(self):
        cot_b = self._crear_cotizacion("COT-F9-B", sede=self.sede_b)

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a])

        resp = self.api_client.patch(
            f"/api/v1/facturas/{self.factura.uuid}/",
            data={"cotizacion_uuid": str(cot_b.uuid)},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.factura.refresh_from_db()
        self.assertIsNone(self.factura.cotizacion_uuid)

    def test_alcance_sede_puede_vincular_cotizacion_de_su_sede_o_sin_sede(self):
        cot_a = self._crear_cotizacion("COT-F9-A", sede=self.sede_a)
        cot_sin = self._crear_cotizacion("COT-F9-SIN")

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a])

        resp = self.api_client.patch(
            f"/api/v1/facturas/{self.factura.uuid}/",
            data={"cotizacion_uuid": str(cot_a.uuid)},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

        resp2 = self.api_client.patch(
            f"/api/v1/facturas/{self.factura.uuid}/",
            data={"cotizacion_uuid": str(cot_sin.uuid)},
            format="json",
        )
        self.assertEqual(resp2.status_code, status.HTTP_200_OK, resp2.content)

    def test_alcance_empresa_puede_vincular_cualquier_cotizacion(self):
        cot_b = self._crear_cotizacion("COT-F9-E-B", sede=self.sede_b)
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        resp = self.api_client.patch(
            f"/api/v1/facturas/{self.factura.uuid}/",
            data={"cotizacion_uuid": str(cot_b.uuid)},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
