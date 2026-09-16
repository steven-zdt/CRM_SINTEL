"""
Test funcional completo de CRUD de Ordenes de Compra en el workspace
(Capa 2: via API real, mismo endpoint que el offcanvas/JS del frontend
consume). Contraparte de clientes/proveedores -- hueco real detectado
durante la mision UI/UX: Compras tenia tests especificos (F5 scope,
recepcion, sincronizacion CxP) pero ninguno de ciclo de vida basico
CREATE->READ->UPDATE->cambiar-estado->DELETE con caminos negativos
(Fase 8 de la mision).

Verifica:
- LIST: GET /api/v1/compras/
- CREATE: POST /api/v1/compras/ (con items, plantilla, proveedor)
- READ: GET /api/v1/compras/{uuid}/
- UPDATE: PATCH /api/v1/compras/{uuid}/
- Cambio de estado: POST /api/v1/compras/{uuid}/cambiar-estado/
- DELETE: DELETE /api/v1/compras/{uuid}/ (regla real: solo BORRADOR)
- Negativos: items vacios, fecha_entrega < fecha, transicion invalida,
  eliminar orden ya aprobada, UUID inexistente
"""
from rest_framework import status

from apps.tenant.compras.models import OrdenCompra, PlantillaOrdenCompra
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class ComprasCrudWorkspaceTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test Compras CRUD", nit="900555111", direccion="Calle 1",
        )
        # IsTenantAdminOrReadOnly lee TenantProfile.rol (SSoT v2.61.8), no
        # TenantMembership.rol -- SintelTenantTestCase solo crea el segundo.
        TenantProfile.objects.get_or_create(
            user=self.user, empresa=self.empresa,
            defaults={"rol": "ADMIN", "alcance": "EMPRESA", "cargo": "Gerente de Compras"},
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede CRUD Test")
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor CRUD Test",
            tipo_documento="NIT", numero_documento="900555222", activo=True,
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa, nombre="Plantilla CRUD Test", prefijo="OCCRUD",
            rango_desde=1, rango_hasta=1000, consecutivo_actual=1, vigente=True,
        )

    def _payload_valido(self):
        return {
            "plantilla": str(self.plantilla.uuid),
            "proveedor": str(self.proveedor.uuid),
            "sede": str(self.sede.uuid),
            "fecha": "2026-06-01",
            "fecha_entrega": "2026-06-10",
            "observaciones": "Orden de prueba CRUD",
            "items": [{
                "descripcion": "Item de prueba",
                "cantidad": "2",
                "valor_unitario": "100000",
                "porcentaje_iva": "19",
            }],
        }

    def test_orden_compra_crud_completo(self):
        # 1. LIST inicial
        resp = self.api_client.get("/api/v1/compras/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        initial_count = len(resp.json().get("results", resp.json()))

        # 2. CREATE
        resp = self.api_client.post("/api/v1/compras/", data=self._payload_valido(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        created = resp.json()
        self.assertEqual(created["estado"], "BORRADOR")
        self.assertEqual(len(created["items"]), 1)
        orden_uuid = created["uuid"]

        orden_db = OrdenCompra.objects.get(uuid=orden_uuid)
        self.assertEqual(orden_db.observaciones, "Orden de prueba CRUD")

        # 3. READ
        resp = self.api_client.get(f"/api/v1/compras/{orden_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["proveedor_nombre"], "Proveedor CRUD Test")

        # 4. UPDATE (partial)
        resp = self.api_client.patch(
            f"/api/v1/compras/{orden_uuid}/",
            data={"observaciones": "Orden actualizada CRUD"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["observaciones"], "Orden actualizada CRUD")

        # 5. LIST refleja la orden creada
        resp = self.api_client.get("/api/v1/compras/")
        items = resp.json().get("results", resp.json())
        self.assertEqual(len(items), initial_count + 1)

        # 6. DELETE negativo: transicion invalida antes de cambiar estado
        resp = self.api_client.post(
            f"/api/v1/compras/{orden_uuid}/cambiar-estado/", data={"estado": "RECIBIDA"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

        # 7. Cambiar estado valido: BORRADOR -> APROBADA
        resp = self.api_client.post(
            f"/api/v1/compras/{orden_uuid}/cambiar-estado/", data={"estado": "APROBADA"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["estado"], "APROBADA")

        # 8. DELETE negativo: ya no esta en Borrador, no se puede eliminar
        resp = self.api_client.delete(f"/api/v1/compras/{orden_uuid}/")
        self.assertIn(resp.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT), resp.content)
        self.assertTrue(OrdenCompra.objects.filter(uuid=orden_uuid).exists())

    def test_orden_compra_delete_positivo_en_borrador(self):
        resp = self.api_client.post("/api/v1/compras/", data=self._payload_valido(), format="json")
        orden_uuid = resp.json()["uuid"]

        resp = self.api_client.delete(f"/api/v1/compras/{orden_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT, resp.content)
        self.assertFalse(OrdenCompra.objects.filter(uuid=orden_uuid).exists())

    def test_orden_compra_create_sin_items_es_rechazada(self):
        payload = self._payload_valido()
        payload["items"] = []
        resp = self.api_client.post("/api/v1/compras/", data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_orden_compra_create_fecha_entrega_anterior_a_fecha_es_rechazada(self):
        payload = self._payload_valido()
        payload["fecha"] = "2026-06-10"
        payload["fecha_entrega"] = "2026-06-01"
        resp = self.api_client.post("/api/v1/compras/", data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertIn("fecha_entrega", resp.json())

    def test_orden_compra_read_uuid_inexistente_retorna_404(self):
        resp = self.api_client.get("/api/v1/compras/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)
