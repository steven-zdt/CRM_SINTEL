"""
Test funcional completo de CRUD de Proyectos en el workspace (Capa 2: via
API real, mismo endpoint que el offcanvas/JS del frontend consume).

Hueco real detectado durante Batch 3 de la mision UI/UX: Proyectos tenia
cobertura extensa de fases/presupuesto/tareas (test_avanzar_fase_persistencia.py,
test_proyecto_fase_validation.py, test_presupuesto_proyecto.py) pero ningun
test ejercia el CRUD real de Proyecto (create/read/update/delete) via API --
todos los Proyecto de esos tests se creaban directamente por ORM como fixture.

Verifica:
- LIST: GET /api/v1/proyectos/
- CREATE: POST /api/v1/proyectos/
- READ: GET /api/v1/proyectos/{uuid}/
- UPDATE: PATCH /api/v1/proyectos/{uuid}/
- DELETE: DELETE /api/v1/proyectos/{uuid}/
- Negativos: campos requeridos vacios, UUID inexistente
"""
from rest_framework import status

from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proyectos.models import Proyecto
from tests.tenant.base_test import SintelTenantTestCase


class ProyectoCrudWorkspaceTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test Proyectos CRUD", nit="900555555", direccion="Calle 1",
        )
        TenantProfile.objects.get_or_create(
            user=self.user, empresa=self.empresa,
            defaults={"rol": "ADMIN", "alcance": "EMPRESA", "cargo": "Gerente de Proyectos"},
        )

    def _payload_valido(self, nombre="Proyecto de prueba CRUD"):
        return {
            "nombre": nombre,
            "tipo_servicio": "PROYECTO_INTEGRAL",
            "descripcion": "Proyecto de prueba para el ciclo CRUD completo",
        }

    def test_proyecto_crud_completo(self):
        # 1. LIST inicial
        resp = self.api_client.get("/api/v1/proyectos/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        initial_count = len(resp.json().get("results", resp.json()))

        # 2. CREATE
        resp = self.api_client.post("/api/v1/proyectos/", data=self._payload_valido(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        created = resp.json()
        self.assertEqual(created["nombre"], "Proyecto de prueba CRUD")
        self.assertEqual(created["fase_actual"], "BORRADOR")
        proyecto_uuid = created["uuid"]

        proyecto_db = Proyecto.objects.get(uuid=proyecto_uuid)
        self.assertEqual(proyecto_db.nombre, "Proyecto de prueba CRUD")

        # 3. READ
        resp = self.api_client.get(f"/api/v1/proyectos/{proyecto_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["nombre"], "Proyecto de prueba CRUD")

        # 4. UPDATE (PATCH -- este ViewSet no define partial_update propio,
        # DRF lo enruta al mismo update() con partial=True via kwargs)
        resp = self.api_client.patch(
            f"/api/v1/proyectos/{proyecto_uuid}/",
            data={"nombre": "Proyecto de prueba CRUD actualizado"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["nombre"], "Proyecto de prueba CRUD actualizado")
        proyecto_db.refresh_from_db()
        self.assertEqual(proyecto_db.nombre, "Proyecto de prueba CRUD actualizado")

        # 5. LIST refleja el update
        resp = self.api_client.get("/api/v1/proyectos/")
        items = resp.json().get("results", resp.json())
        self.assertEqual(len(items), initial_count + 1)

        # 6. DELETE
        resp = self.api_client.delete(f"/api/v1/proyectos/{proyecto_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT, resp.content)
        self.assertFalse(Proyecto.objects.filter(uuid=proyecto_uuid).exists())

    def test_proyecto_create_campos_requeridos_vacios(self):
        resp = self.api_client.post("/api/v1/proyectos/", data={}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_proyecto_read_uuid_inexistente_retorna_404(self):
        resp = self.api_client.get("/api/v1/proyectos/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)
