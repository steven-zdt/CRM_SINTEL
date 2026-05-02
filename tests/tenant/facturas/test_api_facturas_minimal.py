"""
Tests API minimalistas para validar el flujo completo de Facturas.

Verifica:
- Upload sin archivo → 400 {"error":"missing_xml",...}
- Upload preview → 200 (DTO)
- Upload persist → 201/200 (creado o idempotente)
- Delete → 204 (eliminado)
"""
import os
from pathlib import Path
from tests.tenant.base_test import SintelTenantTestCase
from rest_framework import status


class TestFacturasAPIMinimal(SintelTenantTestCase):
    """
    Tests API minimalistas para validar el flujo completo de Facturas.
    """

    def test_upload_missing_xml_400(self):
        """
        Verifica que POST /api/v1/facturas/upload-ubl/ sin archivo retorna 400.
        """
        response = self.api_client.post(
            '/api/v1/facturas/upload-ubl/',
            data={'naturaleza': 'VENTA'},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('message', data)
        self.assertEqual(data['error'], 'missing_xml')

    def test_upload_preview_200(self):
        """
        Verifica que POST /api/v1/facturas/upload-ubl/?preview=true retorna 200 con DTO.
        """
        # Buscar un archivo XML de prueba en el proyecto
        test_xml_path = Path(__file__).parent.parent.parent.parent / 'fixtures' / 'facturas' / 'sample_ubl.xml'
        
        # Si no existe, crear uno mínimo
        if not test_xml_path.exists():
            # Crear XML mínimo válido para UBL 2.1
            xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>TEST001</cbc:ID>
  <cbc:IssueDate>2024-01-01</cbc:IssueDate>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyIdentification>
        <cbc:ID>900000000</cbc:ID>
      </cac:PartyIdentification>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Test Supplier</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyIdentification>
        <cbc:ID>800000000</cbc:ID>
      </cac:PartyIdentification>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Test Customer</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount>1000.00</cbc:LineExtensionAmount>
    <cbc:TaxInclusiveAmount>1190.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount>1190.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
</Invoice>'''
        else:
            xml_content = test_xml_path.read_text(encoding='utf-8')
        
        response = self.api_client.post(
            '/api/v1/facturas/upload-ubl/?preview=true',
            data={
                'xml': xml_content,
                'naturaleza': 'VENTA'
            },
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # Debe retornar un DTO con campos básicos
        self.assertIn('numero', data)
        self.assertIn('emisor_razon_social', data)

    def test_upload_persist_201_o_200(self):
        """
        Verifica que POST /api/v1/facturas/upload-ubl/ persiste y retorna 201 o 200 (idempotente).
        """
        # XML mínimo válido
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>TEST_PERSIST_001</cbc:ID>
  <cbc:IssueDate>2024-01-01</cbc:IssueDate>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyIdentification>
        <cbc:ID>900000000</cbc:ID>
      </cac:PartyIdentification>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Test Supplier</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyIdentification>
        <cbc:ID>800000000</cbc:ID>
      </cac:PartyIdentification>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Test Customer</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount>1000.00</cbc:LineExtensionAmount>
    <cbc:TaxInclusiveAmount>1190.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount>1190.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
</Invoice>'''
        
        # Primera carga → debe ser 201
        response1 = self.api_client.post(
            '/api/v1/facturas/upload-ubl/',
            data={
                'xml': xml_content,
                'naturaleza': 'VENTA'
            },
            format='multipart'
        )
        
        self.assertIn(response1.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])
        data1 = response1.json()
        self.assertIn('id', data1)
        factura_id = data1['id']
        
        # Segunda carga (idempotente) → debe ser 200
        response2 = self.api_client.post(
            '/api/v1/facturas/upload-ubl/',
            data={
                'xml': xml_content,
                'naturaleza': 'VENTA'
            },
            format='multipart'
        )
        
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        data2 = response2.json()
        self.assertEqual(data2['id'], factura_id)  # Mismo ID
        
        # Limpiar: eliminar la factura de prueba
        self.api_client.delete(f'/api/v1/facturas/{factura_id}/')

    def test_delete_204(self):
        """
        Verifica que DELETE /api/v1/facturas/{id}/ retorna 204 y elimina la factura.
        """
        # Crear una factura de prueba primero
        from apps.tenant.facturas.models import Factura
        from django.utils import timezone
        
        factura = Factura.objects.create(
            numero='TEST_DELETE_001',
            naturaleza='VENTA',
            estado='BORRADOR',
            fecha_emision=timezone.now(),
            receptor_nit='800000000',
            receptor_razon_social='Test Delete',
            moneda='COP',
            subtotal=1000,
            impuestos=190,
            total=1190
        )
        
        factura_id = factura.id
        
        # Verificar que existe
        response_get = self.api_client.get(f'/api/v1/facturas/{factura_id}/')
        self.assertEqual(response_get.status_code, status.HTTP_200_OK)
        
        # Eliminar
        response_delete = self.api_client.delete(f'/api/v1/facturas/{factura_id}/')
        self.assertEqual(response_delete.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verificar que ya no existe
        response_get_after = self.api_client.get(f'/api/v1/facturas/{factura_id}/')
        self.assertEqual(response_get_after.status_code, status.HTTP_404_NOT_FOUND)
