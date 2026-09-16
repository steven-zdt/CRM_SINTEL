"""
Test funcional completo de CRUD de Ventas en el workspace (Capa 2: via API
real, mismo endpoint que el offcanvas/JS del frontend consume).

Hueco real detectado durante el cierre de las 15 apps (mision UI/UX):
Ventas tenia cobertura de edicion (test_editar_venta.py), venta+inventario
(F23), idempotencia y vinculacion de factura, pero ningun test ejercia el
ciclo CREATE (via API) -> READ -> DELETE (anular) completo.

Verifica:
- LIST: GET /api/v1/ventas/
- CREATE: POST /api/v1/ventas/ (crea en BORRADOR)
- READ: GET /api/v1/ventas/{uuid}/
- UPDATE: PATCH /api/v1/ventas/{uuid}/
- DELETE: DELETE /api/v1/ventas/{uuid}/ (anula la venta)
- Negativos: sin items, sin fecha_emision, UUID inexistente
"""
from rest_framework import status

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.ventas.models import Venta
from tests.tenant.base_test import SintelTenantTestCase


class VentaCrudWorkspaceTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test Ventas CRUD", nit="900555888", direccion="Calle 1",
        )
        TenantProfile.objects.get_or_create(
            user=self.user, empresa=self.empresa,
            defaults={"rol": "ADMIN", "alcance": "EMPRESA"},
        )
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="NATURAL", tipo_documento="CC",
            numero_documento="1000999888", razon_social="Cliente Test Ventas CRUD",
            regimen_tributario="ORDINARIO", activo=True,
        )

    def _payload_valido(self):
        return {
            "cliente": str(self.cliente.uuid),
            "fecha_emision": "2026-06-01",
            "observaciones": "Venta de prueba CRUD",
            "items": [{
                "descripcion": "Item de prueba",
                "precio_unitario": "50000.00",
                "cantidad": "2",
            }],
        }

    def test_venta_crud_completo(self):
        # 1. LIST inicial
        resp = self.api_client.get("/api/v1/ventas/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        initial_count = len(resp.json().get("results", resp.json()))

        # 2. CREATE
        resp = self.api_client.post("/api/v1/ventas/", data=self._payload_valido(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        created = resp.json()
        self.assertEqual(created["estado"], "BORRADOR")
        venta_uuid = created["uuid"]

        venta_db = Venta.objects.get(uuid=venta_uuid)
        self.assertEqual(venta_db.observaciones, "Venta de prueba CRUD")

        # 3. READ
        resp = self.api_client.get(f"/api/v1/ventas/{venta_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["observaciones"], "Venta de prueba CRUD")

        # 4. UPDATE (partial)
        resp = self.api_client.patch(
            f"/api/v1/ventas/{venta_uuid}/",
            data={"observaciones": "Venta de prueba CRUD actualizada"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["observaciones"], "Venta de prueba CRUD actualizada")
        venta_db.refresh_from_db()
        self.assertEqual(venta_db.observaciones, "Venta de prueba CRUD actualizada")

        # 5. LIST refleja la venta creada
        resp = self.api_client.get("/api/v1/ventas/")
        items = resp.json().get("results", resp.json())
        self.assertEqual(len(items), initial_count + 1)

        # 6. DELETE (anula la venta, no hard-delete)
        resp = self.api_client.delete(f"/api/v1/ventas/{venta_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT, resp.content)

    def test_venta_create_sin_items_es_rechazada(self):
        payload = self._payload_valido()
        payload["items"] = []
        resp = self.api_client.post("/api/v1/ventas/", data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_venta_create_sin_fecha_emision_es_rechazada(self):
        """Hallazgo real corregido esta sesion: payload["fecha_emision"] (acceso
        directo) lanzaba KeyError -> 500 en vez de 400 cuando el campo faltaba."""
        payload = self._payload_valido()
        del payload["fecha_emision"]
        resp = self.api_client.post("/api/v1/ventas/", data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_venta_read_uuid_inexistente_retorna_404(self):
        resp = self.api_client.get("/api/v1/ventas/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)
