"""
Tests for facturas.services consuming xml_ingest service.

# WARNING: INTEGRATION TESTS: Verify that importar_ubl_sync invokes ingest_ubl_sync
and then materializes correctly.
"""
from unittest.mock import patch

from django_tenants.test.cases import TenantTestCase

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, FacturaAnexos
from apps.tenant.facturas.services import importar_ubl_sync


class ServicesIngestIntegrationTests(TenantTestCase):
    """Test that facturas.services consumes xml_ingest correctly."""
    
    def setUp(self):
        super().setUp()
        Empresa.objects.create(
            razon_social="SINTEL",
            nit="901123299",
            dv="1",
            direccion="Calle 123",
            telefono="3001234567",
        )
    
    def test_importar_ubl_sync_invokes_ingest_ubl_sync(self):
        """Verify that importar_ubl_sync calls ingest_ubl_sync from xml_ingest."""
        xml_bytes = b'<?xml version="1.0"?><Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"><cbc:ID>FV-001</cbc:ID><cbc:IssueDate>2026-01-30</cbc:IssueDate><cac:AccountingSupplierParty><cac:Party><cac:PartyTaxScheme><cbc:CompanyID>901123299</cbc:CompanyID><cbc:RegistrationName>SINTEL</cbc:RegistrationName></cac:PartyTaxScheme></cac:Party></cac:AccountingSupplierParty><cac:AccountingCustomerParty><cac:Party><cac:PartyTaxScheme><cbc:CompanyID>900298074</cbc:CompanyID><cbc:RegistrationName>GVS</cbc:RegistrationName></cac:PartyTaxScheme></cac:Party></cac:AccountingCustomerParty><cac:LegalMonetaryTotal><cbc:TaxExclusiveAmount>1000.00</cbc:TaxExclusiveAmount><cbc:TaxInclusiveAmount>1190.00</cbc:TaxInclusiveAmount><cbc:PayableAmount>1190.00</cbc:PayableAmount></cac:LegalMonetaryTotal></Invoice>'
        
        with patch('apps.tenant.facturas.services.ingest_ubl_sync') as mock_ingest:
            mock_ingest.return_value = ({
                'numero': 'FV-001',
                'prefijo': 'FV',
                'consecutivo': 1,
                'fecha_emision': '2026-01-30T00:00:00-05:00',
                'emisor_nit': '901123299',
                'emisor_razon_social': 'SINTEL',
                'receptor_nit': '900298074',
                'receptor_razon_social': 'GVS',
                'moneda': 'COP',
                'subtotal': 1000.00,
                'impuestos': 190.00,
                'total': 1190.00,
                'cufe': None,
                'naturaleza': None,
                'ubl_xml': xml_bytes.decode('utf-8'),
                'application_response_xml': None,
            }, 200)
            
            payload, code = importar_ubl_sync(xml_bytes)
            
            # Verify ingest_ubl_sync was called
            mock_ingest.assert_called_once_with(xml_bytes)
            
            # Verify factura was created
            self.assertIn(code, (200, 201))
            self.assertTrue(Factura.objects.filter(numero='FV-001').exists())
            
            factura = Factura.objects.get(numero='FV-001')
            self.assertEqual(factura.naturaleza, Factura.Naturaleza.VENTA)  # Emisor == Empresa
            
            # Verify anexos were created (if persist_anexos=True)
            self.assertTrue(FacturaAnexos.objects.filter(factura=factura).exists())
            anexos = FacturaAnexos.objects.get(factura=factura)
            self.assertIsNotNone(anexos.ubl_xml)
    
    def test_importar_ubl_sync_handles_parse_error(self):
        """Verify that importar_ubl_sync handles parse errors from ingest_ubl_sync."""
        xml_bytes = b'<invalid>xml'
        
        with patch('apps.tenant.facturas.services.ingest_ubl_sync', side_effect=Exception("Parse error")):
            payload, code = importar_ubl_sync(xml_bytes)
            
            # Should return error response
            self.assertEqual(code, 422)
            self.assertIn('error', payload)
            self.assertIn('parse_error', payload['error'])
