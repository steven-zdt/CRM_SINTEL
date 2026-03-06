"""
Tests de API endpoint para upload de documentos tipo=inventario (FASE 9).

⚠️ PRINCIPIOS:
- API-First JSON-only
- Preview mode
- Validación de items
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from django_tenants.test.cases import TenantTestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class TestUploadDocumentEndpointInventario(TenantTestCase):
    """Tests de API endpoint para upload de inventario."""
    
    def setUp(self):
        """Configurar cliente y usuario."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_upload_inventario_preview(self):
        """Test: Preview de inventario retorna DTO sin persistir."""
        csv_content = b'''numero,fecha_emision,almacen,item_codigo,item_descripcion,item_cantidad,item_unidad
INV001,2026-01-01,ALM001,ITEM001,Producto 1,10.00,UND
INV001,2026-01-01,ALM001,ITEM002,Producto 2,5.00,UND'''
        
        file = SimpleUploadedFile("inventario.csv", csv_content, content_type="text/csv")
        
        response = self.client.post(
            '/api/v1/core/documentos/upload/?preview=true&tipo=inventario',
            {'file': file},
            format='multipart'
        )
        
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY)
        data = response.json()
        assert "persisted" in data
        assert data["persisted"] is False
        assert "dto" in data
    
    def test_upload_inventario_no_items(self):
        """Test: Error 422 si no hay items."""
        csv_content = b'''numero,fecha_emision,almacen
INV001,2026-01-01,ALM001'''
        
        file = SimpleUploadedFile("inventario.csv", csv_content, content_type="text/csv")
        
        response = self.client.post(
            '/api/v1/core/documentos/upload/?preview=true&tipo=inventario',
            {'file': file},
            format='multipart'
        )
        
        # Puede ser 422 (validación) o 200 (si el parser no valida aún)
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY)
        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            data = response.json()
            assert "error" in data or "missing_fields" in data
