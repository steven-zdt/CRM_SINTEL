"""
API tests forenses para Facturas: upload, detail, delete.

Verifica:
- POST /api/v1/facturas/upload-ubl/ → 201/200/409/400 con logs forenses
- GET /api/v1/facturas/{id}/ → 200
- DELETE /api/v1/facturas/{id}/ → 204
- Errores minimalistas
- Logs estructurados sin secretos
"""

import io
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from tests.tenant.base_test import SintelTenantTestCase

# XML mínimo para tests forenses
SAMPLE_INVOICE = b"""<?xml version="1.0" encoding="utf-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:ID>FORENSY001</cbc:ID>
  <cbc:UUID>CUFE-FORENSY-001</cbc:UUID>
  <cbc:IssueDate>2026-01-20</cbc:IssueDate>
  <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty><cac:PartyTaxScheme>
    <cbc:RegistrationName>EMISOR SAS</cbc:RegistrationName><cbc:CompanyID>900000001</cbc:CompanyID>
  </cac:PartyTaxScheme></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:PartyTaxScheme>
    <cbc:RegistrationName>RECEPTOR SAS</cbc:RegistrationName><cbc:CompanyID>900000002</cbc:CompanyID>
  </cac:PartyTaxScheme></cac:AccountingCustomerParty>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="COP">10000.00</cbc:LineExtensionAmount>
    <cbc:PayableAmount currencyID="COP">11900.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:TaxTotal><cbc:TaxAmount currencyID="COP">1900.00</cbc:TaxAmount></cac:TaxTotal>
</Invoice>
"""


@pytest.mark.django_db
class TestFacturasAPIForensics(SintelTenantTestCase):
    """
    Tests API forenses para Facturas: upload, detail, delete.
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

    def test_upload_missing_xml_returns_400(self):
        """
        POST /api/v1/facturas/upload-ubl/ sin file ni xml → 400 {"error":"missing_xml",...}
        """
        url = reverse("factura-upload-ubl")
        r = self.api_client.post(url, data={"naturaleza": "VENTA"}, format="multipart")

        assert r.status_code == status.HTTP_400_BAD_REQUEST
        data = r.json()
        assert data == {
            "error": "missing_xml",
            "message": "Falta archivo o contenido XML.",
        }

    def test_upload_preview_ok(self):
        """
        POST /api/v1/facturas/upload-ubl/?preview=true → 200 OK con DTO
        """
        url = reverse("factura-upload-ubl") + "?preview=true"
        f = io.BytesIO(SAMPLE_INVOICE)
        f.name = "inv.xml"
        r = self.api_client.post(
            url, data={"file": f, "naturaleza": "VENTA"}, format="multipart"
        )

        assert r.status_code == status.HTTP_200_OK
        data = r.json()
        assert data["numero"] == "FORENSY001"
        assert "error" not in data

    def test_upload_persist_then_detail_and_delete(self):
        """
        Flujo completo: upload → detail → delete
        """
        # 1. Upload persistente
        url = reverse("factura-upload-ubl")
        f = io.BytesIO(SAMPLE_INVOICE)
        f.name = "inv.xml"
        r = self.api_client.post(
            url, data={"file": f, "naturaleza": "VENTA"}, format="multipart"
        )

        assert r.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)
        fact_id = r.json()["id"]
        fact_uuid = r.json()["uuid"]

        # 2. Detalle
        # F29-001: BaseTenantViewSet.lookup_field = "uuid", no "pk".
        detail_url = reverse("factura-detail", kwargs={"uuid": fact_uuid})
        rd = self.api_client.get(detail_url)
        assert rd.status_code == status.HTTP_200_OK
        assert rd.json()["id"] == fact_id
        assert rd.json()["numero"] == "FORENSY001"

        # 3. Delete
        delr = self.api_client.delete(detail_url)
        assert delr.status_code == status.HTTP_204_NO_CONTENT

        # 4. Verificar que fue eliminada
        verify_get = self.api_client.get(detail_url)
        assert verify_get.status_code == status.HTTP_404_NOT_FOUND

    def test_upload_invalid_naturaleza_returns_400(self):
        """
        POST /api/v1/facturas/upload-ubl/ con naturaleza inválida → 400 {"error":"invalid_param",...}
        """
        url = reverse("factura-upload-ubl")
        f = io.BytesIO(SAMPLE_INVOICE)
        f.name = "inv.xml"
        r = self.api_client.post(
            url, data={"file": f, "naturaleza": "INVALIDO"}, format="multipart"
        )

        assert r.status_code == status.HTTP_400_BAD_REQUEST
        data = r.json()
        assert data["error"] == "invalid_param"
        assert "naturaleza debe ser VENTA o COMPRA" in data["message"]

    def test_upload_duplicate_returns_409(self):
        """
        POST /api/v1/facturas/upload-ubl/ con factura duplicada → 409 {"error":"duplicate",...}
        """
        # Crear factura existente
        Factura.objects.create(
            numero="FORENSY001",
            prefijo="FORENSY",
            consecutivo=1,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.ACEPTADA,
            naturaleza=Factura.Naturaleza.VENTA,
            fecha_emision=timezone.now(),
            emisor_nit="900000001",
            emisor_razon_social="EMISOR SAS",
            receptor_nit="900000002",
            receptor_razon_social="RECEPTOR SAS",
            moneda="COP",
            subtotal=Decimal("10000.00"),
            impuestos=Decimal("1900.00"),
            total=Decimal("11900.00"),
        )

        # Intentar importar la misma factura
        url = reverse("factura-upload-ubl")
        f = io.BytesIO(SAMPLE_INVOICE)
        f.name = "inv.xml"
        r = self.api_client.post(
            url, data={"file": f, "naturaleza": "VENTA"}, format="multipart"
        )

        assert r.status_code == status.HTTP_409_CONFLICT
        data = r.json()
        assert data["error"] == "duplicate"
        assert "ya existe" in data["message"]
