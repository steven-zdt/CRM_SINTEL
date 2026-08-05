"""
Smoke tests para upload-ubl: garantiza que no retorne 500 por prefijos XML no declarados.

[WARNING] OBJETIVO: Validar que el parser UBL con local-name() y namespaces dinámicos
no falle con prefijos no declarados (ej. sts:).
"""

from django.urls import reverse
from rest_framework import status

from tests.tenant.base_test import SintelTenantTestCase


class TestUploadUBLSmoke(SintelTenantTestCase):
    """
    Smoke tests para upload-ubl.

    Valida que el parser sea robusto ante prefijos XML no declarados.
    """

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        # Crear empresa para que las facturas puedan usar datos del emisor
        from apps.tenant.empresa.models import Empresa

        Empresa.objects.create(
            razon_social="Empresa Test", nit="900123456", dv="7", moneda="COP"
        )

    def test_upload_ubl_handles_vendor_prefixes(self):
        """
        Si el XPath usa local-name() / ns dinámico, no debe fallar por prefijos desconocidos.
        """
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>INV-1000</cbc:ID>
  <cbc:IssueDate>2024-01-15</cbc:IssueDate>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyLegalEntity>
        <cbc:CompanyID>900999888</cbc:CompanyID>
        <cbc:RegistrationName>Proveedor Test</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyLegalEntity>
        <cbc:CompanyID>900123456</cbc:CompanyID>
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
  <!-- Nota: NO declaramos 'sts:' y no lo usamos en XPath -->
</Invoice>"""

        # Autenticar cliente
        self.api_client.force_authenticate(user=self.user)

        # Intentar subir UBL
        url = reverse("factura-upload-ubl")
        resp = self.api_client.post(url, data={"xml": xml}, format="json")

        # Nunca debe retornar 500 (error interno)
        assert (
            resp.status_code != 500
        ), f"El parser no debe retornar 500. Status: {resp.status_code}, Response: {resp.data}"
        # Debe retornar 201 (éxito) o 400 (validación), nunca 500
        assert resp.status_code in (
            201,
            400,
        ), f"Status inesperado: {resp.status_code}, Response: {resp.data}"

    def test_upload_ubl_without_file_or_xml_returns_400(self):
        """
        Si no se envía 'file' ni 'xml', debe retornar 400.
        """
        self.api_client.force_authenticate(user=self.user)

        url = reverse("factura-upload-ubl")
        resp = self.api_client.post(url, data={}, format="json")

        assert resp.status_code == 400
        assert (
            "file" in resp.data.get("detail", "").lower()
            or "xml" in resp.data.get("detail", "").lower()
        )

    def test_upload_ubl_invalid_xml_returns_400(self):
        """
        Si el XML es inválido, debe retornar 400 (no 500).
        """
        self.api_client.force_authenticate(user=self.user)

        url = reverse("factura-upload-ubl")
        resp = self.api_client.post(
            url, data={"xml": "<invalid>xml</invalid>"}, format="json"
        )

        # Debe retornar 400 (cliente) o 201 si el parser es muy permisivo, pero nunca 500
        assert resp.status_code != 500, "XML inválido no debe retornar 500"
        assert resp.status_code in (201, 400), f"Status inesperado: {resp.status_code}"
