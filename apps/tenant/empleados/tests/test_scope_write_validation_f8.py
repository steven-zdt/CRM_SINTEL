"""
Fase F8 (proyecto OSF), "Migrar Business Services a scope-aware": el
serializer de Empleado ya validaba (DSV) que `sede`/`area` pertenecieran a
la empresa (anti-IDOR), pero nunca verificaba que estuvieran DENTRO del
alcance organizacional del usuario que hace la peticion (perfil.
sedes_asignadas/areas_asignadas). Un perfil con alcance SEDE asignado solo
a Sede A podia, via API, asignarle a un empleado la Sede B (misma empresa,
pero fuera de su alcance) sin que nada lo impidiera. Corregido con
`sede_esta_en_alcance()`/`area_esta_en_alcance()` (nuevo,
apps/tenant/core/services/organizational_scope.py) en `validate()`.
"""
from rest_framework import status

from apps.tenant.empleados.models import Empleado
from apps.tenant.empresa.models import Area, Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class EmpleadoScopeWriteValidationF8Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F8 Empleados", nit="900000782", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F8 Empl")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F8 Empl")
        self.empleado = Empleado.objects.create(
            empresa=self.empresa, tipo_documento="CC", numero_documento="F8-1",
            primer_nombre="Test", primer_apellido="F8", email="f8emp@test.com",
            estado="ACTIVO", fecha_ingreso="2024-01-01", eps="EPS004", afp="AFP001",
        )

    def test_alcance_sede_no_puede_asignar_sede_fuera_de_su_alcance(self):
        # rol="ADMIN" requerido: EmpleadoViewSet exige rol ADMIN para editar,
        # ortogonal a alcance (ADR-003 seccion 5) - un ADMIN puede tener alcance SEDE.
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a])

        resp = self.api_client.patch(
            f"/api/v1/empleados/{self.empleado.uuid}/",
            data={"sede": str(self.sede_b.uuid)},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertIn("sede", resp.json())
        self.empleado.refresh_from_db()
        self.assertIsNone(self.empleado.sede_id)

    def test_alcance_sede_si_puede_asignar_su_propia_sede(self):
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a])

        resp = self.api_client.patch(
            f"/api/v1/empleados/{self.empleado.uuid}/",
            data={"sede": str(self.sede_a.uuid)},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.empleado.refresh_from_db()
        self.assertEqual(self.empleado.sede_id, self.sede_a.id)

    def test_alcance_empresa_puede_asignar_cualquier_sede(self):
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        resp = self.api_client.patch(
            f"/api/v1/empleados/{self.empleado.uuid}/",
            data={"sede": str(self.sede_b.uuid)},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
