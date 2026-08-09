"""
Fase F13 (proyecto OSF), "Resto de aplicaciones (una a la vez)" - sub-fase 5:
empleados. Mismo patron de auditoria objeto-por-accion: `EmpleadoServiceMixin`
sobrescribia `get_qs_list()` (F7, scope-aware) pero no `get_qs_detail()` -
caia al generico de `BaseServiceMixin` (solo empresa_id), afectando
retrieve/update/partial_update/destroy (via get_object() -> get_qs_detail()).
`EmpleadoTableView` (grilla HTML) tampoco aplicaba ningun filtro de
sede/area.
"""
from rest_framework import status

from apps.tenant.empleados.models import Empleado
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class EmpleadoObjectLevelScopeF13Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F13 Empleados", nit="900000791", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F13 Empl")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F13 Empl")

    def _crear(self, doc, sede=None, area=None):
        return Empleado.objects.create(
            empresa=self.empresa, tipo_documento="CC", numero_documento=doc,
            primer_nombre="Test", primer_apellido="F13", email=f"f13emp{doc}@test.com",
            estado="ACTIVO", fecha_ingreso="2024-01-01", eps="EPS004", afp="AFP001",
            sede=sede, area=area,
        )

    def _asignar_perfil_sede(self, sedes):
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set(sedes)
        return perfil

    def test_alcance_sede_no_puede_ver_empleado_de_otra_sede_por_uuid_directo(self):
        emp_b = self._crear("F13-B", sede=self.sede_b)
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.get(f"/api/v1/empleados/{emp_b.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)

    def test_alcance_sede_puede_ver_empleado_sin_sede_null_safe(self):
        emp_sin = self._crear("F13-SIN")
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.get(f"/api/v1/empleados/{emp_sin.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_alcance_empresa_puede_ver_cualquier_sede(self):
        emp_b = self._crear("F13-EMP-B", sede=self.sede_b)
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        resp = self.api_client.get(f"/api/v1/empleados/{emp_b.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
