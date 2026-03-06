"""
Tests tenant-aware para importar_ubl (Service Layer).

⚠️ TENANT TESTS: Requieren base de datos y tenant (TenantTestCase).
"""
from django_tenants.test.cases import TenantTestCase
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.services import importar_ubl
from apps.tenant.facturas.models import Factura, NaturalezaFactura


XML_VENTA = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>FST354</cbc:ID>
  <cbc:IssueDate>2026-01-01</cbc:IssueDate>
  <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyIdentification>
        <cbc:ID schemeID="31">901123299</cbc:ID>
      </cac:PartyIdentification>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>SINTEL TECNOLOGY SAS</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyIdentification>
        <cbc:ID schemeID="31">800765432</cbc:ID>
      </cac:PartyIdentification>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>CLIENTE TEST</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:LegalMonetaryTotal>
    <cbc:TaxExclusiveAmount currencyID="COP">10000</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="COP">11900</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="COP">11900</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
</Invoice>"""

XML_COMPRA = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>BOG1299136</cbc:ID>
  <cbc:IssueDate>2026-01-01</cbc:IssueDate>
  <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyIdentification>
        <cbc:ID schemeID="31">860030723</cbc:ID>
      </cac:PartyIdentification>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>PROVEEDOR TEST</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyIdentification>
        <cbc:ID schemeID="31">901123299</cbc:ID>
      </cac:PartyIdentification>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>SINTEL TECNOLOGY SAS</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:LegalMonetaryTotal>
    <cbc:TaxExclusiveAmount currencyID="COP">1076400</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="COP">1280916</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="COP">1280916</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
</Invoice>"""


class ImportarUblServiceTests(TenantTestCase):
    """Tests para importar_ubl con preview y persistencia."""
    
    def setUp(self):
        super().setUp()
        # Crear empresa del tenant (SSoT)
        self.empresa = Empresa.objects.create(
            razon_social="SINTEL TECNOLOGY SAS",
            nit="901123299",
            dv="1",
            direccion="Calle 123",
            telefono="1234567890"
        )
    
    def test_422_sin_empresa(self):
        """Test: Retorna 422 si no hay Empresa configurada."""
        # Eliminar empresa
        Empresa.objects.all().delete()
        
        payload, code = importar_ubl(XML_VENTA, preview=True)
        self.assertEqual(code, 422)
        self.assertEqual(payload["error"], "empresa_no_configurada")
        self.assertIn("message", payload)
    
    def test_200_con_empresa_y_venta(self):
        """Test: Preview de factura VENTA (emisor == empresa)."""
        payload, code = importar_ubl(XML_VENTA, preview=True)
        self.assertEqual(code, 200)
        self.assertTrue(payload["preview"])
        self.assertEqual(payload["factura"]["naturaleza"], NaturalezaFactura.VENTA)
        self.assertEqual(payload["factura"]["numero"], "FST354")
    
    def test_preview_compra(self):
        """Test: Preview de factura COMPRA (emisor != empresa)."""
        payload, code = importar_ubl(XML_COMPRA, preview=True)
        self.assertEqual(code, 200)
        self.assertTrue(payload["preview"])
        self.assertEqual(payload["factura"]["naturaleza"], NaturalezaFactura.COMPRA)
        self.assertEqual(payload["factura"]["numero"], "BOG1299136")
    
    def test_persistencia_asigna_naturaleza_venta(self):
        """Test: Persistencia asigna naturaleza VENTA correctamente."""
        payload, code = importar_ubl(XML_VENTA, preview=False)
        self.assertEqual(code, 201)
        self.assertFalse(payload["preview"])
        self.assertTrue(Factura.objects.exists())
        factura = Factura.objects.first()
        self.assertEqual(factura.naturaleza, NaturalezaFactura.VENTA)
        self.assertEqual(factura.numero, "FST354")
    
    def test_persistencia_asigna_naturaleza_compra(self):
        """Test: Persistencia asigna naturaleza COMPRA correctamente."""
        payload, code = importar_ubl(XML_COMPRA, preview=False)
        self.assertEqual(code, 201)
        self.assertFalse(payload["preview"])
        self.assertTrue(Factura.objects.exists())
        factura = Factura.objects.first()
        self.assertEqual(factura.naturaleza, NaturalezaFactura.COMPRA)
        self.assertEqual(factura.numero, "BOG1299136")
