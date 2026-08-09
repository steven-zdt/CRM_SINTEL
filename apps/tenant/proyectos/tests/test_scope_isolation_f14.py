"""
Fase F14 (proyecto OSF), "Pruebas de aislamiento organizacional" - ver
docstring completo en apps/tenant/facturas/tests/test_scope_isolation_f14.py
para el contexto transversal. Este archivo cierra el gap para `proyectos`:
(1) alcance=SEDE sin sedes asignadas -> frozenset(), ve solo sin-sede; (2)
alcance=SEDE con DOS sedes asignadas -> ve proyectos de ambas.
"""
from rest_framework import status

from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proyectos.models import Proyecto
from tests.tenant.base_test import SintelTenantTestCase


class ProyectoIsolationF14Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F14 Proyectos", nit="900000796", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F14 Proy")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F14 Proy")

    def _crear(self, nombre, sede=None):
        return Proyecto.objects.create(empresa=self.empresa, nombre=nombre, sede=sede)

    def test_alcance_sede_sin_asignaciones_no_ve_ninguna_sede_solo_null_safe(self):
        p_sin = self._crear("Proyecto F14 Sin Sede")
        p_a = self._crear("Proyecto F14 Sede A", sede=self.sede_a)

        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )

        resp = self.api_client.get("/api/v1/proyectos/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        ids = {row["id"] for row in resp.json().get("results", resp.json())}
        self.assertIn(p_sin.id, ids)
        self.assertNotIn(p_a.id, ids)

    def test_alcance_sede_con_dos_sedes_asignadas_ve_ambas(self):
        p_a = self._crear("Proyecto F14 Doble A", sede=self.sede_a)
        p_b = self._crear("Proyecto F14 Doble B", sede=self.sede_b)
        sede_c = Sede.objects.create(empresa=self.empresa, nombre="Sede C F14 Proy")
        p_c = self._crear("Proyecto F14 Doble C", sede=sede_c)

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a, self.sede_b])

        resp = self.api_client.get("/api/v1/proyectos/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        ids = {row["id"] for row in resp.json().get("results", resp.json())}
        self.assertIn(p_a.id, ids)
        self.assertIn(p_b.id, ids)
        self.assertNotIn(p_c.id, ids)
