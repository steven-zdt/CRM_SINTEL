"""
Tests mínimos de API de Facturas (lectura).

Verifica que:
- GET /api/v1/facturas/?limit=10 → 200
- GET /api/v1/facturas/?limit=10&estado=... → 200
"""
from tests.tenant.base_test import SintelTenantTestCase
from rest_framework import status


class TestFacturasMin(SintelTenantTestCase):
    """
    Tests mínimos para verificar la API de Facturas (lectura).
    """

    def test_get_facturas_returns_200(self):
        """
        Verifica que GET /api/v1/facturas/?limit=10 retorna 200.
        """
        response = self.api_client.get('/api/v1/facturas/?limit=10')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # Debe retornar una lista (puede estar vacía)
        self.assertIsInstance(data, (list, dict))
        # Si es dict, debe tener 'results' o 'data'
        if isinstance(data, dict):
            self.assertIn('results', data)

    def test_get_facturas_with_estado_filter_returns_200(self):
        """
        Verifica que GET /api/v1/facturas/?limit=10&estado=... retorna 200.
        """
        response = self.api_client.get('/api/v1/facturas/?limit=10&estado=BORRADOR')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # Debe retornar una lista o dict
        self.assertIsInstance(data, (list, dict))
