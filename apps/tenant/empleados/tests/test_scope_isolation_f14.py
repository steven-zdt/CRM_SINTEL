"""
Fase F14 (proyecto OSF), "Pruebas de aislamiento organizacional" - ver
docstring completo en apps/tenant/facturas/tests/test_scope_isolation_f14.py
para el contexto transversal. Este archivo cierra 3 gaps para `empleados`
(unica de las 6 apps con AMBOS campos sede Y area):
(1) alcance=SEDE sin sedes asignadas -> frozenset(), ve solo sin-sede;
(2) alcance=SEDE con DOS sedes asignadas -> ve empleados de ambas;
(3) alcance=AREA a nivel de OBJETO (retrieve por UUID) - F7 solo probo AREA
    en el listado (`test_alcance_area_filtra_por_area_no_solo_por_sede`),
    F13 solo probo SEDE a nivel de objeto - la combinacion AREA+retrieve
    nunca se habia verificado.
"""
from rest_framework import status

from apps.tenant.empleados.models import Empleado
from apps.tenant.empresa.models import Area, Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class EmpleadoIsolationF14Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F14 Empleados", nit="900000797", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F14 Empl")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F14 Empl")

    def _crear(self, doc, sede=None, area=None):
        return Empleado.objects.create(
            empresa=self.empresa, tipo_documento="CC", numero_documento=doc,
            primer_nombre="Test", primer_apellido="F14", email=f"f14emp{doc}@test.com",
            estado="ACTIVO", fecha_ingreso="2024-01-01", eps="EPS004", afp="AFP001",
            sede=sede, area=area,
        )

    def test_alcance_sede_sin_asignaciones_no_ve_ninguna_sede_solo_null_safe(self):
        e_sin = self._crear("F14-SIN")
        e_a = self._crear("F14-A", sede=self.sede_a)

        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )

        resp = self.api_client.get("/api/v1/empleados/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        ids = {row["id"] for row in resp.json().get("results", resp.json())}
        self.assertIn(e_sin.id, ids)
        self.assertNotIn(e_a.id, ids)

    def test_alcance_sede_con_dos_sedes_asignadas_ve_ambas(self):
        e_a = self._crear("F14-DOBLE-A", sede=self.sede_a)
        e_b = self._crear("F14-DOBLE-B", sede=self.sede_b)
        sede_c = Sede.objects.create(empresa=self.empresa, nombre="Sede C F14 Empl")
        e_c = self._crear("F14-DOBLE-C", sede=sede_c)

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a, self.sede_b])

        resp = self.api_client.get("/api/v1/empleados/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        ids = {row["id"] for row in resp.json().get("results", resp.json())}
        self.assertIn(e_a.id, ids)
        self.assertIn(e_b.id, ids)
        self.assertNotIn(e_c.id, ids)

    def test_alcance_area_no_puede_ver_por_uuid_directo_empleado_de_otra_area(self):
        area_x = Area.objects.create(
            empresa=self.empresa, sede=self.sede_a, nombre="Area X F14 Empl", codigo_funcionamiento="AXE-F14",
        )
        area_y = Area.objects.create(
            empresa=self.empresa, sede=self.sede_a, nombre="Area Y F14 Empl", codigo_funcionamiento="AYE-F14",
        )
        e_area_y = self._crear("F14-AREA-Y", sede=self.sede_a, area=area_y)

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="AREA",
        )
        perfil.sedes_asignadas.set([self.sede_a])
        perfil.areas_asignadas.set([area_x])

        resp = self.api_client.get(f"/api/v1/empleados/{e_area_y.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)

    def test_alcance_area_puede_ver_por_uuid_directo_empleado_de_su_propia_area(self):
        area_x = Area.objects.create(
            empresa=self.empresa, sede=self.sede_a, nombre="Area X2 F14 Empl", codigo_funcionamiento="AX2E-F14",
        )
        e_area_x = self._crear("F14-AREA-X", sede=self.sede_a, area=area_x)

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="AREA",
        )
        perfil.sedes_asignadas.set([self.sede_a])
        perfil.areas_asignadas.set([area_x])

        resp = self.api_client.get(f"/api/v1/empleados/{e_area_x.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
