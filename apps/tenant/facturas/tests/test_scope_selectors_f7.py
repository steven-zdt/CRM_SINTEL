"""
Fase F7 (proyecto OSF), "Migrar Selectors a scope-aware" - primera de las 6
apps candidatas fuertes identificadas en F6 (el campo `sede` ya existe en
`Factura`, pero nunca se usaba para filtrar).

Hallazgo real verificado empiricamente antes de escribir codigo: el 100% de
las Facturas reales en los 3 tenants del entorno tiene `sede=NULL` - decision
del usuario (F7): un registro sin sede debe quedar VISIBLE para todos los
alcances (EMPRESA/SEDE/AREA), no solo EMPRESA - `filter_by_scope_null_safe`
en vez de `filter_by_scope` (que compras SI puede usar porque su `sede` es
NOT NULL).
"""
from rest_framework import status

from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.facturas.models import Factura
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class FacturaScopeSelectorsF7Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F7 Facturas", nit="900000666", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F7 Facturas")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F7 Facturas")

    def _crear_factura(self, numero, sede=None):
        return Factura.objects.create(
            empresa=self.empresa, numero=numero, consecutivo=1,
            fecha_emision="2026-06-01T00:00:00Z",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="123", receptor_razon_social="Cliente F7",
            sede=sede,
        )

    def test_alcance_sede_ve_sin_sede_y_su_sede_pero_no_la_de_otra(self):
        f_sin_sede = self._crear_factura("F7-SIN-SEDE")
        f_sede_a = self._crear_factura("F7-SEDE-A", sede=self.sede_a)
        f_sede_b = self._crear_factura("F7-SEDE-B", sede=self.sede_b)

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a])

        resp = self.api_client.get("/api/v1/facturas/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        numeros = {row["numero"] for row in resp.json().get("results", resp.json())}
        self.assertIn(f_sin_sede.numero, numeros)
        self.assertIn(f_sede_a.numero, numeros)
        self.assertNotIn(f_sede_b.numero, numeros)

    def test_alcance_empresa_sigue_viendo_todo(self):
        self._crear_factura("F7-E-A", sede=self.sede_a)
        self._crear_factura("F7-E-B", sede=self.sede_b)
        self._crear_factura("F7-E-SIN")

        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )

        resp = self.api_client.get("/api/v1/facturas/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        numeros = {row["numero"] for row in resp.json().get("results", resp.json())}
        self.assertEqual(numeros, {"F7-E-A", "F7-E-B", "F7-E-SIN"})
