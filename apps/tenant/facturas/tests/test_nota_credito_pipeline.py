"""
Smoke tests para el pipeline XML de Nota Crédito (Fase 9).

# WARNING: OBJETIVO: Validar el pipeline canónico de XML sin romper producción.
- Detección de parsers (Invoice y CreditNote)
- Preview mode (sin persistir)
- Persistencia e idempotencia (CUDE)
- Contratos API (listas/detalle sin xml_content, /xml/ dedicado)
- Inmutabilidad (POST/PUT/PATCH bloqueados)

Arquitectura:
- Usa SintelTenantTestCase para multi-tenant
- Feature flag FEATURE_XML_PIPELINE controla el rollout
"""
import pytest

pytestmark = pytest.mark.skip(reason="Legacy xml_ingest ingest_service path removed; migrate to current document_ingest APIs")

from decimal import Decimal

from django.test import override_settings
from rest_framework import status

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, NotaCredito
from tests.tenant.base_test import SintelTenantTestCase


class NotaCreditoPipelineSmokeTests(SintelTenantTestCase):
    """
    Smoke tests para el pipeline XML de Nota Crédito.
    
    # WARNING: IMPORTANTE: Estos tests requieren FEATURE_XML_PIPELINE=True
    """
    
    def setUp(self):
        """Configuración inicial: crear empresa y factura de referencia."""
        super().setUp()
        
        # Crear empresa del tenant (requerido para importar facturas)
        Empresa.objects.create(
            nit="900123456",
            razon_social="Empresa Test S.A.S.",
            direccion="Calle 123",
            email="test@empresa.com"
        )
        
        # Crear factura de referencia para las notas crédito
        self.factura = Factura.objects.create(
            numero="FV001",
            prefijo="FV",
            consecutivo=1,
            naturaleza="VENTA",
            estado="ACEPTADA",
            fecha_emision="2024-01-15T10:00:00Z",
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test S.A.S.",
            receptor_nit="800987654",
            receptor_razon_social="Cliente Test S.A.S.",
            moneda="COP",
            subtotal=Decimal("100000.00"),
            impuestos=Decimal("19000.00"),
            total=Decimal("119000.00"),
            cufe="TEST-CUFE-001"
        )
    
    def _crear_xml_credit_note(self, numero="NC001", cude="TEST-CUDE-001", motivo="Devolución"):
        """Helper: crea XML de Nota Crédito UBL 2.1."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<CreditNote xmlns="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
            xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
            xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:CustomizationID>2.1</cbc:CustomizationID>
    <cbc:ProfileID>DIAN 2.1: Nota Crédito</cbc:ProfileID>
    <cbc:ID>{numero}</cbc:ID>
    <cbc:UUID>{cude}</cbc:UUID>
    <cbc:IssueDate>2024-01-20</cbc:IssueDate>
    <cbc:IssueTime>10:00:00</cbc:IssueTime>
    <cbc:Note>{motivo}</cbc:Note>
    <cac:DiscrepancyResponse>
        <cbc:Description>{motivo}</cbc:Description>
    </cac:DiscrepancyResponse>
    <cac:BillingReference>
        <cac:InvoiceDocumentReference>
            <cbc:ID>{self.factura.numero}</cbc:ID>
            <cbc:UUID>{self.factura.cufe}</cbc:UUID>
        </cac:InvoiceDocumentReference>
    </cac:BillingReference>
    <cac:LegalMonetaryTotal>
        <cbc:LineExtensionAmount currencyID="COP">50000.00</cbc:LineExtensionAmount>
        <cbc:TaxExclusiveAmount currencyID="COP">50000.00</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="COP">59500.00</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount currencyID="COP">59500.00</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
</CreditNote>"""
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_1_deteccion_parser_credit_note(self):
        """
        Test 1: Detección de parser para Nota Crédito UBL 2.1.
        
        Criterio: ParserRegistry.detect_type() identifica correctamente creditnote.ubl21
        """
        xml_text = self._crear_xml_credit_note()
        
        from apps.services.xml_ingest.registry import registry
        
        document_type = registry.detect_type(xml_text)
        self.assertEqual(document_type, "creditnote.ubl21", 
                        "El parser debe detectar creditnote.ubl21")
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_2_preview_mode_sin_persistir(self):
        """
        Test 2: Preview mode retorna DTO sin persistir.
        
        Criterio: ingest_xml(..., preview=True) devuelve dto sin crear NotaCredito
        """
        xml_text = self._crear_xml_credit_note()
        
        # Preview mode: no debe persistir
        payload, status_code = ingest_xml(xml_text, preview=True)
        
        self.assertEqual(status_code, 200)
        self.assertFalse(payload.get("persisted", True), 
                        "Preview mode no debe persistir")
        self.assertEqual(payload.get("document_type"), "creditnote.ubl21")
        self.assertIn("dto", payload)
        
        # Verificar que NO se creó NotaCredito
        self.assertEqual(NotaCredito.objects.count(), 0,
                        "Preview mode no debe crear NotaCredito")
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_3_persistencia_idempotencia_cude(self):
        """
        Test 3: Persistencia con idempotencia por CUDE.
        
        Criterio:
        - 1er upload NC → 201 Created
        - 2º upload (mismo CUDE) → 409 Conflict (duplicate)
        """
        xml_text = self._crear_xml_credit_note(cude="TEST-CUDE-DUPLICATE")
        
        # Primer upload: debe crear
        payload1, status1 = ingest_xml(xml_text, preview=False)
        
        self.assertEqual(status1, 201, "Primer upload debe retornar 201")
        self.assertTrue(payload1.get("persisted"), "Debe persistir en primer upload")
        self.assertEqual(NotaCredito.objects.count(), 1,
                        "Debe existir una NotaCredito")
        
        # Segundo upload (mismo CUDE): debe retornar 409
        payload2, status2 = ingest_xml(xml_text, preview=False)
        
        self.assertEqual(status2, 409, "Segundo upload debe retornar 409 (duplicate)")
        self.assertFalse(payload2.get("persisted", True), 
                        "No debe persistir en segundo upload")
        self.assertEqual(NotaCredito.objects.count(), 1,
                        "No debe crear duplicado")
        self.assertEqual(payload2.get("error"), "duplicate")
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_4_vinculo_one_to_one_factura(self):
        """
        Test 4: Nota Crédito vinculada 1:1 a Factura.
        
        Criterio:
        - NC se vincula correctamente a factura referenciada
        - Una factura solo puede tener UNA nota crédito
        """
        xml_text = self._crear_xml_credit_note(cude="TEST-CUDE-ONE-TO-ONE")
        
        payload, status_code = ingest_xml(xml_text, preview=False)
        
        self.assertEqual(status_code, 201)
        
        nota = NotaCredito.objects.get(cude="TEST-CUDE-ONE-TO-ONE")
        self.assertEqual(nota.factura.id, self.factura.id,
                        "Nota crédito debe estar vinculada a la factura")
        self.assertTrue(self.factura.tiene_nota_credito,
                       "Factura debe tener nota crédito")
        
        # Intentar crear segunda NC para misma factura: debe fallar
        xml_text2 = self._crear_xml_credit_note(
            numero="NC002", 
            cude="TEST-CUDE-ONE-TO-ONE-2"
        )
        payload2, status2 = ingest_xml(xml_text2, preview=False)
        
        self.assertEqual(status2, 422, "Segunda NC debe retornar 422")
        self.assertEqual(payload2.get("error"), "already_has_nc")
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_5_factura_inexistente_error(self):
        """
        Test 5: Error cuando factura referenciada no existe.
        
        Criterio: Si factura no existe → 422 missing_invoice
        """
        # XML con referencia a factura inexistente
        xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<CreditNote xmlns="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
            xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
            xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:ID>NC999</cbc:ID>
    <cbc:UUID>TEST-CUDE-NOT-FOUND</cbc:UUID>
    <cac:BillingReference>
        <cac:InvoiceDocumentReference>
            <cbc:ID>FACTURA-INEXISTENTE</cbc:ID>
            <cbc:UUID>CUFE-INEXISTENTE</cbc:UUID>
        </cac:InvoiceDocumentReference>
    </cac:BillingReference>
    <cac:LegalMonetaryTotal>
        <cbc:PayableAmount currencyID="COP">10000.00</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
