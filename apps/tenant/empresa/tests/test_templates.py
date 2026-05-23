"""
Smoke tests de templates para la app empresa.

Verifica que los endpoints API no renderizan templates HTML.
"""
from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.empresa.models import Empresa


class EmpresaTemplateTests(TenantAPITestCase):
    """Tests de templates para endpoints de empresa."""
    
    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        self.empresa = Empresa.objects.first()
        if not self.empresa:
            self.empresa = Empresa.objects.create(
                razon_social='Test Empresa',
                nit='900123456',
                dv='1',
                direccion='Calle Test 123',
                ciudad='Bogotá',
                departamento='Cundinamarca',
                email='test@example.com',
                activa=True,
            )
    
    def test_api_endpoints_no_render_templates(self):
        """Test: Los endpoints /api/v1/empresas/ no renderizan templates."""
        response = self.tget('/api/v1/empresas/')
        self.assertIn('application/json', response['content-type'])
        self.assertNotIn('text/html', response['content-type'])
    
    def test_activas_endpoint_no_render_templates(self):
        """Test: El endpoint activas/ no renderiza templates."""
        response = self.tget('/api/v1/empresas/activas/')
        self.assertIn('application/json', response['content-type'])
        self.assertNotIn('text/html', response['content-type'])
