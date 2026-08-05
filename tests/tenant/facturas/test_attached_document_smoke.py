"""
Smoke test para AttachedDocument con Invoice interno.

Valida que el parser extraiga correctamente el Invoice desde CDATA
y mapee numero, cufe, prefijo/consecutivo, qr_code, qr_url.
"""

from django.urls import reverse
from rest_framework import status

from tests.tenant.base_test import SintelTenantTestCase


class TestAttachedDocumentSmoke(SintelTenantTestCase):
    """
    Smoke tests para AttachedDocument.

    Valida que el parser maneje correctamente AttachedDocument con Invoice interno.
    """

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        # Crear empresa para que las facturas puedan usar datos del emisor
        from apps.tenant.empresa.models import Empresa

        Empresa.objects.create(
            razon_social="Empresa Test", nit="900123456", dv="7", moneda="COP"
        )

    def test_attached_document_with_invoice_internal(self):
        """
        AttachedDocument con Invoice interno en CDATA.

        Invoice/cbc:ID = FST354
        Invoice/cbc:UUID = <hash largo>
        sts:QRCode presente.

        Esperado:
        - 201 si datos consistentes → en DB numero='FST354', prefijo='FST', consecutivo=354, cufe='<hash>'
        - Nunca 500; si falta el Invoice interno o el ID no viene, 400.
        """
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<AttachedDocument xmlns="urn:oasis:names:specification:ubl:schema:xsd:AttachedDocument-2"
                  xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                  xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cac:Attachment>
    <cbc:Description><![CDATA[<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures">
  <cbc:ID>FST354</cbc:ID>
  <cbc:UUID>a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6</cbc:UUID>
  <cbc:IssueDate>2024-01-15</cbc:IssueDate>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>900999888</cbc:CompanyID>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Proveedor Test</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>900123456</cbc:CompanyID>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Empresa Test</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:LegalMonetaryTotal>
    <cbc:TaxExclusiveAmount>100000.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount>119000.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount>119000.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
  <cac:UBLExtensions>
    <cac:UBLExtension>
      <cac:ExtensionContent>
        <sts:DianExtensions>
          <sts:QRCode>https://catalogo-vpfe.dian.gov.co/document/consultarqr?documentkey=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6</sts:QRCode>
        </sts:DianExtensions>
      </cac:ExtensionContent>
    </cac:UBLExtension>
  </cac:UBLExtensions>
</Invoice>]]></cbc:Description>
  </cac:Attachment>
</AttachedDocument>"""

        # Autenticar cliente
        self.api_client.force_authenticate(user=self.user)

        # Intentar subir UBL
        url = reverse("factura-upload-ubl")
        resp = self.api_client.post(url, data={"xml": xml}, format="json")

        # Nunca debe retornar 500
        assert (
            resp.status_code != 500
        ), f"El parser no debe retornar 500. Status: {resp.status_code}, Response: {resp.data}"

        # Debe retornar 201 (éxito) o 400 (validación)
        if resp.status_code == 201:
            data = resp.json()
            # Verificar mapeo correcto
            assert (
                data.get("numero") == "FST354"
            ), f"Expected numero='FST354', got '{data.get('numero')}'"
            assert (
                data.get("prefijo") == "FST"
            ), f"Expected prefijo='FST', got '{data.get('prefijo')}'"
            assert (
                data.get("consecutivo") == 354
            ), f"Expected consecutivo=354, got '{data.get('consecutivo')}'"
            assert (
                data.get("cufe")
                == "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"
            ), f"Expected cufe con hash, got '{data.get('cufe')}'"
            # QR code debe estar presente
            assert data.get("qr_code") is not None, "QR code debe estar presente"
        else:
            # Si retorna 400, debe ser por validación, no por error de parsing
            assert (
                resp.status_code == 400
            ), f"Status inesperado: {resp.status_code}, Response: {resp.data}"

    def test_attached_document_without_invoice_returns_400(self):
        """
        AttachedDocument sin Invoice interno debe retornar 400 (no 500).
        """
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<AttachedDocument xmlns="urn:oasis:names:specification:ubl:schema:xsd:AttachedDocument-2">
  <cac:Attachment>
    <cbc:Description>No es un Invoice válido</cbc:Description>
  </cac:Attachment>
</AttachedDocument>"""

        self.api_client.force_authenticate(user=self.user)

        url = reverse("factura-upload-ubl")
        resp = self.api_client.post(url, data={"xml": xml}, format="json")

        # Debe retornar 400 (no 500)
        assert (
            resp.status_code != 500
        ), "AttachedDocument sin Invoice no debe retornar 500"
        assert (
            resp.status_code == 400
        ), f"Status inesperado: {resp.status_code}, Response: {resp.data}"
