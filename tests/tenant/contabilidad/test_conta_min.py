"""
Tests mínimos de API de Contabilidad (lectura).

Verifica que:
- GET /api/v1/cuentas-contables/?limit=10 → 200
- GET /api/v1/asientos-contables/?limit=10 → 200
"""

from rest_framework import status

from tests.tenant.base_test import SintelTenantTestCase


class TestContabilidadMin(SintelTenantTestCase):
    """
    Tests mínimos para verificar la API de Contabilidad (lectura).
    """

    def test_get_cuentas_contables_returns_200(self):
        """
        Verifica que GET /api/v1/cuentas-contables/?limit=10 retorna 200.
        """
        response = self.api_client.get("/api/v1/cuentas-contables/?limit=10")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # Debe retornar una lista o dict
        self.assertIsInstance(data, (list, dict))

    def test_get_asientos_contables_returns_200(self):
        """
        Verifica que GET /api/v1/asientos-contables/?limit=10 retorna 200.
        """
        response = self.api_client.get("/api/v1/asientos-contables/?limit=10")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # Debe retornar una lista o dict
        self.assertIsInstance(data, (list, dict))
