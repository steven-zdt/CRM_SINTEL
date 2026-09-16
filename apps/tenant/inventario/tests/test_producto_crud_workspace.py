"""
Test funcional completo de CRUD de Productos en el workspace (Capa 2: via
API real, mismo endpoint que el offcanvas/JS del frontend consume).

Hueco real detectado durante Batch 2 de la mision UI/UX: Inventario tenia
cobertura extensa de Kardex/Movimientos/Traslados (test_kardex_service.py,
test_f21_traslado_inventario.py) pero ningun test ejercia el CRUD real de
Producto (create/read/update/delete) via API -- solo se creaban productos
directamente por ORM como fixtures de otros tests.

Verifica:
- LIST: GET /api/v1/inventario/productos/
- CREATE: POST /api/v1/inventario/productos/
- READ: GET /api/v1/inventario/productos/{uuid}/
- UPDATE: PATCH /api/v1/inventario/productos/{uuid}/
- DELETE: DELETE /api/v1/inventario/productos/{uuid}/ (regla real: solo inactivo)
- Negativos: codigo duplicado, campos requeridos vacios, UUID inexistente
"""
from rest_framework import status

from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import Producto
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class ProductoCrudWorkspaceTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test Inventario CRUD", nit="900555333", direccion="Calle 1",
        )
        # IsTenantAdminOrReadOnly lee TenantProfile.rol, no TenantMembership.rol.
        TenantProfile.objects.get_or_create(
            user=self.user, empresa=self.empresa,
            defaults={"rol": "ADMIN", "alcance": "EMPRESA", "cargo": "Gerente de Inventario"},
        )

    def _payload_valido(self, codigo="PROD-CRUD-001"):
        return {
            "codigo": codigo,
            "nombre": "Producto de prueba CRUD",
            "descripcion": "Producto de prueba para el ciclo CRUD completo",
            "unidad": "UND",
            "precio_venta": "15000.00",
            "activo": True,
        }

    def test_producto_crud_completo(self):
        # 1. LIST inicial
        resp = self.api_client.get("/api/v1/inventario/productos/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        initial_count = len(resp.json().get("results", resp.json()))

        # 2. CREATE
        resp = self.api_client.post("/api/v1/inventario/productos/", data=self._payload_valido(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        created = resp.json()
        self.assertEqual(created["codigo"], "PROD-CRUD-001")
        producto_uuid = created["id"]

        producto_db = Producto.objects.get(uuid=producto_uuid)
        self.assertEqual(producto_db.nombre, "Producto de prueba CRUD")
        self.assertTrue(producto_db.activo)

        # 3. READ
        resp = self.api_client.get(f"/api/v1/inventario/productos/{producto_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["nombre"], "Producto de prueba CRUD")

        # 4. UPDATE (partial)
        resp = self.api_client.patch(
            f"/api/v1/inventario/productos/{producto_uuid}/",
            data={"nombre": "Producto de prueba CRUD actualizado", "precio_venta": "18000.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["nombre"], "Producto de prueba CRUD actualizado")
        producto_db.refresh_from_db()
        self.assertEqual(producto_db.nombre, "Producto de prueba CRUD actualizado")

        # 5. LIST refleja el update
        resp = self.api_client.get("/api/v1/inventario/productos/")
        items = resp.json().get("results", resp.json())
        self.assertEqual(len(items), initial_count + 1)

        # 6. DELETE negativo: producto activo no se puede eliminar (regla real de negocio)
        resp = self.api_client.delete(f"/api/v1/inventario/productos/{producto_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

        # 7. Inactivar, luego DELETE positivo
        resp = self.api_client.patch(
            f"/api/v1/inventario/productos/{producto_uuid}/", data={"activo": False}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

        resp = self.api_client.delete(f"/api/v1/inventario/productos/{producto_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT, resp.content)
        self.assertFalse(Producto.objects.filter(uuid=producto_uuid).exists())

    def test_producto_create_campos_requeridos_vacios(self):
        resp = self.api_client.post("/api/v1/inventario/productos/", data={}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_producto_create_codigo_duplicado_es_rechazado(self):
        resp = self.api_client.post("/api/v1/inventario/productos/", data=self._payload_valido(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)

        resp = self.api_client.post("/api/v1/inventario/productos/", data=self._payload_valido(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        # Hallazgo menor (Batch 2, no corregido -- fuera de alcance quirurgico
        # de esta pasada): ProductoViewSet.create() intenta dar un mensaje
        # amigable ("duplicate_code") parseando el texto crudo del IntegrityError
        # con una regex que espera `Key (codigo)=(...)`, pero la constraint real
        # es compuesta (`unique_producto_codigo_per_empresa`, sobre empresa+codigo),
        # asi que el mensaje de Postgres no matchea y siempre cae al fallback
        # generico "integrity_error". El resultado sigue siendo 400 (correcto),
        # solo el mensaje es menos especifico de lo que el código pretende.
        self.assertEqual(resp.json().get("error"), "integrity_error")

    def test_producto_read_uuid_inexistente_retorna_404(self):
        resp = self.api_client.get("/api/v1/inventario/productos/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)
