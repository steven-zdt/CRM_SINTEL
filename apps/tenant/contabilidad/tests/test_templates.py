"""
Smoke tests de templates para la app contabilidad.

Verifica que los endpoints API no renderizan templates HTML.
"""
from decimal import Decimal

from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.contabilidad.models import AsientoContable, CuentaContable


class ContabilidadTemplateTests(TenantAPITestCase):
    """Tests de templates para endpoints de contabilidad."""
    
    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        self.asiento = AsientoContable.objects.create(
            numero='AS-001',
            fecha='2024-01-15',
            descripcion='Test',
            estado='BORRADOR',
        )
    
    def test_api_endpoints_no_render_templates(self):
        """Test: Los endpoints /api/v1/asientos-contables/ no renderizan templates."""
        response = self.tget('/api/v1/asientos-contables/')
        self.assertIn('application/json', response['content-type'])
        self.assertNotIn('text/html', response['content-type'])
    
    def test_aprobar_endpoint_no_render_templates(self):
        """Test: El endpoint aprobar/ no renderiza templates."""
        # Crear cuenta y movimientos balanceados para poder aprobar
        cuenta = CuentaContable.objects.create(
            codigo='110505',
            nombre='Caja',
            tipo='ACTIVO',
            activa=True,
        )
        from apps.tenant.contabilidad.models import MovimientoContable
        MovimientoContable.objects.create(
            asiento=self.asiento,
            cuenta=cuenta,
            debe=Decimal('100000.00'),
            haber=Decimal('0.00'),
            descripcion='Debe',
            orden=1,
        )
        MovimientoContable.objects.create(
            asiento=self.asiento,
            cuenta=cuenta,
            debe=Decimal('0.00'),
            haber=Decimal('100000.00'),
            descripcion='Haber',
            orden=2,
        )
        
        response = self.tpost(f'/api/v1/asientos-contables/{self.asiento.id}/aprobar/', {})
        self.assertIn('application/json', response['content-type'])
        self.assertNotIn('text/html', response['content-type'])
