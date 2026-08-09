"""
Fase F13 (proyecto OSF), "Resto de aplicaciones (una a la vez)" - sub-fase 4:
proyectos. Mismo patron de auditoria objeto-por-accion: `ProyectoViewSet.get_object()`
resolvia `qs_detail()` solo por empresa_id (afecta retrieve/update/partial_update/
destroy/cambiar-fase). Ademas, `ItemPresupuestoViewSet`/`TareaDiariaViewSet`
(recursos hijos referenciados por `proyecto_uuid`) tampoco heredaban el
alcance del Proyecto padre, y `ProyectoTableView` (grilla HTML) no aplicaba
ningun filtro de sede.
"""
from rest_framework import status

from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proyectos.models import ItemPresupuestoProyecto, Proyecto
from tests.tenant.base_test import SintelTenantTestCase


class ProyectoObjectLevelScopeF13Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F13 Proyectos", nit="900000790", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F13 Proy")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F13 Proy")

    def _crear(self, nombre, sede=None):
        return Proyecto.objects.create(empresa=self.empresa, nombre=nombre, sede=sede)

    def _asignar_perfil_sede(self, sedes):
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set(sedes)
        return perfil

    def test_alcance_sede_no_puede_ver_proyecto_de_otra_sede_por_uuid_directo(self):
        p_b = self._crear("Proyecto F13 B", sede=self.sede_b)
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.get(f"/api/v1/proyectos/{p_b.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)

    def test_alcance_sede_puede_ver_proyecto_sin_sede_null_safe(self):
        p_sin = self._crear("Proyecto F13 Sin Sede")
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.get(f"/api/v1/proyectos/{p_sin.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_alcance_sede_no_puede_listar_items_presupuesto_de_proyecto_de_otra_sede(self):
        p_b = self._crear("Proyecto F13 Items B", sede=self.sede_b)
        ItemPresupuestoProyecto.objects.create(
            empresa=self.empresa, proyecto=p_b, categoria="MATERIALES",
            descripcion="Item F13", cantidad=1, valor_unitario=1000,
        )
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.get(f"/api/v1/proyectos/items-presupuesto/?proyecto_uuid={p_b.uuid}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(len(resp.json().get("results", resp.json())), 0)

    def test_alcance_empresa_puede_ver_cualquier_sede(self):
        p_b = self._crear("Proyecto F13 EMP B", sede=self.sede_b)
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        resp = self.api_client.get(f"/api/v1/proyectos/{p_b.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
