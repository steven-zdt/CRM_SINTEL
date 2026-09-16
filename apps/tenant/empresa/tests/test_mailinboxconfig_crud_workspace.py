"""
Test funcional completo de CRUD de MailInboxConfig en el workspace (Capa 2:
via API real, mismo endpoint que el offcanvas/JS del frontend consume).

Hueco real detectado durante Batch 4 de la mision UI/UX: existian tests de
render-offcanvas y de la grilla (Tabulator), pero ningun test ejercia el
CRUD real (create/read/update/delete) via los metodos POST/PATCH/DELETE
del ViewSet -- MailInboxConfigViewSet usa el ModelViewSet por defecto de
DRF sin metodos propios, asi que nunca se habia ejercido esa ruta.

Nota (hallazgo documentado, no corregido esta sesion -- mismo patron que
PerfilViewSet, ver checklist de la mision): MailInboxConfigViewSet no
hereda BaseTenantViewSet y no define lookup_field -- usa el default de DRF
(`pk`, entero crudo), exponiendo IDs secuenciales en la URL en vez de UUID.
Estos tests usan el PK porque hoy es la unica forma soportada; no valida
ni recomienda ese comportamiento.

Verifica:
- LIST: GET /api/v1/empresas/mail-inbox-config/
- CREATE: POST /api/v1/empresas/mail-inbox-config/
- READ: GET /api/v1/empresas/mail-inbox-config/{id}/
- UPDATE: PATCH /api/v1/empresas/mail-inbox-config/{id}/
- DELETE: DELETE /api/v1/empresas/mail-inbox-config/{id}/
- Negativo: campo requerido invalido (email malformado)
"""
from rest_framework import status

from apps.tenant.empresa.models import Empresa, MailInboxConfig
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class MailInboxConfigCrudWorkspaceTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test MailInbox CRUD", nit="900555777", direccion="Calle 1",
        )
        TenantProfile.objects.get_or_create(
            user=self.user, empresa=self.empresa,
            defaults={"rol": "ADMIN", "alcance": "EMPRESA"},
        )

    def _payload_valido(self, nombre="Buzon de prueba CRUD"):
        return {
            "nombre": nombre,
            "email_address": "facturas-test@example.com",
            "provider": "custom",
            "imap_password": "app-password-de-prueba",
        }

    def test_mailinboxconfig_crud_completo(self):
        # 1. LIST inicial
        resp = self.api_client.get("/api/v1/empresas/mail-inbox-config/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        initial_count = len(resp.json().get("results", resp.json()))

        # 2. CREATE
        resp = self.api_client.post(
            "/api/v1/empresas/mail-inbox-config/", data=self._payload_valido(), format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        created = resp.json()
        self.assertEqual(created["nombre"], "Buzon de prueba CRUD")
        config_id = created["id"]

        config_db = MailInboxConfig.objects.get(id=config_id)
        self.assertEqual(config_db.email_address, "facturas-test@example.com")

        # 3. READ
        resp = self.api_client.get(f"/api/v1/empresas/mail-inbox-config/{config_id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["nombre"], "Buzon de prueba CRUD")

        # 4. UPDATE (partial)
        resp = self.api_client.patch(
            f"/api/v1/empresas/mail-inbox-config/{config_id}/",
            data={"nombre": "Buzon de prueba CRUD actualizado"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["nombre"], "Buzon de prueba CRUD actualizado")
        config_db.refresh_from_db()
        self.assertEqual(config_db.nombre, "Buzon de prueba CRUD actualizado")

        # 5. LIST refleja el update
        resp = self.api_client.get("/api/v1/empresas/mail-inbox-config/")
        items = resp.json().get("results", resp.json())
        self.assertEqual(len(items), initial_count + 1)

        # 6. DELETE
        resp = self.api_client.delete(f"/api/v1/empresas/mail-inbox-config/{config_id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT, resp.content)
        self.assertFalse(MailInboxConfig.objects.filter(id=config_id).exists())

    def test_mailinboxconfig_create_email_invalido_es_rechazado(self):
        payload = self._payload_valido()
        payload["email_address"] = "no-es-un-email"
        resp = self.api_client.post("/api/v1/empresas/mail-inbox-config/", data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_mailinboxconfig_read_id_inexistente_retorna_404(self):
        resp = self.api_client.get("/api/v1/empresas/mail-inbox-config/999999/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)
