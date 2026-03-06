"""
Smoke tests para partials del dashboard.

Verifica que todos los partials retornen 200 y contengan los markers esperados.
"""
import pytest
from tests.tenant.base_test import SintelTenantTestCase


@pytest.mark.django_db
class TestDashboardPartials(SintelTenantTestCase):
    """Tests de smoke para partials del dashboard."""
    
    def test_header_partial_200(self):
        """Test: GET /ui/dashboard/partials/header/ retorna 200 y contiene data-partial."""
        response = self.api_client.get("/ui/dashboard/partials/header/")
        assert response.status_code == 200
        assert b'data-partial="dashboard-header"' in response.content
    
    def test_kpis_partial_200(self):
        """Test: GET /ui/dashboard/partials/kpis/ retorna 200 y contiene data-partial."""
        response = self.api_client.get("/ui/dashboard/partials/kpis/")
        assert response.status_code == 200
        assert b'data-partial="dashboard-kpis"' in response.content
    
    def test_charts_partial_200(self):
        """Test: GET /ui/dashboard/partials/charts/ retorna 200 y contiene data-partial."""
        response = self.api_client.get("/ui/dashboard/partials/charts/")
        assert response.status_code == 200
        assert b'data-partial="dashboard-charts"' in response.content
    
    def test_table_partial_200(self):
        """Test: GET /ui/dashboard/partials/table/ retorna 200 y contiene data-partial."""
        response = self.api_client.get("/ui/dashboard/partials/table/")
        assert response.status_code == 200
        assert b'data-partial="dashboard-table"' in response.content
    
    def test_partials_require_authentication(self):
        """Test: Los partials requieren autenticación."""
        from rest_framework.test import APIClient
        unauthenticated_client = APIClient(HTTP_HOST=self.domain.domain)
        response = unauthenticated_client.get("/ui/dashboard/partials/header/")
        assert response.status_code == 302  # Redirect to login
