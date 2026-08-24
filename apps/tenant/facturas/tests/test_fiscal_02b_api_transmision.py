"""
FISCAL-02B: validacion funcional via API real (HTTP, no llamada directa al
service) de POST /facturas/{uuid}/transmitir/ y /reconciliar/.

Cubre la guarda de seguridad critica: sin FISCAL_ALLOW_MOCK_TRANSPORT=True
el endpoint SIEMPRE usa NullTransportAdapter, sin importar que parametros
traiga la request -- nunca finge una transmision DIAN real ante un
usuario real. Solo con el flag activo (entorno de desarrollo/QA) y
?_mock_scenario= explicito se ejercitan los escenarios simulados via HTTP.
"""
from decimal import Decimal

from django.test import override_settings
from rest_framework import status

from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, FacturaAnexos, TransmisionFactura


class FacturaTransmitirAPITests(TenantAPITestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first()
        self.factura = Factura.objects.create(
            empresa=self.empresa, numero="FE-API-1", prefijo="FE", consecutivo=1, tipo="FE",
            naturaleza=Factura.Naturaleza.VENTA, estado=Factura.Estado.BORRADOR, fecha_emision="2026-06-25",
            emisor_nit="900123456", emisor_razon_social="Empresa Emisora S.A.S.",
            receptor_nit="800654321", receptor_razon_social="Cliente Receptor S.A.S.",
            subtotal=Decimal("100000.00"), impuestos=Decimal("19000.00"), total=Decimal("119000.00"),
            cufe="cufe-api-test",
        )
        FacturaAnexos.objects.create(factura=self.factura, ubl_xml="<Invoice>contenido</Invoice>")

    # ---- Guarda de seguridad: sin el flag, SIEMPRE NullTransportAdapter ----

    def test_sin_flag_activo_transmitir_usa_null_adapter_y_es_honesto(self):
        response = self.tpost(f"/api/v1/facturas/{self.factura.uuid}/transmitir/", {})

        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data["resultado"]["success"])
        self.assertIn("no hay un adaptador de transporte dian real configurado", data["resultado"]["response_message"].lower())
        self.factura.refresh_from_db()
        self.assertEqual(self.factura.estado, Factura.Estado.ERROR_TRANSMISION)

    def test_mock_scenario_es_ignorado_sin_el_flag_de_settings(self):
        """Aunque el request pida explicitamente un escenario Mock, sin
        FISCAL_ALLOW_MOCK_TRANSPORT=True debe usarse NullTransportAdapter
        de todas formas -- esta es la guarda de seguridad critica."""
        response = self.tpost(
            f"/api/v1/facturas/{self.factura.uuid}/transmitir/?_mock_scenario=TEST_ACCEPTED", {},
        )

        data = response.json()
        self.assertEqual(data["resultado"]["status"], "ERROR_TRANSMISION")
        self.factura.refresh_from_db()
        self.assertNotEqual(self.factura.estado, Factura.Estado.ACEPTADA, "el mock NUNCA debe activarse sin el flag")

    # ---- Con el flag activo (entorno de desarrollo/QA): validacion funcional real ----

    @override_settings(FISCAL_ALLOW_MOCK_TRANSPORT=True)
    def test_con_flag_activo_mock_scenario_aceptado_funciona_via_http(self):
        response = self.tpost(
            f"/api/v1/facturas/{self.factura.uuid}/transmitir/?_mock_scenario=TEST_ACCEPTED", {},
        )

        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["resultado"]["success"])
        self.assertEqual(data["resultado"]["status"], "ACEPTADO")
        self.assertEqual(data["factura"]["estado"], "ACEPTADA")
        self.assertEqual(data["transmision"]["environment"], "TEST")

    @override_settings(FISCAL_ALLOW_MOCK_TRANSPORT=True)
    def test_con_flag_activo_mock_scenario_rechazado_funciona_via_http(self):
        response = self.tpost(
            f"/api/v1/facturas/{self.factura.uuid}/transmitir/?_mock_scenario=TEST_REJECTED", {},
        )

        data = response.json()
        self.assertEqual(data["resultado"]["status"], "RECHAZADO")
        self.assertEqual(data["factura"]["estado"], "RECHAZADA")

    @override_settings(FISCAL_ALLOW_MOCK_TRANSPORT=True)
    def test_idempotencia_via_http_segundo_intento_inmediato_es_400(self):
        primer = self.tpost(f"/api/v1/facturas/{self.factura.uuid}/transmitir/?_mock_scenario=TEST_PENDING", {})
        self.assertEqual(primer.status_code, status.HTTP_200_OK)

        segundo = self.tpost(f"/api/v1/facturas/{self.factura.uuid}/transmitir/?_mock_scenario=TEST_ACCEPTED", {})

        self.assertEqual(segundo.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- reconciliar() via API ----

    def test_reconciliar_sin_transmision_previa_es_404(self):
        response = self.tpost(f"/api/v1/facturas/{self.factura.uuid}/reconciliar/", {})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(FISCAL_ALLOW_MOCK_TRANSPORT=True)
    def test_reconciliar_via_http_con_adaptador_sin_memoria_no_inventa_un_resultado(self):
        """Cada request HTTP construye una instancia nueva de MockTransportAdapter
        -- get_status() en una instancia sin historial (nunca vio el send()
        de la request anterior) retorna "not_found" honestamente, nunca
        ACEPTADO/RECHAZADO inventados. Mismo comportamiento esperado de un
        adaptador real cuyo proceso no comparte memoria entre requests."""
        self.tpost(f"/api/v1/facturas/{self.factura.uuid}/transmitir/?_mock_scenario=TEST_PENDING", {})
        self.factura.refresh_from_db()
        self.assertEqual(self.factura.estado, Factura.Estado.ENVIADA)

        response = self.tpost(
            f"/api/v1/facturas/{self.factura.uuid}/reconciliar/?_mock_scenario=TEST_ACCEPTED", {},
        )

        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["resultado"]["status"], "ERROR_TRANSMISION")
        self.assertIn("not_found", data["resultado"]["errors"])
