"""
Tests tenant-aware para importar_ubl (Service Layer).

# WARNING: TENANT TESTS: Requieren base de datos y tenant (TenantTestCase).
"""
from django_tenants.test.cases import TenantTestCase

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, NaturalezaFactura
from apps.tenant.facturas.services import importar_ubl

# F27 (CORREGIR): las fixtures originales usaban
# AccountingSupplierParty/CustomerParty > Party > PartyIdentification > ID
# para el NIT -- el parser real (apps/services/document_parser/xml_parser/
# parser.py, mismo patron usado en test_nota_credito_pipeline.py) lee el NIT
# desde Party > PartyTaxScheme > CompanyID, no PartyIdentification. Con la
# estructura vieja, emisor.nit/receptor.nit llegaban vacios ("") al DTO y
# ingest_document() rechazaba el documento con
# missing_required_fields: emisor.nit, receptor.nit -- confirmado
# reproduciendo ingest_document() directamente via manage.py shell.
XML_VENTA = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>FST354</cbc:ID>
  <cbc:IssueDate>2026-01-01</cbc:IssueDate>
  <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyTaxScheme>
        <cbc:RegistrationName>SINTEL TECNOLOGY SAS</cbc:RegistrationName>
        <cbc:CompanyID schemeAgencyID="195" schemeID="4">901123299</cbc:CompanyID>
        <cac:TaxScheme><cbc:ID>01</cbc:ID></cac:TaxScheme>
      </cac:PartyTaxScheme>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyTaxScheme>
        <cbc:RegistrationName>CLIENTE TEST</cbc:RegistrationName>
        <cbc:CompanyID schemeAgencyID="195" schemeID="4">800765432</cbc:CompanyID>
        <cac:TaxScheme><cbc:ID>01</cbc:ID></cac:TaxScheme>
      </cac:PartyTaxScheme>
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
      <cac:PartyTaxScheme>
        <cbc:RegistrationName>PROVEEDOR TEST</cbc:RegistrationName>
        <cbc:CompanyID schemeAgencyID="195" schemeID="4">860030723</cbc:CompanyID>
        <cac:TaxScheme><cbc:ID>01</cbc:ID></cac:TaxScheme>
      </cac:PartyTaxScheme>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyTaxScheme>
        <cbc:RegistrationName>SINTEL TECNOLOGY SAS</cbc:RegistrationName>
        <cbc:CompanyID schemeAgencyID="195" schemeID="4">901123299</cbc:CompanyID>
        <cac:TaxScheme><cbc:ID>01</cbc:ID></cac:TaxScheme>
      </cac:PartyTaxScheme>
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
        """
        Test: Retorna 422 si no hay Empresa configurada.

        F27 (CORREGIR, contrato cambiado): el pipeline universal
        (`ingest_document()`) es deliberadamente agnostico de dominio en
        preview -- no valida Empresa en absoluto (confirmado: con
        `preview=True` y 0 Empresa en el tenant, retorna 200
        `document_ingest_preview_ok`, no 422). La validacion de Empresa
        solo ocurre al persistir (`guardar_desde_dto()`), asi que este test
        debe ejercitar `preview=False` para seguir probando el escenario
        real que su nombre describe.
        """
        # Eliminar empresa
        Empresa.objects.all().delete()

        payload, code = importar_ubl(XML_VENTA, preview=False)
        self.assertEqual(code, 422)
        self.assertEqual(payload["error"], "empresa_no_configurada")
        self.assertIn("message", payload)
    
    def test_200_con_empresa_y_venta(self):
        """
        Test: Preview de factura VENTA (emisor == empresa).

        F27 (CORREGIR, contrato cambiado): el pipeline universal
        (`ingest_document()`, `FEATURE_DOCUMENT_PIPELINE=True` por defecto)
        es deliberadamente agnostico de dominio en preview -- no calcula
        `naturaleza` (eso ocurre despues, en `guardar_desde_dto()`, dentro
        del bloque de persistencia). El payload real de preview es
        `{"persisted": False, "dto": {...}, ...}`, no
        `{"preview": True, "factura": {...}}`. Se corrige la aserción para
        reflejar lo que preview SI garantiza hoy: no persiste, y el DTO
        extrae correctamente el numero del documento.
        """
        payload, code = importar_ubl(XML_VENTA, preview=True)
        self.assertEqual(code, 200)
        self.assertFalse(payload.get("persisted", True))
        self.assertEqual(payload["dto"]["numero"], "FST354")
        self.assertFalse(Factura.objects.exists())

    def test_preview_compra(self):
        """Test: Preview de factura COMPRA (emisor != empresa) -- ver nota en test_200_con_empresa_y_venta."""
        payload, code = importar_ubl(XML_COMPRA, preview=True)
        self.assertEqual(code, 200)
        self.assertFalse(payload.get("persisted", True))
        self.assertEqual(payload["dto"]["numero"], "BOG1299136")
        self.assertFalse(Factura.objects.exists())

    def test_persistencia_asigna_naturaleza_venta(self):
        """
        Test: Persistencia asigna naturaleza VENTA correctamente.

        F27 (CORREGIR): `guardar_desde_dto()` retorna `naturaleza` en el
        nivel superior del payload (`business_service.py:814-822`), no
        anidado bajo una clave "factura" que nunca existio en ese contrato.
        """
        payload, code = importar_ubl(XML_VENTA, preview=False)
        self.assertEqual(code, 201)
        self.assertTrue(payload.get("created"))
        self.assertTrue(Factura.objects.exists())
        factura = Factura.objects.first()
        self.assertEqual(factura.naturaleza, NaturalezaFactura.VENTA)
        self.assertEqual(factura.numero, "FST354")
        self.assertEqual(payload["naturaleza"], NaturalezaFactura.VENTA)

    def test_persistencia_asigna_naturaleza_compra(self):
        """Test: Persistencia asigna naturaleza COMPRA correctamente -- ver nota en test_persistencia_asigna_naturaleza_venta."""
        payload, code = importar_ubl(XML_COMPRA, preview=False)
        self.assertEqual(code, 201)
        self.assertTrue(payload.get("created"))
        self.assertTrue(Factura.objects.exists())
        factura = Factura.objects.first()
        self.assertEqual(factura.naturaleza, NaturalezaFactura.COMPRA)
        self.assertEqual(factura.numero, "BOG1299136")
        self.assertEqual(payload["naturaleza"], NaturalezaFactura.COMPRA)
