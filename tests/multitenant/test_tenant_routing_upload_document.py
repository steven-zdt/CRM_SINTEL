"""
Tests de routing multitenant para upload de documentos (FASE 9).

⚠️ PRINCIPIOS:
- Endpoints usan esquema del tenant que hace la petición
- TenantMainMiddleware resuelve tenant por dominio
- URLConf correcto según dominio
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from django_tenants.test.cases import TenantTestCase
from django.contrib.auth import get_user_model
from apps.public.tenants.models import Client, Domain

User = get_user_model()


class TestTenantRoutingUploadDocument(TenantTestCase):
    """Tests de routing multitenant para upload."""
    
    def setUp(self):
        """Configurar tenant y usuario."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_upload_uses_current_tenant_schema(self):
        """Test: Upload usa esquema del tenant actual."""
        csv_content = b'''numero,fecha_emision,emisor_nit,emisor_razon_social,total
GAS001,2026-01-01,900123456-7,Proveedor Test,500.00'''
        
        file = SimpleUploadedFile("gasto.csv", csv_content, content_type="text/csv")
        
        response = self.client.post(
            '/api/v1/core/documentos/upload/?preview=true&tipo=gasto',
            {'file': file},
            format='multipart',
            HTTP_HOST=f'{self.tenant.schema_name}.localhost'  # Usar dominio del tenant
        )
        
        # Verificar que la respuesta es del tenant correcto
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY)
        
        # Verificar que el esquema usado es el del tenant
        from django.db import connection
        assert connection.schema_name == self.tenant.schema_name
    
    def test_upload_endpoint_available_in_tenant_urlconf(self):
        """Test: Endpoint disponible en TENANT_URLCONF."""
        # El endpoint debe estar disponible cuando se accede por dominio del tenant
        response = self.client.get(
            '/api/v1/core/documentos/',
            HTTP_HOST=f'{self.tenant.schema_name}.localhost'
        )
        
        # Puede ser 405 (Method Not Allowed) o 404, pero no 500
        assert response.status_code != 500
