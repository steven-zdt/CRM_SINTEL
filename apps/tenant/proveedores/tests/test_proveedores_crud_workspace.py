"""
Test funcional completo de CRUD de Proveedores en el workspace (Capa 2:
via API real, mismo endpoint que el offcanvas/JS del frontend consume).

Contraparte de apps/tenant/clientes/tests/test_clientes_crud_workspace.py
-- hueco real detectado durante la mision UI/UX: Proveedores tenia
cobertura dispersa (representante/DSV, cuentas por pagar, filtros) pero
ningun test unico de ciclo de vida completo CREATE->READ->UPDATE->DELETE
con los caminos negativos que exige Fase 8 de la mision (campo requerido
vacio, duplicado, recurso inexistente, eliminar sin cumplir precondicion).

Verifica:
- LIST: GET /api/v1/proveedores/
- CREATE: POST /api/v1/proveedores/ (JURIDICA exige representante)
- READ: GET /api/v1/proveedores/{uuid}/
- UPDATE: PATCH /api/v1/proveedores/{uuid}/
- DELETE: DELETE /api/v1/proveedores/{uuid}/ (regla real: solo inactivo)
- Negativos: campos requeridos vacios, documento duplicado, UUID inexistente
"""
from rest_framework import status

from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class ProveedoresCrudWorkspaceTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test Proveedores CRUD", nit="900555000", direccion="Calle 1",
        )
        # IsTenantAdminOrReadOnly lee TenantProfile.rol (SSoT v2.61.8), no
        # TenantMembership.rol -- SintelTenantTestCase solo crea el segundo.
        TenantProfile.objects.get_or_create(
            user=self.user, empresa=self.empresa,
            defaults={"rol": "ADMIN", "alcance": "EMPRESA", "cargo": "Gerente de Compras"},
        )

    def _payload_valido(self, numero_documento="900123456"):
        return {
            "tipo_persona": "JURIDICA",
            "tipo_documento": "NIT",
            "numero_documento": numero_documento,
            "razon_social": "PROVEEDOR TEST S.A.S.",
            "nombre_comercial": "PROVEEDOR TEST",
            "regimen_tributario": "ORDINARIO",
            "responsable_iva": True,
            "email_contacto": "compras@proveedortest.com",
            "telefono_contacto": "3001234567",
            "activo": True,
            "representante": {
                "numero_documento": "1000999888",
                "nombre_completo": "Representante Legal Proveedor Test",
            },
        }

    def test_proveedor_crud_completo(self):
        # 1. LIST inicial
        resp = self.api_client.get("/api/v1/proveedores/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        data = resp.json()
        initial_count = len(data.get("results", data))

        # 2. CREATE
        resp = self.api_client.post("/api/v1/proveedores/", data=self._payload_valido(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        created = resp.json()
        self.assertEqual(created["razon_social"], "PROVEEDOR TEST S.A.S.")
        proveedor_uuid = created["uuid"]

        proveedor_db = Proveedor.objects.get(uuid=proveedor_uuid)
        self.assertEqual(proveedor_db.email_contacto, "compras@proveedortest.com")
        self.assertTrue(proveedor_db.activo)

        # 3. READ
        resp = self.api_client.get(f"/api/v1/proveedores/{proveedor_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        detail = resp.json()
        self.assertEqual(detail["razon_social"], "PROVEEDOR TEST S.A.S.")
        self.assertEqual(detail["email_contacto"], "compras@proveedortest.com")

        # 4. UPDATE (partial)
        resp = self.api_client.patch(
            f"/api/v1/proveedores/{proveedor_uuid}/",
            data={"razon_social": "PROVEEDOR TEST ACTUALIZADO S.A.S.", "telefono_contacto": "3009998888"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        updated = resp.json()
        self.assertEqual(updated["razon_social"], "PROVEEDOR TEST ACTUALIZADO S.A.S.")
        proveedor_db.refresh_from_db()
        self.assertEqual(proveedor_db.razon_social, "PROVEEDOR TEST ACTUALIZADO S.A.S.")

        # 5. LIST refleja el update
        resp = self.api_client.get("/api/v1/proveedores/")
        items = resp.json().get("results", resp.json())
        self.assertEqual(len(items), initial_count + 1)
        fila = next((p for p in items if p["uuid"] == proveedor_uuid), None)
        self.assertIsNotNone(fila)
        self.assertEqual(fila["razon_social"], "PROVEEDOR TEST ACTUALIZADO S.A.S.")

        # 6. DELETE negativo: proveedor activo no se puede eliminar (regla real de negocio)
        resp = self.api_client.delete(f"/api/v1/proveedores/{proveedor_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

        # 7. Inactivar, luego DELETE positivo
        resp = self.api_client.patch(
            f"/api/v1/proveedores/{proveedor_uuid}/", data={"activo": False}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

        resp = self.api_client.delete(f"/api/v1/proveedores/{proveedor_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT, resp.content)
        self.assertFalse(Proveedor.objects.filter(uuid=proveedor_uuid).exists())

    def test_proveedor_create_campos_requeridos_vacios(self):
        resp = self.api_client.post("/api/v1/proveedores/", data={}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_proveedor_create_documento_duplicado_es_rechazado(self):
        resp = self.api_client.post("/api/v1/proveedores/", data=self._payload_valido(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)

        resp = self.api_client.post("/api/v1/proveedores/", data=self._payload_valido(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertIn("numero_documento", resp.json())

    def test_proveedor_read_uuid_inexistente_retorna_404(self):
        resp = self.api_client.get("/api/v1/proveedores/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)

    def test_proveedor_juridica_sin_representante_es_rechazado(self):
        payload = self._payload_valido()
        payload.pop("representante")
        resp = self.api_client.post("/api/v1/proveedores/", data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
