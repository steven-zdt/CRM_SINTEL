"""
Fase F7 (proyecto OSF), "Migrar Selectors a scope-aware" - Empleado,
6/6 apps candidatas fuertes (F6): el campo `sede`/`area` ya existia (hallazgo
de OCF Fase 0, sin tag DT-SEDE) pero nunca se usaba para filtrar. NULL-safe:
el 100% de los Empleado reales tiene sede=NULL/area=NULL hoy. Unica de las 6
apps con AMBOS campos (sede Y area).
"""
from rest_framework import status

from apps.tenant.empleados.models import Empleado
from apps.tenant.empresa.models import Area, Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class EmpleadosScopeSelectorsF7Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F7 Empleados", nit="900000781", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F7 Empl")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F7 Empl")

    def _crear(self, numero_documento, sede=None, area=None):
        return Empleado.objects.create(
            empresa=self.empresa, tipo_documento="CC", numero_documento=numero_documento,
            primer_nombre="Test", primer_apellido="F7", email=f"{numero_documento}@test.com",
            estado="ACTIVO", fecha_ingreso="2024-01-01", eps="EPS004", afp="AFP001",
            sede=sede, area=area,
        )

    def test_alcance_sede_ve_sin_sede_y_su_sede_pero_no_la_de_otra(self):
        e_sin = self._crear("F7-1")
        e_a = self._crear("F7-2", sede=self.sede_a)
        e_b = self._crear("F7-3", sede=self.sede_b)

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a])

        resp = self.api_client.get("/api/v1/empleados/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        ids = {row["id"] for row in resp.json().get("results", resp.json())}
        self.assertIn(e_sin.id, ids)
        self.assertIn(e_a.id, ids)
        self.assertNotIn(e_b.id, ids)

    def test_alcance_area_filtra_por_area_no_solo_por_sede(self):
        area_x = Area.objects.create(
            empresa=self.empresa, sede=self.sede_a, nombre="Area X F7 Empl", codigo_funcionamiento="AXE-F7",
        )
        area_y = Area.objects.create(
            empresa=self.empresa, sede=self.sede_a, nombre="Area Y F7 Empl", codigo_funcionamiento="AYE-F7",
        )
        e_area_x = self._crear("F7-10", sede=self.sede_a, area=area_x)
        e_area_y = self._crear("F7-11", sede=self.sede_a, area=area_y)

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="AREA",
        )
        perfil.sedes_asignadas.set([self.sede_a])
        perfil.areas_asignadas.set([area_x])

        resp = self.api_client.get("/api/v1/empleados/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        ids = {row["id"] for row in resp.json().get("results", resp.json())}
        self.assertIn(e_area_x.id, ids)
        self.assertNotIn(e_area_y.id, ids)

    def test_alcance_empresa_sigue_viendo_todo(self):
        self._crear("F7-20", sede=self.sede_a)
        self._crear("F7-21", sede=self.sede_b)
        self._crear("F7-22")

        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        resp = self.api_client.get("/api/v1/empleados/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(len(resp.json().get("results", resp.json())), 3)
