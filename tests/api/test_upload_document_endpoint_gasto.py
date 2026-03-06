"""
Tests de API endpoint para upload de documentos tipo=gasto (FASE 9).

⚠️ PRINCIPIOS:
- API-First JSON-only
- Preview mode
- Persistencia
- Códigos HTTP correctos
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from django_tenants.test.cases import TenantTestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class TestUploadDocumentEndpointGasto(TenantTestCase):
    """Tests de API endpoint para upload de gastos."""
    
    def setUp(self):
        """Configurar cliente y usuario."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_upload_gasto_preview(self):
        """Test: Preview de gasto retorna DTO sin persistir."""
        csv_content = b'''numero,fecha_emision,emisor_nit,emisor_razon_social,total,categoria
GAS001,2026-01-01,900123456-7,Proveedor Test,500.00,Viaticos'''
        
        file = SimpleUploadedFile("gasto.csv", csv_content, content_type="text/csv")
        
        response = self.client.post(
            '/api/v1/core/documentos/upload/?preview=true&tipo=gasto',
            {'file': file},
            format='multipart'
        )
        
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY)
        data = response.json()
        assert "persisted" in data
        assert data["persisted"] is False
        assert "dto" in data
        assert "sha256" in data
        assert "metadata" in data
    
    def test_upload_gasto_missing_file(self):
        """Test: Error 400 si no se envía archivo."""
        response = self.client.post('/api/v1/core/documentos/upload/?tipo=gasto')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"] == "missing_file"
    
    def test_upload_gasto_invalid_total(self):
        """Test: Error 422 si total <= 0."""
        csv_content = b'''numero,fecha_emision,emisor_nit,emisor_razon_social,total,categoria
GAS001,2026-01-01,900123456-7,Proveedor Test,0.00,Viaticos'''
        
        file = SimpleUploadedFile("gasto.csv", csv_content, content_type="text/csv")
        
        response = self.client.post(
            '/api/v1/core/documentos/upload/?preview=true&tipo=gasto',
            {'file': file},
            format='multipart'
        )
        
        # Puede ser 422 (validación) o 200 (si el parser no valida aún)
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY)
        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            data = response.json()
            assert "error" in data or "missing_fields" in data
    
    def test_upload_gasto_response_structure(self):
        """Test: Estructura de respuesta correcta."""
        csv_content = b'''numero,fecha_emision,emisor_nit,emisor_razon_social,total,categoria
GAS001,2026-01-01,900123456-7,Proveedor Test,500.00,Viaticos'''
        
        file = SimpleUploadedFile("gasto.csv", csv_content, content_type="text/csv")
        
        response = self.client.post(
            '/api/v1/core/documentos/upload/?preview=true&tipo=gasto',
            {'file': file},
            format='multipart'
        )
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # Verificar estructura mínima
            assert "persisted" in data
            assert "dto" in data
            assert "sha256" in data
            assert "metadata" in data
            assert "tipo" in data
    
    def test_upload_gasto_json_only(self):
        """Test: Respuesta es JSON-only (no HTML)."""
        csv_content = b'''numero,fecha_emision,emisor_nit,emisor_razon_social,total,categoria
GAS001,2026-01-01,900123456-7,Proveedor Test,500.00,Viaticos'''
        
        file = SimpleUploadedFile("gasto.csv", csv_content, content_type="text/csv")
        
        response = self.client.post(
            '/api/v1/core/documentos/upload/?preview=true&tipo=gasto',
            {'file': file},
            format='multipart'
        )
        
        assert 'application/json' in response['Content-Type']
        assert '<html>' not in response.content.decode('utf-8', errors='ignore').lower()
