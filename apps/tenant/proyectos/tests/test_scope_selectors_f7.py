"""
Fase F7 (proyecto OSF), "Migrar Selectors a scope-aware" - Proyecto,
5/6 apps candidatas fuertes (F6): el campo `sede` ya existia (DT-SEDE)
pero nunca se usaba para filtrar. NULL-safe: el 100% de los Proyecto
reales tiene sede=NULL hoy.
"""
from rest_framework import status

from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proyectos.models import Proyecto
from tests.tenant.base_test import SintelTenantTestCase


class ProyectosScopeSelectorsF7Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F7 Proyectos", nit="900000780", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F7 Proy")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F7 Proy")

    def _crear(self, nombre, sede=None):
        return Proyecto.objects.create(empresa=self.empresa, nombre=nombre, sede=sede)

    def test_alcance_sede_ve_sin_sede_y_su_sede_pero_no_la_de_otra(self):
        p_sin = self._crear("Proyecto F7 Sin Sede")
        p_a = self._crear("Proyecto F7 Sede A", sede=self.sede_a)
        p_b = self._crear("Proyecto F7 Sede B", sede=self.sede_b)

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a])

        resp = self.api_client.get("/api/v1/proyectos/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        ids = {row["id"] for row in resp.json().get("results", resp.json())}
        self.assertIn(p_sin.id, ids)
        self.assertIn(p_a.id, ids)
        self.assertNotIn(p_b.id, ids)

    def test_alcance_empresa_sigue_viendo_todo(self):
        self._crear("Proyecto F7 E A", sede=self.sede_a)
        self._crear("Proyecto F7 E B", sede=self.sede_b)
        self._crear("Proyecto F7 E Sin")

        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        resp = self.api_client.get("/api/v1/proyectos/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(len(resp.json().get("results", resp.json())), 3)
