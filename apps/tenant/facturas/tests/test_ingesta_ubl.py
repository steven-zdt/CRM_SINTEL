import pytest
from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from apps.tenant.facturas.models import Factura
from apps.tenant.facturas.tasks import procesar_factura_xml_task
from apps.tenant.facturas.utils.ubl_parser import fast_get_cufe

XML_SAMPLE = b'''
<Invoice xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:ID>F001</cbc:ID>
  <cbc:UUID>1234567890ABCDEFGHIJKLMN</cbc:UUID>
  <cbc:IssueDate>2026-03-25</cbc:IssueDate>
  <cbc:IssueTime>12:00:00</cbc:IssueTime>
  <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>900123456</cbc:CompanyID>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Proveedor S.A.S.</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>901999888</cbc:CompanyID>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Mi Empresa S.A.S.</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:LegalMonetaryTotal>
    <cbc:TaxExclusiveAmount>100000.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount>119000.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount>119000.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:InvoiceLine>
    <cbc:ID>1</cbc:ID>
    <cbc:InvoicedQuantity unitCode="UND">1</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount>100000.00</cbc:LineExtensionAmount>
    <cac:Item>
      <cbc:Description>Producto de prueba</cbc:Description>
      <cac:SellersItemIdentification>
        <cbc:ID>PROD001</cbc:ID>
      </cac:SellersItemIdentification>
    </cac:Item>
    <cac:Price>
      <cbc:PriceAmount>100000.00</cbc:PriceAmount>
    </cac:Price>
  </cac:InvoiceLine>
</Invoice>
'''

class TestFacturaIngestion(TenantTestCase):
    @pytest.mark.django_db
    def test_fast_get_cufe(self):
        cufe = fast_get_cufe(XML_SAMPLE)
        assert cufe == "1234567890ABCDEFGHIJKLMN"

    @pytest.mark.django_db
    def test_procesar_factura_xml_task(self):
      from apps.tenant.empresa.models import Empresa
      User = get_user_model()
      user = User.objects.create(username="tester", email="tester@example.com")
      # Crear Empresa dummy si no existe
      empresa = Empresa.objects.first()
      if not empresa:
        empresa = Empresa.objects.create(
          razon_social="Empresa Test",
          nit="900000001",
          dv="1",
          direccion="Calle 123",
          telefono="1234567",
          email_contacto="test@empresa.com",
          regimen_tributario="NO_RESPONDE",
          moneda="COP"
        )
      empresa_id = empresa.id
      usuario_id = user.id
      # Ejecutar tarea de forma síncrona para test
      procesar_factura_xml_task(XML_SAMPLE.decode(), empresa_id, usuario_id)
      factura = Factura.objects.filter(cufe="1234567890ABCDEFGHIJKLMN", empresa_id=empresa_id).first()
      assert factura is not None
      assert factura.numero == "F001"
      assert factura.total == 119000
      assert factura.emisor_nit == "900123456"
      assert factura.receptor_nit == "901999888"
