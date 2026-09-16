"""
Test funcional completo de CRUD de Cuentas Bancarias en el workspace (Capa 2:
via API real, mismo endpoint que el offcanvas/JS del frontend consume).

Hueco real detectado durante Batch 2 de la mision UI/UX: Bancos tenia
cobertura extensa de importacion/conciliacion/matching pero ningun test
ejercia el CRUD real de CuentaBancaria (create/read/update/delete) via API
-- solo se creaban cuentas directamente por ORM como fixtures de otros tests.

Verifica:
- LIST: GET /api/v1/bancos/cuentas/
- CREATE: POST /api/v1/bancos/cuentas/
- READ: GET /api/v1/bancos/cuentas/{uuid}/
- UPDATE: PATCH /api/v1/bancos/cuentas/{uuid}/
- DELETE: DELETE /api/v1/bancos/cuentas/{uuid}/ (regla real: rechaza si tiene extractos asociados)
- Negativos: campos requeridos vacios, UUID inexistente
"""
from rest_framework import status

from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class CuentaBancariaCrudWorkspaceTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test Bancos CRUD", nit="900555444", direccion="Calle 1",
        )
        TenantProfile.objects.get_or_create(
            user=self.user, empresa=self.empresa,
            defaults={"rol": "ADMIN", "alcance": "EMPRESA", "cargo": "Tesorero"},
        )

    def _payload_valido(self, numero="123456789"):
        return {
            "nombre": "Cuenta de prueba CRUD",
            "banco": "Bancolombia",
            "tipo": "AHORROS",
            "numero": numero,
        }

    def test_cuenta_bancaria_crud_completo(self):
        # 1. LIST inicial
        resp = self.api_client.get("/api/v1/bancos/cuentas/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        initial_count = len(resp.json().get("results", resp.json()))

        # 2. CREATE
        resp = self.api_client.post("/api/v1/bancos/cuentas/", data=self._payload_valido(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        created = resp.json()
        self.assertEqual(created["nombre"], "Cuenta de prueba CRUD")
        cuenta_uuid = created["uuid"]

        cuenta_db = CuentaBancaria.objects.get(uuid=cuenta_uuid)
        self.assertEqual(cuenta_db.numero, "123456789")

        # 3. READ
        resp = self.api_client.get(f"/api/v1/bancos/cuentas/{cuenta_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["banco"], "Bancolombia")

        # 4. UPDATE (partial)
        resp = self.api_client.patch(
            f"/api/v1/bancos/cuentas/{cuenta_uuid}/",
            data={"nombre": "Cuenta de prueba CRUD actualizada"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["nombre"], "Cuenta de prueba CRUD actualizada")
        cuenta_db.refresh_from_db()
        self.assertEqual(cuenta_db.nombre, "Cuenta de prueba CRUD actualizada")

        # 5. LIST refleja el update
        resp = self.api_client.get("/api/v1/bancos/cuentas/")
        items = resp.json().get("results", resp.json())
        self.assertEqual(len(items), initial_count + 1)

        # 6. DELETE positivo (sin extractos asociados)
        resp = self.api_client.delete(f"/api/v1/bancos/cuentas/{cuenta_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT, resp.content)
        self.assertFalse(CuentaBancaria.objects.filter(uuid=cuenta_uuid).exists())

    def test_cuenta_bancaria_delete_con_extractos_asociados_es_rechazada(self):
        resp = self.api_client.post("/api/v1/bancos/cuentas/", data=self._payload_valido(), format="json")
        cuenta_uuid = resp.json()["uuid"]
        cuenta = CuentaBancaria.objects.get(uuid=cuenta_uuid)
        ExtractoBancario.objects.create(empresa=self.empresa, cuenta=cuenta, mes=1, anio=2026)

        resp = self.api_client.delete(f"/api/v1/bancos/cuentas/{cuenta_uuid}/")
        self.assertIn(resp.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY), resp.content)
        self.assertTrue(CuentaBancaria.objects.filter(uuid=cuenta_uuid).exists())

    def test_cuenta_bancaria_create_campos_requeridos_vacios(self):
        # CuentaBancariaViewSet.create() enruta ValidationError via
        # handle_service_error(), que mapea a 422 (no 400) -- convencion real
        # de este ViewSet (ver apps/tenant/api/mixins.py), distinta del
        # patron directo `if serializer.is_valid(): ... else: 400` de otras apps.
        resp = self.api_client.post("/api/v1/bancos/cuentas/", data={}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, resp.content)

    def test_cuenta_bancaria_read_uuid_inexistente_retorna_404(self):
        resp = self.api_client.get("/api/v1/bancos/cuentas/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)
