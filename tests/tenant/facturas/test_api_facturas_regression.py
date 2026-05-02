"""
Tests de regresión para upload de facturas UBL.

Verifica que:
- Errores de parsing retornen 400 (dto_parse_error) y no 500
- Rutas con local-name() y predicados funcionen correctamente (usando .xpath())
- Logging con extra no cause KeyError por colisión con campos reservados de LogRecord
"""
import io
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from tests.tenant.base_test import SintelTenantTestCase
from apps.tenant.empresa.models import Empresa


# XML mínimo de control (Invoice válido)
SAMPLE_OK = ("""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:ID>TST-OK</cbc:ID>
  <cbc:UUID>CUFE-TST-OK</cbc:UUID>
  <cbc:IssueDate>2026-01-20</cbc:IssueDate>
  <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty><cac:PartyTaxScheme>
    <cbc:RegistrationName>EMISOR</cbc:RegistrationName><cbc:CompanyID>900</cbc:CompanyID>
  </cac:PartyTaxScheme></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:PartyTaxScheme>
    <cbc:RegistrationName>RECEPTOR</cbc:RegistrationName><cbc:CompanyID>901</cbc:CompanyID>
  </cac:PartyTaxScheme></cac:AccountingCustomerParty>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="COP">100.00</cbc:LineExtensionAmount>
    <cbc:PayableAmount currencyID="COP">119.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:TaxTotal><cbc:TaxAmount currencyID="COP">19.00</cbc:TaxAmount></cac:TaxTotal>
</Invoice>""").encode('utf-8')

# Caso error: documento que forzaba 'invalid predicate' con .find()
# Ahora debe responder 400 dto_parse_error (y no 500).
INVALID_WRAPPER = ("""<?xml version="1.0" encoding="UTF-8"?>
<Root xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
      xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <!-- No es Invoice ni AttachedDocument válido -->
  <cbc:ID>NOPE</cbc:ID>
</Root>""").encode('utf-8')


@pytest.mark.django_db
class TestFacturasAPIRegression(SintelTenantTestCase):
    """
    Tests de regresión para upload de facturas UBL.
    """
    
    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        # Crear empresa para que las facturas puedan usar datos del emisor
        self.empresa = Empresa.objects.create(
            razon_social="Empresa Test",
            nit="900123456",
            dv="7",
            moneda="COP"
        )
        
        # Crear APIClient autenticado
        self.api_client = APIClient(HTTP_HOST=self.domain.domain)
        self.api_client.force_authenticate(user=self.user)
    
    def test_upload_ok_preview_returns_200(self):
        """
        Upload de XML válido en modo preview debe retornar 200 (no 500).
        Valida que XPath con local-name() funcione correctamente.
        """
        url = reverse("factura-upload-ubl") + "?preview=true"
        f = io.BytesIO(SAMPLE_OK)
        f.name = "ok.xml"
        r = self.api_client.post(
            url,
            data={"file": f, "naturaleza": "VENTA"},
            format="multipart"
        )
        assert r.status_code == status.HTTP_200_OK, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert "error" not in data
        assert data["numero"] == "TST-OK"
    
    def test_upload_invalid_is_400_not_500(self):
        """
        Upload de XML inválido debe retornar 400 dto_parse_error (no 500).
        
        Este test valida que:
        - Rutas con local-name() y predicados no causen 'invalid predicate' errors (500)
        - Logging con extra no cause KeyError por colisión con campos reservados
        """
        url = reverse("factura-upload-ubl")
        f = io.BytesIO(INVALID_WRAPPER)
        f.name = "bad.xml"
        r = self.api_client.post(
            url,
            data={"file": f, "naturaleza": "VENTA"},
            format="multipart"
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST, f"Expected 400, got {r.status_code}"
        data = r.json()
        assert data["error"] == "dto_parse_error"
        assert "message" in data
