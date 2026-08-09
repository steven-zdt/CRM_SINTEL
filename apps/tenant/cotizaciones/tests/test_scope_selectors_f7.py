"""
Fase F7 (proyecto OSF), "Migrar Selectors a scope-aware" - Cotizacion,
2/6 apps candidatas fuertes (F6): el campo `sede` ya existia (DT-SEDE-04)
pero nunca se usaba para filtrar. NULL-safe: el 100% de las Cotizaciones
reales tiene sede=NULL hoy.
"""
from rest_framework import status

from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class CotizacionScopeSelectorsF7Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F7 Cotizaciones", nit="900000777", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F7 Cot")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F7 Cot")

    def _crear(self, numero, sede=None):
        return Cotizacion.objects.create(
            empresa=self.empresa, numero_cotizacion=numero, fecha_vencimiento="2026-12-31", sede=sede,
        )

    def test_alcance_sede_ve_sin_sede_y_su_sede_pero_no_la_de_otra(self):
        c_sin = self._crear("COT-F7-SIN")
        c_a = self._crear("COT-F7-A", sede=self.sede_a)
        c_b = self._crear("COT-F7-B", sede=self.sede_b)

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a])

        resp = self.api_client.get("/api/v1/cotizaciones/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        numeros = {row["numero_cotizacion"] for row in resp.json().get("results", resp.json())}
        self.assertIn(c_sin.numero_cotizacion, numeros)
        self.assertIn(c_a.numero_cotizacion, numeros)
        self.assertNotIn(c_b.numero_cotizacion, numeros)

    def test_alcance_empresa_sigue_viendo_todo(self):
        self._crear("COT-F7-E-A", sede=self.sede_a)
        self._crear("COT-F7-E-B", sede=self.sede_b)
        self._crear("COT-F7-E-SIN")

        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        resp = self.api_client.get("/api/v1/cotizaciones/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        numeros = {row["numero_cotizacion"] for row in resp.json().get("results", resp.json())}
        self.assertEqual(numeros, {"COT-F7-E-A", "COT-F7-E-B", "COT-F7-E-SIN"})
