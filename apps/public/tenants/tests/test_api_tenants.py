"""
Tests de API para la app tenants.

Verifica:
- ReadOnly para Client y Domain (list/detail)
- 405 en POST/PUT/DELETE
- Paginación estándar
- Filtros y búsqueda
"""
from unittest.mock import patch
from django.utils import timezone
from rest_framework import status
from apps.config.tests.base_public import PublicAPITestCase
from apps.public.tenants.models import Client, Domain


class ClientViewSetTests(PublicAPITestCase):
    """Tests para ClientViewSet (ReadOnly)."""
    
    @patch('apps.public.tenants.models.Client.create_schema')
    def setUp(self, mock_create_schema):
        """
        Configuración inicial.
        
        Bypass de creación de esquemas para tests ReadOnly (acelera y evita ValidationError).
        Usa schema_name válido (sin guiones) para evitar errores de validación.
        """
        super().setUp()
        mock_create_schema.return_value = None
        
        # Crear algunos tenants de prueba con schema_name válido
        self.tenant1 = Client.objects.create(
            schema_name='t1',  # Schema name válido (sin guiones)
            nombre='Empresa 1',
            on_trial=True,
            paid_until=None,
        )
        self.tenant2 = Client.objects.create(
            schema_name='t2',  # Schema name válido (sin guiones)
            nombre='Empresa 2',
            on_trial=False,
            paid_until=timezone.now().date(),
        )
        
        # Crear dominios
        self.domain1 = Domain.objects.create(
            domain='empresa1.localhost',
            tenant=self.tenant1,
            is_primary=True,
        )
        self.domain2 = Domain.objects.create(
            domain='empresa2.localhost',
            tenant=self.tenant2,
            is_primary=True,
        )
    
    def test_list_tenants(self):
        """Test: GET /api/public/v1/tenants/ devuelve lista paginada."""
        response = self.json('get', '/api/public/v1/tenants/')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertPaginationFormat(response.data)
        self.assertGreaterEqual(len(response.data['results']), 2)
    
    def test_detail_tenant(self):
        """Test: GET /api/public/v1/tenants/{id}/ devuelve detalle."""
        response = self.json('get', f'/api/public/v1/tenants/{self.tenant1.id}/')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.tenant1.id)
        self.assertEqual(response.data['nombre'], 'Empresa 1')
    
    def test_create_tenant_405(self):
        """Test: POST /api/public/v1/tenants/ devuelve 405 (ReadOnly)."""
        data = {
            'nombre': 'Nueva Empresa',
            'on_trial': True,
        }
        response = self.json('post', '/api/public/v1/tenants/', data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_update_tenant_405(self):
        """Test: PUT /api/public/v1/tenants/{id}/ devuelve 405 (ReadOnly)."""
        data = {'nombre': 'Empresa Actualizada'}
        response = self.json('put', f'/api/public/v1/tenants/{self.tenant1.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_delete_tenant_405(self):
        """Test: DELETE /api/public/v1/tenants/{id}/ devuelve 405 (ReadOnly)."""
        response = self.json('delete', f'/api/public/v1/tenants/{self.tenant1.id}/')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_filter_by_on_trial(self):
        """Test: Filtrar por on_trial."""
        response = self.json('get', '/api/public/v1/tenants/?on_trial=true')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        for result in response.data['results']:
            self.assertTrue(result['on_trial'])
    
    def test_search_by_nombre(self):
        """Test: Búsqueda por nombre."""
        response = self.json('get', '/api/public/v1/tenants/?search=Empresa 1')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
        self.assertIn('Empresa 1', response.data['results'][0]['nombre'])
    
    def test_pagination(self):
        """Test: Paginación funciona correctamente."""
        response = self.json('get', '/api/public/v1/tenants/?page=1&page_size=1')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIsNotNone(response.data['next'])


class DomainViewSetTests(PublicAPITestCase):
    """Tests para DomainViewSet (ReadOnly)."""
    
    @patch('apps.public.tenants.models.Client.create_schema')
    def setUp(self, mock_create_schema):
        """
        Configuración inicial.
        
        Bypass de creación de esquemas para tests ReadOnly.
        """
        super().setUp()
        mock_create_schema.return_value = None
        
        self.tenant = Client.objects.create(
            schema_name='test',  # Schema name válido (sin guiones)
            nombre='Test Tenant',
            on_trial=True,
        )
        self.domain = Domain.objects.create(
            domain='test.localhost',
            tenant=self.tenant,
            is_primary=True,
        )
    
    def test_list_domains(self):
        """Test: GET /api/public/v1/domains/ devuelve lista paginada."""
        response = self.json('get', '/api/public/v1/domains/')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertPaginationFormat(response.data)
    
    def test_detail_domain(self):
        """Test: GET /api/public/v1/domains/{id}/ devuelve detalle."""
        response = self.json('get', f'/api/public/v1/domains/{self.domain.id}/')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.domain.id)
        self.assertEqual(response.data['domain'], 'test.localhost')
    
    def test_create_domain_405(self):
        """Test: POST /api/public/v1/domains/ devuelve 405 (ReadOnly)."""
        data = {
            'domain': 'new.localhost',
            'tenant': self.tenant.id,
            'is_primary': False,
        }
        response = self.json('post', '/api/public/v1/domains/', data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_update_domain_405(self):
        """Test: PUT /api/public/v1/domains/{id}/ devuelve 405 (ReadOnly)."""
        data = {'domain': 'updated.localhost'}
        response = self.json('put', f'/api/public/v1/domains/{self.domain.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_delete_domain_405(self):
        """Test: DELETE /api/public/v1/domains/{id}/ devuelve 405 (ReadOnly)."""
        response = self.json('delete', f'/api/public/v1/domains/{self.domain.id}/')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
