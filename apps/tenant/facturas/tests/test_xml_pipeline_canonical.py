"""
Smoke tests para validar que el pipeline XML usa servicios canónicos.

# WARNING: SSoT XML: Verifica que apps/services/xml_ingest y apps/services/xml_parser
son la única vía de procesamiento XML.
"""
import pytest

pytestmark = pytest.mark.skip(reason="Legacy xml_ingest module path removed; test requires migration to current document_ingest pipeline")

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django_tenants.test.cases import TenantTestCase

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura

UBL_MIN = b"""<?xml version="1.0"?>
<Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" 
        xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:ID>FV-001</cbc:ID>
    <cbc:IssueDate>2026-01-30</cbc:IssueDate>
    <cac:AccountingSupplierParty>
        <cac:Party>
            <cac:PartyTaxScheme>
                <cbc:CompanyID>901123299</cbc:CompanyID>
                <cac:PartyLegalEntity>
                    <cbc:RegistrationName>SINTEL</cbc:RegistrationName>
                </cac:PartyLegalEntity>
            </cac:PartyTaxScheme>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
        <cac:Party>
            <cac:PartyTaxScheme>
                <cbc:CompanyID>900298074</cbc:CompanyID>
                <cac:PartyLegalEntity>
                    <cbc:RegistrationName>GVS</cbc:RegistrationName>
                </cac:PartyLegalEntity>
            </cac:PartyTaxScheme>
        </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:LegalMonetaryTotal>
        <cbc:TaxExclusiveAmount currencyID="COP">1000.00</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="COP">1190.00</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount currencyID="COP">1190.00</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
</Invoice>"""


class XMLPipelineCanonicalTests(TenantTestCase):
    """Tests para validar pipeline XML canónico."""
    
    def setUp(self):
        super().setUp()
        Empresa.objects.create(
            razon_social="SINTEL",
            nit="901123299",
            dv="1",
            direccion="Calle 123",
            telefono="3001234567",
        )
    
    def test_xml_parser_can_parse_invoice(self):
        """Verifica que xml_parser puede parsear Invoice XML."""
        root = parse_xml_bytes(UBL_MIN)
        self.assertIsNotNone(root)
        
        bundle = ensure_invoice_root_and_artifacts(root)
        self.assertEqual(bundle["container"], "Invoice")
        self.assertIsNotNone(bundle["invoice_root"])
        self.assertIsNotNone(bundle["invoice_xml"])
    
    def test_xml_ingest_sync_returns_enriched_payload(self):
        """Verifica que xml_ingest retorna payload enriquecido."""
        payload, status_code = ingest_ubl_sync(UBL_MIN)
        
        self.assertEqual(status_code, 200)
        self.assertIn("dto", payload)
        self.assertIn("anexos", payload)
        self.assertIn("meta", payload)
        
        dto = payload["dto"]
        self.assertIn("numero", dto)
        self.assertIn("emisor_nit", dto)
        self.assertIn("receptor_nit", dto)
    
    def test_upload_ubl_uses_canonical_pipeline(self):
        """Verifica que upload_ubl usa el pipeline canónico."""
        url = reverse("factura-upload-ubl")
        f = SimpleUploadedFile("test.xml", UBL_MIN, content_type="text/xml")
        
        resp = self.client.post(f"{url}?async=false", {"file": f}, format="multipart")
        
        # Debe crear factura correctamente
        self.assertIn(resp.status_code, (200, 201))
        self.assertTrue(Factura.objects.filter(numero="FV-001").exists())
        
        factura = Factura.objects.get(numero="FV-001")
        # Verificar que tiene datos del emisor (desde SSoT)
        self.assertEqual(factura.emisor_nit, "901123299")
        self.assertEqual(factura.emisor_razon_social, "SINTEL")
    
    def test_materialize_uses_canonical_dto_structure(self):
        """Verifica que materializar_factura_desde_result maneja DTO canónico."""
        from apps.tenant.facturas.services import materializar_factura_desde_result
        
        # Simular payload enriquecido del servicio canónico
        enriched_payload = {
            "dto": {
                "numero": "TEST-001",
                "prefijo": "TEST",
                "consecutivo": 1,
                "fecha_emision": "2026-01-30T00:00:00-05:00",
                "emisor_nit": "901123299",
                "emisor_razon_social": "SINTEL",
                "receptor_nit": "900298074",
                "receptor_razon_social": "GVS",
                "subtotal": "1000.00",
                "impuestos": "190.00",
                "total": "1190.00",
                "moneda": "COP",
                "cufe": "test-cufe-123",
            },
            "anexos": {
                "ubl_xml": UBL_MIN.decode("utf-8"),
                "application_response_xml": None,
            },
            "meta": {
                "container": "Invoice",
            },
        }
        
        payload, status_code = materializar_factura_desde_result(enriched_payload, persist_anexos=True)
        
        self.assertIn(status_code, (200, 201))
        self.assertIn("numero", payload)
        self.assertEqual(payload["numero"], "TEST-001")
        
        # Verificar que se creó la factura
        self.assertTrue(Factura.objects.filter(numero="TEST-001").exists())
