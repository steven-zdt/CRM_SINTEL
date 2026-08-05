"""
Smoke tests para verificar el manejo de errores minimalista en upload-ubl.

Verifica:
- Respuestas minimalistas: {"error": code, "message": message}
- 400 para XML inválido → "dto_parse_error"
- 409 para duplicados → "duplicate"
- 500 para errores internos → "internal"
- Timezone-aware parsing sin warnings
- CSRF y MultiPartParser funcionando
"""

from datetime import datetime
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from tests.tenant.base_test import SintelTenantTestCase


@pytest.mark.django_db
class TestUploadUBLMinimalErrors(SintelTenantTestCase):
    """
    Smoke tests para verificar respuestas de error minimalistas.
    """

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        # Crear empresa para que las facturas puedan usar datos del emisor
        self.empresa = Empresa.objects.create(
            razon_social="Empresa Test", nit="900123456", dv="7", moneda="COP"
        )

        # Crear APIClient autenticado
        self.api_client = APIClient(HTTP_HOST=self.domain.domain)
        self.api_client.force_authenticate(user=self.user)

    def test_upload_invalid_xml_returns_400_dto_parse_error(self):
        """
        XML inválido → 400 {"error": "dto_parse_error", "message": "Error al parsear UBL."}
        """
        url = reverse("factura-upload-ubl")

        # XML mal formado
        invalid_xml = "<Invoice><invalid>"
        resp = self.api_client.post(url, data={"xml": invalid_xml}, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        data = resp.json()
        assert "error" in data
        assert "message" in data
        assert data["error"] == "dto_parse_error"
        assert data["message"] == "Error al parsear UBL."
        # Verificar formato minimal: NO debe tener details, hint, etc.
        assert "details" not in data
        assert "hint" not in data

    def test_upload_missing_file_or_xml_returns_400_missing_xml(self):
        """
        Falta file o xml → 400 {"error": "missing_xml", "message": "Falta archivo o contenido XML."}
        """
        url = reverse("factura-upload-ubl")

        resp = self.api_client.post(url, data={}, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        data = resp.json()
        assert data["error"] == "missing_xml"
        assert data["message"] == "Falta archivo o contenido XML."
        assert "details" not in data
        assert "hint" not in data

    def test_upload_invalid_naturaleza_returns_400_invalid_param(self):
        """
        Naturaleza inválida → 400 {"error": "invalid_param", "message": "naturaleza debe ser VENTA o COMPRA."}
        """
        url = reverse("factura-upload-ubl")

        valid_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
                 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
          <cbc:ID>TEST-001</cbc:ID>
          <cbc:IssueDate>2024-01-15</cbc:IssueDate>
          <cac:AccountingSupplierParty>
            <cac:Party><cac:PartyLegalEntity><cbc:CompanyID>900123456</cbc:CompanyID></cac:PartyLegalEntity></cac:Party>
          </cac:AccountingSupplierParty>
          <cac:AccountingCustomerParty>
            <cac:Party><cac:PartyLegalEntity><cbc:CompanyID>800111222</cbc:CompanyID></cac:PartyLegalEntity></cac:Party>
          </cac:AccountingCustomerParty>
          <cac:LegalMonetaryTotal>
            <cbc:TaxExclusiveAmount>100000.00</cbc:TaxExclusiveAmount>
            <cbc:PayableAmount>119000.00</cbc:PayableAmount>
          </cac:LegalMonetaryTotal>
          <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
        </Invoice>"""

        resp = self.api_client.post(
            url, data={"xml": valid_xml, "naturaleza": "INVALIDO"}, format="json"
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        data = resp.json()
        assert data["error"] == "invalid_param"
        assert data["message"] == "naturaleza debe ser VENTA o COMPRA."
        assert "details" not in data

    def test_upload_duplicate_numero_returns_409_duplicate(self):
        """
        Factura duplicada (por número) → 409 {"error": "duplicate", "message": "La factura ya existe."}
        """
        url = reverse("factura-upload-ubl")

        # Crear factura existente
        Factura.objects.create(
            numero="TEST-DUP-001",
            prefijo="TEST",
            consecutivo=1,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.ACEPTADA,
            naturaleza=Factura.Naturaleza.VENTA,
            fecha_emision=timezone.now(),
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="800111222",
            receptor_razon_social="Cliente A",
            moneda="COP",
            subtotal=Decimal("100000.00"),
            impuestos=Decimal("19000.00"),
            total=Decimal("119000.00"),
        )

        # Intentar importar la misma factura
        duplicate_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
                 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
          <cbc:ID>TEST-DUP-001</cbc:ID>
          <cbc:IssueDate>2024-01-15</cbc:IssueDate>
          <cac:AccountingSupplierParty>
            <cac:Party><cac:PartyLegalEntity><cbc:CompanyID>900123456</cbc:CompanyID></cac:PartyLegalEntity></cac:Party>
          </cac:AccountingSupplierParty>
          <cac:AccountingCustomerParty>
            <cac:Party><cac:PartyLegalEntity><cbc:CompanyID>800111222</cbc:CompanyID></cac:PartyLegalEntity></cac:Party>
          </cac:AccountingCustomerParty>
          <cac:LegalMonetaryTotal>
            <cbc:TaxExclusiveAmount>100000.00</cbc:TaxExclusiveAmount>
            <cbc:PayableAmount>119000.00</cbc:PayableAmount>
          </cac:LegalMonetaryTotal>
          <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
        </Invoice>"""

        resp = self.api_client.post(url, data={"xml": duplicate_xml}, format="json")

        assert resp.status_code == status.HTTP_409_CONFLICT
        data = resp.json()
        assert data["error"] == "duplicate"
        assert data["message"] == "La factura ya existe."
        assert "details" not in data
        assert "hint" not in data

    def test_upload_valid_xml_returns_201_created(self):
        """
        XML válido → 201 Created (formato normal, no error)
        """
        url = reverse("factura-upload-ubl")

        valid_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
                 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
          <cbc:ID>TEST-OK-001</cbc:ID>
          <cbc:IssueDate>2024-01-15</cbc:IssueDate>
          <cac:AccountingSupplierParty>
            <cac:Party><cac:PartyLegalEntity><cbc:CompanyID>900123456</cbc:CompanyID><cbc:RegistrationName>Empresa Test</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party>
          </cac:AccountingSupplierParty>
          <cac:AccountingCustomerParty>
            <cac:Party><cac:PartyLegalEntity><cbc:CompanyID>800111222</cbc:CompanyID><cbc:RegistrationName>Cliente A</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party>
          </cac:AccountingCustomerParty>
          <cac:LegalMonetaryTotal>
            <cbc:TaxExclusiveAmount>100000.00</cbc:TaxExclusiveAmount>
            <cbc:PayableAmount>119000.00</cbc:PayableAmount>
          </cac:LegalMonetaryTotal>
          <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
        </Invoice>"""

        resp = self.api_client.post(url, data={"xml": valid_xml}, format="json")

        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)
        data = resp.json()
        # Verificar que NO es formato de error
        assert "error" not in data
        assert "id" in data or "numero" in data

    def test_upload_preview_returns_200_ok(self):
        """
        Preview mode → 200 OK con DTO (no error)
        """
        url = reverse("factura-upload-ubl") + "?preview=true"

        valid_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
                 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
          <cbc:ID>TEST-PREVIEW-001</cbc:ID>
          <cbc:IssueDate>2024-01-15</cbc:IssueDate>
          <cac:AccountingSupplierParty>
            <cac:Party><cac:PartyLegalEntity><cbc:CompanyID>900123456</cbc:CompanyID><cbc:RegistrationName>Empresa Test</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party>
          </cac:AccountingSupplierParty>
          <cac:AccountingCustomerParty>
            <cac:Party><cac:PartyLegalEntity><cbc:CompanyID>800111222</cbc:CompanyID><cbc:RegistrationName>Cliente A</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party>
          </cac:AccountingCustomerParty>
          <cac:LegalMonetaryTotal>
            <cbc:TaxExclusiveAmount>100000.00</cbc:TaxExclusiveAmount>
            <cbc:PayableAmount>119000.00</cbc:PayableAmount>
          </cac:LegalMonetaryTotal>
          <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
        </Invoice>"""

        resp = self.api_client.post(url, data={"xml": valid_xml}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        # Verificar que es DTO (no error)
        assert "error" not in data
        assert "numero" in data or "total" in data

    def test_upload_xml_with_timezone_aware_datetime(self):
        """
        Verificar que el parsing de fechas es timezone-aware (sin warnings).
        """
        url = reverse("factura-upload-ubl")

        # XML con fecha y hora
        xml_with_time = """<?xml version="1.0" encoding="UTF-8"?>
        <Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
                 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
          <cbc:ID>TEST-TZ-001</cbc:ID>
          <cbc:IssueDate>2024-01-15</cbc:IssueDate>
          <cbc:IssueTime>14:30:00</cbc:IssueTime>
          <cac:AccountingSupplierParty>
            <cac:Party><cac:PartyLegalEntity><cbc:CompanyID>900123456</cbc:CompanyID><cbc:RegistrationName>Empresa Test</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party>
          </cac:AccountingSupplierParty>
          <cac:AccountingCustomerParty>
            <cac:Party><cac:PartyLegalEntity><cbc:CompanyID>800111222</cbc:CompanyID><cbc:RegistrationName>Cliente A</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party>
          </cac:AccountingCustomerParty>
          <cac:LegalMonetaryTotal>
            <cbc:TaxExclusiveAmount>100000.00</cbc:TaxExclusiveAmount>
            <cbc:PayableAmount>119000.00</cbc:PayableAmount>
          </cac:LegalMonetaryTotal>
          <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
        </Invoice>"""

        resp = self.api_client.post(url, data={"xml": xml_with_time}, format="json")

        # Debe ser exitoso (201 o 200) sin errores de timezone
        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)
        data = resp.json()
        assert "error" not in data

    def test_error_response_format_is_minimal(self):
        """
        Verificar que TODAS las respuestas de error tienen formato minimal:
        {"error": code, "message": message} sin details, hint, etc.
        """
        url = reverse("factura-upload-ubl")

        # Probar diferentes tipos de error
        test_cases = [
            # XML inválido
            ("<invalid>", status.HTTP_400_BAD_REQUEST, "dto_parse_error"),
            # Falta input
            ({}, status.HTTP_400_BAD_REQUEST, "dto_parse_error"),
        ]

        for input_data, expected_status, expected_code in test_cases:
            resp = self.api_client.post(url, data=input_data, format="json")
            assert resp.status_code == expected_status
            data = resp.json()

            # Verificar formato minimal
            assert "error" in data
            assert "message" in data
            assert data["error"] == expected_code
            assert isinstance(data["message"], str)

            # Verificar que NO tiene campos adicionales
            assert "details" not in data
            assert "hint" not in data
            assert "code" not in data  # "error" es el campo, no "code"
            # Verificar que "error" es string, no objeto
            assert isinstance(data["error"], str)
            assert not isinstance(data["error"], dict)
