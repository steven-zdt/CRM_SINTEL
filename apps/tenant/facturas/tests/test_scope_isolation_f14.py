"""
Fase F14 (proyecto OSF), "Pruebas de aislamiento organizacional" - cierre
formal transversal a las 6 apps candidatas fuertes (facturas, cotizaciones,
gastos, inventario, proyectos, empleados).

Auditoria previa (agente de exploracion dedicado) confirmo 2 invariantes de
`OrganizationalScope` verificados a nivel unitario desde F2
(apps/tenant/core/tests/test_organizational_scope.py) pero NUNCA
end-to-end contra un endpoint real de ninguna de las 6 apps:

1. Un perfil alcance=SEDE con CERO sedes asignadas debe resolver
   `sede_ids=frozenset()` (no `None`) y por lo tanto ver SOLO los registros
   sin sede (NULL-safe), nunca los de una sede ajena - "restringe a nada,
   no a todo" (F2). Nunca antes probado contra un endpoint real.
2. Un perfil asignado a DOS sedes debe ver registros de AMBAS, no solo la
   primera - todos los tests F7/F13 previos de las 6 apps usaban una sola
   sede asignada.

Este archivo cierra ese gap para `facturas`.
"""
from rest_framework import status

from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.facturas.models import Factura
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class FacturaIsolationF14Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F14 Facturas", nit="900000792", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F14 Facturas")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F14 Facturas")

    def _crear(self, numero, sede=None):
        return Factura.objects.create(
            empresa=self.empresa, numero=numero, consecutivo=1,
            fecha_emision="2026-06-01T00:00:00Z",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="123", receptor_razon_social="Cliente F14",
            sede=sede,
        )

    def test_alcance_sede_sin_asignaciones_no_ve_ninguna_sede_solo_null_safe(self):
        f_sin = self._crear("F14-SIN")
        f_a = self._crear("F14-A", sede=self.sede_a)

        # alcance=SEDE pero SIN llamar a sedes_asignadas.set(...) - perfil
        # con cero sedes asignadas (frozenset(), no None).
        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )

        resp = self.api_client.get("/api/v1/facturas/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        numeros = {row["numero"] for row in resp.json().get("results", resp.json())}
        self.assertIn(f_sin.numero, numeros)
        self.assertNotIn(f_a.numero, numeros)

    def test_alcance_sede_con_dos_sedes_asignadas_ve_ambas(self):
        f_a = self._crear("F14-DOBLE-A", sede=self.sede_a)
        f_b = self._crear("F14-DOBLE-B", sede=self.sede_b)
        sede_c = Sede.objects.create(empresa=self.empresa, nombre="Sede C F14 Facturas")
        f_c = self._crear("F14-DOBLE-C", sede=sede_c)

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a, self.sede_b])

        resp = self.api_client.get("/api/v1/facturas/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        numeros = {row["numero"] for row in resp.json().get("results", resp.json())}
        self.assertIn(f_a.numero, numeros)
        self.assertIn(f_b.numero, numeros)
        self.assertNotIn(f_c.numero, numeros)
