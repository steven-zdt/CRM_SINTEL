"""
API tests end-to-end para Facturas: upload, detail, delete.

Verifica:
- POST /api/v1/facturas/upload-ubl/ → 201/200/409/400
- GET /api/v1/facturas/{id}/ → 200
- DELETE /api/v1/facturas/{id}/ → 204
- Errores minimalistas
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from decimal import Decimal
from django.utils import timezone
from datetime import datetime
from tests.tenant.base_test import SintelTenantTestCase
from apps.tenant.facturas.models import Factura
from apps.tenant.empresa.models import Empresa


@pytest.mark.django_db
class TestFacturasAPIE2E(SintelTenantTestCase):
    """
    Tests API end-to-end para Facturas: upload, detail, delete.
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
    
    def test_upload_ubl_valid_xml_returns_201(self):
        """
        POST /api/v1/facturas/upload-ubl/ con XML válido → 201 Created
        """
        url = reverse('factura-upload-ubl')
        
        valid_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
                 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
          <cbc:ID>TEST-E2E-001</cbc:ID>
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
        assert "error" not in data
        assert "id" in data or "numero" in data
    
    def test_upload_ubl_missing_file_returns_400_missing_xml(self):
        """
        POST /api/v1/facturas/upload-ubl/ sin file ni xml → 400 {"error":"missing_xml",...}
        """
        url = reverse('factura-upload-ubl')
        
        resp = self.api_client.post(url, data={}, format="json")
        
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        data = resp.json()
        assert data["error"] == "missing_xml"
        assert "Falta archivo" in data["message"]
    
    def test_upload_ubl_invalid_naturaleza_returns_400_invalid_param(self):
        """
        POST /api/v1/facturas/upload-ubl/ con naturaleza inválida → 400 {"error":"invalid_param",...}
        """
        url = reverse('factura-upload-ubl')
        
        valid_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
                 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
          <cbc:ID>TEST-E2E-002</cbc:ID>
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
        
        resp = self.api_client.post(url, data={"xml": valid_xml, "naturaleza": "INVALIDO"}, format="json")
        
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        data = resp.json()
        assert data["error"] == "invalid_param"
        assert "naturaleza debe ser VENTA o COMPRA" in data["message"]
    
    def test_get_factura_detail_returns_200(self):
        """
        GET /api/v1/facturas/{id}/ → 200 OK con datos de factura
        """
        # Crear factura de prueba
        factura = Factura.objects.create(
            numero="TEST-DETAIL-001",
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
            total=Decimal("119000.00")
        )
        
        url = reverse('factura-detail', kwargs={'pk': factura.id})
        resp = self.api_client.get(url)
        
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["id"] == factura.id
        assert data["numero"] == "TEST-DETAIL-001"
        assert "error" not in data
    
    def test_delete_factura_returns_204(self):
        """
        DELETE /api/v1/facturas/{id}/ → 204 No Content (rollback de error de carga)
        """
        # Crear factura de prueba
        factura = Factura.objects.create(
            numero="TEST-DELETE-001",
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
            total=Decimal("119000.00")
        )
        
        url = reverse('factura-detail', kwargs={'pk': factura.id})
        resp = self.api_client.delete(url)
        
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        
        # Verificar que la factura fue eliminada
        assert not Factura.objects.filter(id=factura.id).exists()
    
    def test_upload_duplicate_returns_409(self):
        """
        POST /api/v1/facturas/upload-ubl/ con factura duplicada → 409 {"error":"duplicate",...}
        """
        # Crear factura existente
        Factura.objects.create(
            numero="TEST-DUP-E2E",
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
            total=Decimal("119000.00")
        )
        
        # Intentar importar la misma factura
        duplicate_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
                 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
          <cbc:ID>TEST-DUP-E2E</cbc:ID>
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
        
        url = reverse('factura-upload-ubl')
        resp = self.api_client.post(url, data={"xml": duplicate_xml}, format="json")
        
        assert resp.status_code == status.HTTP_409_CONFLICT
        data = resp.json()
        assert data["error"] == "duplicate"
        assert "ya existe" in data["message"]
