"""
Smoke tests de templates para la app tenants.

Verifica que los endpoints API no renderizan templates HTML.
"""
from django.test import TestCase
from apps.config.tests.base_public import PublicAPITestCase


class TenantsTemplateTests(PublicAPITestCase):
    """Tests de templates para endpoints de tenants."""
    
    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        from apps.public.tenants.models import Client
        self.tenant = Client.objects.create(
            nombre='Test Tenant',
            on_trial=True,
        )
    
    def test_api_endpoints_no_render_templates(self):
        """Test: Los endpoints /api/public/v1/tenants/ no renderizan templates."""
        response = self.json('get', '/api/public/v1/tenants/')
        self.assertEqual(response['content-type'], 'application/json')
        # Verificar que no se usó ningún template
        self.assertNotIn('text/html', response['content-type'])
    
    def test_api_detail_no_render_templates(self):
        """Test: El endpoint de detalle no renderiza templates."""
        response = self.json('get', f'/api/public/v1/tenants/{self.tenant.id}/')
        self.assertEqual(response['content-type'], 'application/json')
        self.assertNotIn('text/html', response['content-type'])
