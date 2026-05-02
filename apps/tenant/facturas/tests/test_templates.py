"""
Smoke tests de templates para la app facturas.

Verifica que los endpoints API no renderizan templates HTML.
"""
from decimal import Decimal

from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.facturas.models import Factura


class FacturasTemplateTests(TenantAPITestCase):
    """Tests de templates para endpoints de facturas."""
    
    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        self.factura = Factura.objects.create(
            numero='FAC-001',
            prefijo='FAC',
            consecutivo=1,
            tipo='FE',
            estado='BORRADOR',
            fecha_emision='2024-01-15',
            emisor_nit='900123456',
            emisor_razon_social='Empresa Emisora S.A.S.',
            receptor_nit='800654321',
            receptor_razon_social='Cliente Receptor S.A.S.',
            subtotal=Decimal('100000.00'),
            impuestos=Decimal('19000.00'),
            total=Decimal('119000.00'),
        )
    
    def test_api_endpoints_no_render_templates(self):
        """Test: Los endpoints /api/v1/facturas/ no renderizan templates."""
        response = self.tget('/api/v1/facturas/')
        self.assertIn('application/json', response['content-type'])
        self.assertNotIn('text/html', response['content-type'])
    
    def test_por_estado_endpoint_no_render_templates(self):
        """Test: El endpoint por_estado/ no renderiza templates."""
        response = self.tget('/api/v1/facturas/por_estado/?estado=BORRADOR')
        self.assertIn('application/json', response['content-type'])
        self.assertNotIn('text/html', response['content-type'])