</CreditNote>"""
        
        payload, status_code = ingest_xml(xml_text, preview=False)
        
        self.assertEqual(status_code, 422, "Debe retornar 422 si factura no existe")
        self.assertEqual(payload.get("error"), "missing_invoice")
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_6_contrato_api_lista_sin_xml_content(self):
        """
        Test 6: Contrato API - Lista de notas crédito sin xml_content.
        
        Criterio: GET /api/v1/notas-credito/ no incluye xml_content
        """
        # Crear nota crédito
        xml_text = self._crear_xml_credit_note(cude="TEST-CUDE-API-LIST")
        ingest_xml(xml_text, preview=False)
        
        # GET lista
        response = self.api_client.get('/api/v1/notas-credito/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Verificar que results existe y no tiene xml_content
        if 'results' in data:
            items = data['results']
        else:
            items = data if isinstance(data, list) else []
        
        self.assertGreater(len(items), 0, "Debe haber al menos una nota crédito")
        
        for item in items:
            self.assertNotIn('xml_content', item,
                           "Lista no debe incluir xml_content")
            self.assertIn('numero', item)
            self.assertIn('cude', item)
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_7_contrato_api_detalle_sin_xml_content(self):
        """
        Test 7: Contrato API - Detalle de nota crédito sin xml_content.
        
        Criterio: GET /api/v1/notas-credito/{id}/ no incluye xml_content
        """
        # Crear nota crédito
        xml_text = self._crear_xml_credit_note(cude="TEST-CUDE-API-DETAIL")
        payload, _ = ingest_xml(xml_text, preview=False)
        nc_id = payload.get("id")
        
        # GET detalle
        response = self.api_client.get(f'/api/v1/notas-credito/{nc_id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertNotIn('xml_content', data,
                        "Detalle no debe incluir xml_content")
        self.assertIn('numero', data)
        self.assertIn('cude', data)
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_8_contrato_api_endpoint_xml_dedicado(self):
        """
        Test 8: Contrato API - Endpoint /xml/ entrega XML completo.
        
        Criterio: GET /api/v1/notas-credito/{id}/xml/ retorna XML completo
        """
        # Crear nota crédito
        xml_text = self._crear_xml_credit_note(cude="TEST-CUDE-API-XML")
        payload, _ = ingest_xml(xml_text, preview=False)
        nc_id = payload.get("id")
        
        # GET /xml/
        response = self.api_client.get(f'/api/v1/notas-credito/{nc_id}/xml/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/xml; charset=utf-8')
        
        # Verificar que el contenido XML está presente
        content = response.content.decode('utf-8')
        self.assertIn('CreditNote', content)
        self.assertIn('TEST-CUDE-API-XML', content)
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_9_inmutabilidad_post_put_patch_bloqueados(self):
        """
        Test 9: Inmutabilidad - POST/PUT/PATCH bloqueados.
        
        Criterio:
        - POST /api/v1/notas-credito/ → 405 Method Not Allowed
        - PUT /api/v1/notas-credito/{id}/ → 405 Method Not Allowed
        - PATCH /api/v1/notas-credito/{id}/ → 405 Method Not Allowed
        """
        # Crear nota crédito
        xml_text = self._crear_xml_credit_note(cude="TEST-CUDE-IMMUTABLE")
        payload, _ = ingest_xml(xml_text, preview=False)
        nc_id = payload.get("id")
        
        # POST bloqueado
        response_post = self.api_client.post('/api/v1/notas-credito/', {})
        self.assertEqual(response_post.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # PUT bloqueado
        response_put = self.api_client.put(f'/api/v1/notas-credito/{nc_id}/', {})
        self.assertEqual(response_put.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # PATCH bloqueado
        response_patch = self.api_client.patch(f'/api/v1/notas-credito/{nc_id}/', {})
        self.assertEqual(response_patch.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_10_delete_rollback_tecnico(self):
        """
        Test 10: DELETE permitido para rollback técnico.
        
        Criterio: DELETE /api/v1/notas-credito/{id}/ → 204 No Content
        """
        # Crear nota crédito
        xml_text = self._crear_xml_credit_note(cude="TEST-CUDE-DELETE")
        payload, _ = ingest_xml(xml_text, preview=False)
        nc_id = payload.get("id")
        
        # DELETE permitido
        response = self.api_client.delete(f'/api/v1/notas-credito/{nc_id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(NotaCredito.objects.filter(id=nc_id).exists(),
                        "Nota crédito debe ser eliminada")
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_11_factura_lista_incluye_has_nc(self):
        """
        Test 11: Lista de facturas incluye has_nc y nota_credito_id.
        
        Criterio: GET /api/v1/facturas/ incluye campos has_nc y nota_credito_id
        """
        # Crear nota crédito vinculada
        xml_text = self._crear_xml_credit_note(cude="TEST-CUDE-HAS-NC")
        ingest_xml(xml_text, preview=False)
        
        # GET lista de facturas
        response = self.api_client.get('/api/v1/facturas/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Buscar nuestra factura en los resultados
        if 'results' in data:
            items = data['results']
        else:
            items = data if isinstance(data, list) else []
        
        factura_item = next((f for f in items if f.get('id') == self.factura.id), None)
        
        self.assertIsNotNone(factura_item, "Factura debe estar en la lista")
        self.assertTrue(factura_item.get('has_nc'), 
                        "Factura debe tener has_nc=True")
        self.assertIsNotNone(factura_item.get('nota_credito_id'),
                            "Factura debe tener nota_credito_id")
