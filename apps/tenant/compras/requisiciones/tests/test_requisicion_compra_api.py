"""
Fase 12 (autorizada por el usuario 2026-09-25): API REST de
RequisicionCompra -- CRUD completo via APIClient (mismo patron que
apps/tenant/compras/tests/test_compras_crud_workspace.py), acciones de
maquina de estados, y aislamiento multitenant (empresa_id).
"""

from datetime import date, timedelta

from rest_framework import status

from apps.tenant.compras.requisiciones.models import RequisicionCompra
from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class RequisicionCompraApiTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Req API",
            nit="900700300",
            direccion="Calle Req API",
        )
        TenantProfile.objects.get_or_create(
            user=self.user,
            empresa=self.empresa,
            defaults={"rol": "ADMIN", "alcance": "EMPRESA", "cargo": "Gerente de Compras"},
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede Req API")
        # Cotizacion de origen -- OBLIGATORIA al crear desde 2026-09-26.
        self.cotizacion = Cotizacion.objects.create(
            empresa=self.empresa,
            numero_cotizacion="COT-REQ-API-001",
            fecha_vencimiento=date.today() + timedelta(days=30),
        )

    def _payload_valido(self, **overrides):
        data = {
            "fecha_necesidad": (date.today() + timedelta(days=7)).isoformat(),
            "tipo": "BIEN",
            "prioridad": "MEDIA",
            "justificacion": "Necesidad real de prueba API",
            "observaciones": "",
            "cotizacion": str(self.cotizacion.uuid),
            "items": [
                {
                    "tipo_item": "BIEN",
                    "descripcion": "Item API",
                    "cantidad_solicitada": "2",
                    "valor_unitario_estimado": "75000",
                    "porcentaje_iva": "19",
                }
            ],
        }
        data.update(overrides)
        return data

    def test_requisicion_crud_completo(self):
        # LIST inicial
        resp = self.api_client.get("/api/v1/compras/requisiciones/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        initial_count = len(resp.json().get("results", resp.json()))

        # CREATE
        resp = self.api_client.post(
            "/api/v1/compras/requisiciones/", data=self._payload_valido(), format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        created = resp.json()
        self.assertEqual(created["estado"], "BORRADOR")
        self.assertEqual(created["numero_documento"], "REQ-000001")
        self.assertEqual(len(created["items"]), 1)
        req_uuid = created["uuid"]

        # READ
        resp = self.api_client.get(f"/api/v1/compras/requisiciones/{req_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

        # UPDATE (partial, solo BORRADOR)
        resp = self.api_client.patch(
            f"/api/v1/compras/requisiciones/{req_uuid}/",
            data={"observaciones": "Actualizada via API"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["observaciones"], "Actualizada via API")

        # LIST refleja la nueva
        resp = self.api_client.get("/api/v1/compras/requisiciones/")
        items = resp.json().get("results", resp.json())
        self.assertEqual(len(items), initial_count + 1)

        # estado NO es editable via PATCH generico
        resp = self.api_client.patch(
            f"/api/v1/compras/requisiciones/{req_uuid}/",
            data={"estado": "APROBADA"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        req_db = RequisicionCompra.objects.get(uuid=req_uuid)
        self.assertEqual(req_db.estado, "BORRADOR")  # el intento de PATCH fue ignorado, no aplicado

        # DELETE positivo (BORRADOR sin dependencias)
        resp = self.api_client.delete(f"/api/v1/compras/requisiciones/{req_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT, resp.content)
        self.assertFalse(RequisicionCompra.objects.filter(uuid=req_uuid).exists())

    def test_requisicion_create_sin_items_es_rechazada(self):
        payload = self._payload_valido()
        payload["items"] = []
        resp = self.api_client.post("/api/v1/compras/requisiciones/", data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_requisicion_read_uuid_inexistente_retorna_404(self):
        resp = self.api_client.get(
            "/api/v1/compras/requisiciones/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)

    def test_flujo_estados_via_api(self):
        resp = self.api_client.post(
            "/api/v1/compras/requisiciones/", data=self._payload_valido(), format="json"
        )
        req_uuid = resp.json()["uuid"]

        resp = self.api_client.post(f"/api/v1/compras/requisiciones/{req_uuid}/enviar-aprobacion/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["estado"], "PENDIENTE_APROBACION")

        resp = self.api_client.post(f"/api/v1/compras/requisiciones/{req_uuid}/aprobar/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["estado"], "APROBADA")

        # ya no se puede eliminar (no BORRADOR)
        resp = self.api_client.delete(f"/api/v1/compras/requisiciones/{req_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_rechazar_sin_motivo_via_api_es_422(self):
        resp = self.api_client.post(
            "/api/v1/compras/requisiciones/", data=self._payload_valido(), format="json"
        )
        req_uuid = resp.json()["uuid"]
        self.api_client.post(f"/api/v1/compras/requisiciones/{req_uuid}/enviar-aprobacion/")

        resp = self.api_client.post(
            f"/api/v1/compras/requisiciones/{req_uuid}/rechazar/", data={}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, resp.content)

    def test_rechazar_con_motivo_via_api(self):
        resp = self.api_client.post(
            "/api/v1/compras/requisiciones/", data=self._payload_valido(), format="json"
        )
        req_uuid = resp.json()["uuid"]
        self.api_client.post(f"/api/v1/compras/requisiciones/{req_uuid}/enviar-aprobacion/")

        resp = self.api_client.post(
            f"/api/v1/compras/requisiciones/{req_uuid}/rechazar/",
            data={"motivo": "No aplica"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["estado"], "RECHAZADA")

    def test_transicion_invalida_via_api_es_400(self):
        resp = self.api_client.post(
            "/api/v1/compras/requisiciones/", data=self._payload_valido(), format="json"
        )
        req_uuid = resp.json()["uuid"]
        # BORRADOR -> aprobar directo sin pasar por enviar-aprobacion
        resp = self.api_client.post(f"/api/v1/compras/requisiciones/{req_uuid}/aprobar/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_aislamiento_dsv_empresa_id_incorrecto_no_ve_ni_edita(self):
        """DSV anti-IDOR a nivel de Service Layer: Empresa es singleton por
        tenant schema (UniqueConstraint 'unique_singleton_empresa_per_schema',
        apps/tenant/empresa/models.py) -- no existe un segundo Empresa real
        dentro del mismo schema para simular una empresa "ajena". Se prueba
        el mismo efecto (empresa_id que no coincide con la fila) con un
        empresa_id inexistente, equivalente a lo que veria un request cuyo
        contexto de tenant resolviera mal el empresa_id."""
        resp = self.api_client.post(
            "/api/v1/compras/requisiciones/", data=self._payload_valido(), format="json"
        )
        req_uuid = resp.json()["uuid"]

        from apps.tenant.compras.requisiciones.services.business_service import (
            RequisicionCompraBusinessService,
        )

        empresa_id_incorrecto = self.empresa.id + 999999
        ok, result, code = RequisicionCompraBusinessService.enviar_a_aprobacion(
            req_uuid, empresa_id_incorrecto
        )
        self.assertFalse(ok)
        self.assertEqual(code, 404)

    def test_no_se_puede_generar_orden_sin_aprobar(self):
        resp = self.api_client.post(
            "/api/v1/compras/requisiciones/", data=self._payload_valido(), format="json"
        )
        req_uuid = resp.json()["uuid"]
        resp = self.api_client.post(
            f"/api/v1/compras/requisiciones/{req_uuid}/crear-orden/",
            data={"orden": {}, "items": []},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, resp.content)
