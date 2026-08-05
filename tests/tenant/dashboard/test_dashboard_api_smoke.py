"""
Smoke tests para la API del dashboard.

Verifica que el endpoint /api/v1/dashboard/data/ retorne un payload válido.
"""

import pytest

from tests.tenant.base_test import SintelTenantTestCase


@pytest.mark.django_db
class TestDashboardAPI(SintelTenantTestCase):
    """Tests de smoke para la API del dashboard."""

    def test_dashboard_data(self):
        """Test: GET /api/v1/dashboard/data/ retorna 200 y payload válido."""
        response = self.api_client.get("/api/v1/dashboard/data/")
        assert response.status_code == 200
        data = response.json()

        # Verificar estructura del payload
        assert "kpis" in data
        assert isinstance(data["kpis"], list)
        assert "series" in data
        assert isinstance(data["series"], list)
        assert "table" in data
        assert "columns" in data["table"]
        assert "rows" in data["table"]

        # Verificar que kpis tenga al menos un elemento
        assert len(data["kpis"]) > 0

        # Verificar estructura de un KPI
        kpi = data["kpis"][0]
        assert "label" in kpi
        assert "value" in kpi
        assert isinstance(kpi["value"], (int, float))

    def test_dashboard_data_requires_authentication(self):
        """Test: El endpoint requiere autenticación."""
        from rest_framework.test import APIClient

        unauthenticated_client = APIClient(HTTP_HOST=self.domain.domain)
        response = unauthenticated_client.get("/api/v1/dashboard/data/")
        assert response.status_code == 401  # Unauthorized
