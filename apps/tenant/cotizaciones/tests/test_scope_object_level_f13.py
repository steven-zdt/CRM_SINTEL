"""
Fase F13 (proyecto OSF), "Resto de aplicaciones (una a la vez)" - sub-fase 2:
cotizaciones. Mismo patron de auditoria objeto-por-accion que F11 (Facturas)
y F13/gastos: `CotizacionServiceMixin.get_qs_detail()` estaba sobrescrito
pero NO pasaba `sede_ids` - retrieve/update/exportar-pdf/render-offcanvas-*/
recalcular (todos via get_object()) solo filtraban por empresa_id. Ademas,
`ui_views.py` (paginas de editor/detalle fuera del ViewSet DRF) resolvian
la Cotizacion objetivo con `CotizacionSelector.get_detail_by_uuid(uuid,
empresa.id)` directo, sin ningun chequeo de alcance.
"""
from rest_framework import status

from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.cotizaciones.services.selectors import CotizacionSelector
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class CotizacionObjectLevelScopeF13Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F13 Cotizaciones", nit="900000788", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F13 Cot")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F13 Cot")

    def _crear(self, numero, sede=None):
        return Cotizacion.objects.create(
            empresa=self.empresa, numero_cotizacion=numero, fecha_vencimiento="2026-12-31", sede=sede,
        )

    def _asignar_perfil_sede(self, sedes):
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set(sedes)
        return perfil

    def test_alcance_sede_no_puede_ver_cotizacion_de_otra_sede_por_uuid_directo(self):
        cot_b = self._crear("COT-F13-B", sede=self.sede_b)
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.get(f"/api/v1/cotizaciones/{cot_b.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)

    def test_alcance_sede_puede_ver_cotizacion_sin_sede_null_safe(self):
        cot_sin = self._crear("COT-F13-SIN")
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.get(f"/api/v1/cotizaciones/{cot_sin.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_alcance_empresa_puede_ver_cualquier_sede(self):
        cot_b = self._crear("COT-F13-EMP-B", sede=self.sede_b)
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        resp = self.api_client.get(f"/api/v1/cotizaciones/{cot_b.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_get_detail_by_uuid_selector_respeta_sede_ids_null_safe(self):
        """Ejercita directamente el selector usado por ui_views.py (paginas
        de editor/detalle fuera del ViewSet DRF) - confirma el fix sin
        depender del enrutamiento de las TemplateView."""
        cot_b = self._crear("COT-F13-SEL-B", sede=self.sede_b)
        cot_sin = self._crear("COT-F13-SEL-SIN")

        qs_restringido = CotizacionSelector.get_detail_by_uuid(
            cot_b.uuid, self.empresa.id, sede_ids=frozenset([self.sede_a.id]),
        )
        self.assertFalse(qs_restringido.exists())

        qs_sin = CotizacionSelector.get_detail_by_uuid(
            cot_sin.uuid, self.empresa.id, sede_ids=frozenset([self.sede_a.id]),
        )
        self.assertTrue(qs_sin.exists())
