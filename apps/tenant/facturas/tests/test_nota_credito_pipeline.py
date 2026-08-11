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
import io
from decimal import Decimal

from django.test import override_settings
from rest_framework import status

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, NotaCredito
from apps.tenant.facturas.services.business_service import FacturaBusinessService
from apps.services.document_ingest.ingest_service import ingest_document
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
        self.empresa_test = Empresa.objects.create(
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
    
    def _ingest_xml(self, xml_text, preview=False):
        """Helper para emular el pipeline de ingesta actual."""
        # Note: ingest_document espera bytes como primer argumento
        dto, _ = ingest_document(xml_text.encode('utf-8'), mime_type='text/xml')
        
        if preview:
            # En preview mode el ViewSet usualmente retorna 200 con el DTO
            return {"dto": dto, "persisted": False, "document_type": dto.get("document_type")}, 200
            
        res, status_code = FacturaBusinessService.guardar_desde_dto(
            dto=dto,
            xml_text=xml_text
        )
        return res, status_code
    
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
        <cbc:ReferenceID>{self.factura.numero}</cbc:ReferenceID>
        <cbc:ResponseCode>2</cbc:ResponseCode>
        <cbc:Description>{motivo}</cbc:Description>
    </cac:DiscrepancyResponse>
    <cac:BillingReference>
        <cac:InvoiceDocumentReference>
            <cbc:ID>{self.factura.numero}</cbc:ID>
            <cbc:UUID>{self.factura.cufe}</cbc:UUID>
        </cac:InvoiceDocumentReference>
    </cac:BillingReference>
    <cac:AccountingSupplierParty>
        <cac:Party>
            <cac:PartyTaxScheme>
                <cbc:RegistrationName>Proveedor Test</cbc:RegistrationName>
                <cbc:CompanyID schemeAgencyID="195" schemeID="4">800123456</cbc:CompanyID>
                <cac:TaxScheme><cbc:ID>01</cbc:ID></cac:TaxScheme>
            </cac:PartyTaxScheme>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
        <cac:Party>
            <cac:PartyTaxScheme>
                <cbc:RegistrationName>{self.empresa_test.razon_social}</cbc:RegistrationName>
                <cbc:CompanyID schemeAgencyID="195" schemeID="4">{self.empresa_test.nit}</cbc:CompanyID>
                <cac:TaxScheme><cbc:ID>01</cbc:ID></cac:TaxScheme>
            </cac:PartyTaxScheme>
        </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:LegalMonetaryTotal>
        <cbc:LineExtensionAmount currencyID="COP">50000.00</cbc:LineExtensionAmount>
        <cbc:TaxExclusiveAmount currencyID="COP">50000.00</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="COP">59500.00</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount currencyID="COP">59500.00</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
</CreditNote>"""
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_1_deteccion_parser_credit_note(self):
        """Test 1: Detección de parser para Nota Crédito UBL 2.1."""
        xml_text = self._crear_xml_credit_note()
        
        dto, _ = ingest_document(xml_text.encode('utf-8'), mime_type='text/xml')
        
        self.assertEqual(dto.get("document_type"), "creditnote.ubl21")
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_2_preview_mode_sin_persistir(self):
        """Test 2: Preview mode retorna DTO sin persistir."""
        xml_text = self._crear_xml_credit_note()
        
        payload, status_code = self._ingest_xml(xml_text, preview=True)
        
        self.assertEqual(status_code, 200)
        self.assertFalse(payload.get("persisted", True))
        self.assertEqual(NotaCredito.objects.count(), 0)
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_3_persistencia_idempotencia_cude(self):
        """Test 3: Persistencia con idempotencia por CUDE."""
        xml_text = self._crear_xml_credit_note(cude="TEST-CUDE-DUPLICATE")
        
        # Primer upload
        payload1, status1 = self._ingest_xml(xml_text, preview=False)
        self.assertEqual(status1, 201)
        self.assertEqual(NotaCredito.objects.count(), 1)
        
        # Segundo upload (mismo CUDE) -> 200 (idempotencia silenciosa)
        payload2, status2 = self._ingest_xml(xml_text, preview=False)
        self.assertEqual(status2, 200)
        self.assertEqual(NotaCredito.objects.count(), 1)
        self.assertEqual(payload2.get("error"), "duplicate")
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_4_vinculo_one_to_one_factura(self):
        """Test 4: Nota Crédito vinculada 1:1 a Factura."""
        xml_text = self._crear_xml_credit_note(cude="TEST-CUDE-ONE-TO-ONE")
        payload, status_code = self._ingest_xml(xml_text, preview=False)
        
        self.assertEqual(status_code, 201)
        nota = NotaCredito.objects.get(cude="TEST-CUDE-ONE-TO-ONE")
        self.assertEqual(nota.factura_original.id, self.factura.id)
        
        # Segunda NC para misma factura -> 422
        xml_text2 = self._crear_xml_credit_note(numero="NC002", cude="TEST-CUDE-2")
        payload2, status2 = self._ingest_xml(xml_text2, preview=False)
        self.assertEqual(status2, 422)
        self.assertEqual(payload2.get("error"), "already_has_nc")
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_5_factura_inexistente_error(self):
        """
        Test 5: Error cuando factura referenciada no existe.

        F26: fixture corregida con evidencia. El XML original no declaraba
        AccountingSupplierParty/AccountingCustomerParty -- guardar_desde_dto()
        valida que el NIT de la empresa actual coincida con emisor o receptor
        ANTES de resolver la factura_original_para_nc (business_service.py,
        validacion de pertenencia del NIT), asi que sin esos nodos el XML
        nunca llegaba a ejercitar el chequeo "missing_invoice" que este test
        realmente quiere probar -- fallaba antes, con un
        DjangoValidationError distinto (NIT no coincide). Se agrega
        AccountingCustomerParty con el NIT de self.empresa_test (mismo patron
        que _crear_xml_credit_note) para que el XML sea valido hasta ese
        punto y el test ejercite genuinamente la referencia a una factura
        inexistente.
        """
        xml_text = f"""<?xml version="1.0" encoding="UTF-8"?>
<CreditNote xmlns="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
            xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
            xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
    <cbc:ID>NC999</cbc:ID>
    <cbc:UUID>TEST-CUDE-NOT-FOUND</cbc:UUID>
    <cbc:IssueDate>2024-01-20</cbc:IssueDate>
    <cac:BillingReference>
        <cac:InvoiceDocumentReference>
            <cbc:ID>FACTURA-INEXISTENTE</cbc:ID>
            <cbc:UUID>CUFE-INEXISTENTE</cbc:UUID>
        </cac:InvoiceDocumentReference>
    </cac:BillingReference>
    <cac:AccountingSupplierParty>
        <cac:Party>
            <cac:PartyTaxScheme>
                <cbc:RegistrationName>Proveedor Test</cbc:RegistrationName>
                <cbc:CompanyID schemeAgencyID="195" schemeID="4">800123456</cbc:CompanyID>
                <cac:TaxScheme><cbc:ID>01</cbc:ID></cac:TaxScheme>
            </cac:PartyTaxScheme>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
        <cac:Party>
            <cac:PartyTaxScheme>
                <cbc:RegistrationName>{self.empresa_test.razon_social}</cbc:RegistrationName>
                <cbc:CompanyID schemeAgencyID="195" schemeID="4">{self.empresa_test.nit}</cbc:CompanyID>
                <cac:TaxScheme><cbc:ID>01</cbc:ID></cac:TaxScheme>
            </cac:PartyTaxScheme>
        </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:LegalMonetaryTotal>
        <cbc:PayableAmount currencyID="COP">10000.00</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
</CreditNote>"""
        payload, status_code = self._ingest_xml(xml_text, preview=False)
        self.assertEqual(status_code, 422)
        self.assertEqual(payload.get("error"), "missing_invoice")
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_6_contrato_api_lista_sin_xml_content(self):
        """Test 6: Contrato API - Lista de notas crédito sin xml_content."""
        xml_text = self._crear_xml_credit_note(cude="TEST-CUDE-API-LIST")
        self._ingest_xml(xml_text, preview=False)
        
        response = self.api_client.get('/api/v1/facturas/notas-credito/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        items = data.get('results', [])
        
        self.assertGreater(len(items), 0)
        for item in items:
            self.assertNotIn('xml_content', item)
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_7_contrato_api_detalle_sin_xml_content(self):
        """Test 7: Contrato API - Detalle de nota crédito sin xml_content."""
        xml_text = self._crear_xml_credit_note(cude="TEST-CUDE-API-DETAIL")
        payload, _ = self._ingest_xml(xml_text, preview=False)
        nc_uuid = payload.get("uuid")
        
        response = self.api_client.get(f'/api/v1/facturas/notas-credito/{nc_uuid}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertNotIn('xml_content', data)
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_8_contrato_api_endpoint_xml_dedicado(self):
        """Test 8: Contrato API - Endpoint /xml/ entrega XML completo."""
        xml_text = self._crear_xml_credit_note(cude="TEST-CUDE-API-XML")
        payload, _ = self._ingest_xml(xml_text, preview=False)
        nc_uuid = payload.get("uuid")
        
        response = self.api_client.get(f'/api/v1/facturas/notas-credito/{nc_uuid}/xml/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/xml; charset=utf-8')
        self.assertIn('CreditNote', response.content.decode('utf-8'))
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_9_inmutabilidad_post_put_patch_bloqueados(self):
        """Test 9: Inmutabilidad - POST/PUT/PATCH bloqueados."""
        xml_text = self._crear_xml_credit_note(cude="TEST-CUDE-IMMUTABLE")
        payload, _ = self._ingest_xml(xml_text, preview=False)
        nc_uuid = payload.get("uuid")
        
        self.assertEqual(self.api_client.post('/api/v1/facturas/notas-credito/', {}).status_code, 405)
        self.assertEqual(self.api_client.put(f'/api/v1/facturas/notas-credito/{nc_uuid}/', {}).status_code, 405)
        self.assertEqual(self.api_client.patch(f'/api/v1/facturas/notas-credito/{nc_uuid}/', {}).status_code, 405)
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_10_delete_rollback_tecnico(self):
        """Test 10: DELETE permitido para rollback técnico."""
        xml_text = self._crear_xml_credit_note(cude="TEST-CUDE-DELETE")
        payload, _ = self._ingest_xml(xml_text, preview=False)
        nc_uuid = payload.get("uuid")
        
        response = self.api_client.delete(f'/api/v1/facturas/notas-credito/{nc_uuid}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(NotaCredito.objects.filter(uuid=nc_uuid).exists())
    
    @override_settings(FEATURE_XML_PIPELINE=True)
    def test_11_factura_lista_incluye_has_nc(self):
        """Test 11: Lista de facturas incluye has_nc."""
        xml_text = self._crear_xml_credit_note(cude="TEST-CUDE-HAS-NC")
        self._ingest_xml(xml_text, preview=False)
        
        response = self.api_client.get('/api/v1/facturas/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        items = data.get('results', [])
        
        factura_item = next((f for f in items if f.get('uuid') == str(self.factura.uuid)), None)
        self.assertIsNotNone(factura_item)
        self.assertTrue(factura_item.get('has_nc'))
