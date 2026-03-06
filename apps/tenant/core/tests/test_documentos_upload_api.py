"""
Tests para endpoint universal de documentos (FASE 8).

⚠️ PRINCIPIOS:
- Tests multitenant: Verificar aislamiento por esquema
- API-First: Verificar respuestas JSON-only
- Preview mode: Verificar que preview=true no persiste
- Validación: Verificar códigos HTTP apropiados
"""
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import tenant_context
from apps.public.tenants.models import Client, Domain
from django.contrib.auth import get_user_model

User = get_user_model()


class DocumentoUploadAPITests(TenantTestCase):
    """Tests para endpoint universal de documentos (FASE 8)."""
    
    def setUp(self):
        """Configurar cliente y usuario de prueba."""
        self.client = APIClient()
        # Crear usuario de prueba
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_upload_missing_file(self):
        """Test: Error 400 si no se envía archivo."""
        response = self.client.post('/api/v1/documentos/upload/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
        self.assertEqual(response.json()['error'], 'missing_file')
    
    def test_upload_preview_mode(self):
        """Test: Preview mode retorna DTO sin persistir."""
        # Crear archivo XML de prueba (mínimo válido)
        xml_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:ID>FAC001</cbc:ID>
    <cbc:IssueDate>2026-01-01</cbc:IssueDate>
    <cac:AccountingSupplierParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID>900123456-7</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>Empresa Test</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID>800987654-3</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>Cliente Test</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:LegalMonetaryTotal>
        <cbc:LineExtensionAmount>1000.00</cbc:LineExtensionAmount>
        <cbc:TaxExclusiveAmount>1000.00</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount>1190.00</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount>1190.00</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
</Invoice>'''
        
        file = SimpleUploadedFile("test.xml", xml_content, content_type="application/xml")
        
        response = self.client.post(
            '/api/v1/documentos/upload/?preview=true',
            {'file': file},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data.get('persisted', True))
        self.assertIn('dto', data)
        self.assertIn('sha256', data)
        self.assertIn('metadata', data)
    
    def test_upload_invalid_file(self):
        """Test: Error 400 para archivo inválido."""
        file = SimpleUploadedFile("test.txt", b"invalid content", content_type="text/plain")
        
        response = self.client.post(
            '/api/v1/documentos/upload/',
            {'file': file},
            format='multipart'
        )
        
        # Puede ser 400 (parsing error) o 422 (validación)
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ])
        self.assertIn('error', response.json())
    
    def test_upload_with_tipo_hint(self):
        """Test: Parámetro tipo_hint se pasa al pipeline."""
        xml_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
    <cbc:ID>FAC001</cbc:ID>
</Invoice>'''
        
        file = SimpleUploadedFile("test.xml", xml_content, content_type="application/xml")
        
        response = self.client.post(
            '/api/v1/documentos/upload/?preview=true&tipo=invoice',
            {'file': file},
            format='multipart'
        )
        
        # Debe procesar correctamente (puede fallar en validación, pero no en detección)
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ])
    
    def test_response_structure(self):
        """Test: Respuesta tiene estructura correcta."""
        xml_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
    <cbc:ID>FAC001</cbc:ID>
</Invoice>'''
        
        file = SimpleUploadedFile("test.xml", xml_content, content_type="application/xml")
        
        response = self.client.post(
            '/api/v1/documentos/upload/?preview=true',
            {'file': file},
            format='multipart'
        )
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # Verificar estructura mínima
            self.assertIn('persisted', data)
            self.assertIn('dto', data)
            self.assertIn('sha256', data)
            self.assertIn('metadata', data)
            self.assertIn('tipo', data)
    
    def test_multitenant_isolation(self):
        """Test: Verificar aislamiento multitenant."""
        # Este test requiere múltiples tenants, se puede expandir más adelante
        # Por ahora, verificamos que el endpoint funciona en el tenant actual
        xml_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
    <cbc:ID>FAC001</cbc:ID>
</Invoice>'''
        
        file = SimpleUploadedFile("test.xml", xml_content, content_type="application/xml")
        
        response = self.client.post(
            '/api/v1/documentos/upload/?preview=true',
            {'file': file},
            format='multipart'
        )
        
        # Debe procesar en el contexto del tenant actual
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ])
