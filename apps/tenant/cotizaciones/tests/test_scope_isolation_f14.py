"""
Fase F14 (proyecto OSF), "Pruebas de aislamiento organizacional" - ver
docstring completo en apps/tenant/facturas/tests/test_scope_isolation_f14.py
para el contexto transversal. Este archivo cierra el gap para `cotizaciones`:
(1) alcance=SEDE sin sedes asignadas -> frozenset(), ve solo sin-sede; (2)
alcance=SEDE con DOS sedes asignadas -> ve registros de ambas.
"""
from rest_framework import status

from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class CotizacionIsolationF14Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F14 Cotizaciones", nit="900000793", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F14 Cot")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F14 Cot")

    def _crear(self, numero, sede=None):
        return Cotizacion.objects.create(
            empresa=self.empresa, numero_cotizacion=numero, fecha_vencimiento="2026-12-31", sede=sede,
        )

    def test_alcance_sede_sin_asignaciones_no_ve_ninguna_sede_solo_null_safe(self):
        c_sin = self._crear("COT-F14-SIN")
        c_a = self._crear("COT-F14-A", sede=self.sede_a)

        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )

        resp = self.api_client.get("/api/v1/cotizaciones/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        numeros = {row["numero_cotizacion"] for row in resp.json().get("results", resp.json())}
        self.assertIn(c_sin.numero_cotizacion, numeros)
        self.assertNotIn(c_a.numero_cotizacion, numeros)

    def test_alcance_sede_con_dos_sedes_asignadas_ve_ambas(self):
        c_a = self._crear("COT-F14-DOBLE-A", sede=self.sede_a)
        c_b = self._crear("COT-F14-DOBLE-B", sede=self.sede_b)
        sede_c = Sede.objects.create(empresa=self.empresa, nombre="Sede C F14 Cot")
        c_c = self._crear("COT-F14-DOBLE-C", sede=sede_c)

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a, self.sede_b])

        resp = self.api_client.get("/api/v1/cotizaciones/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        numeros = {row["numero_cotizacion"] for row in resp.json().get("results", resp.json())}
        self.assertIn(c_a.numero_cotizacion, numeros)
        self.assertIn(c_b.numero_cotizacion, numeros)
        self.assertNotIn(c_c.numero_cotizacion, numeros)
