"""
Tests de integración para workspace y dashboard.

Verifica que el workspace cargue correctamente los partials del dashboard.
"""

import pytest

from tests.tenant.base_test import SintelTenantTestCase


@pytest.mark.django_db
class TestWorkspaceIntegration(SintelTenantTestCase):
    """Tests de integración para workspace y dashboard."""

    def test_workspace_renders(self):
        """Test: GET /workspace/ retorna 200 y contiene los slots del dashboard."""
        response = self.api_client.get("/workspace/")
        assert response.status_code == 200

        # Verificar que workspace contiene los slots del dashboard
        assert b"slot-dashboard-header" in response.content
        assert b"slot-dashboard-kpis" in response.content
        assert b"slot-dashboard-charts" in response.content
        assert b"slot-dashboard-table" in response.content

        # Verificar que contiene los atributos HTMX
        assert b'hx-get="/ui/dashboard/partials/header/"' in response.content
        assert b'hx-get="/ui/dashboard/partials/kpis/"' in response.content
        assert b'hx-get="/ui/dashboard/partials/charts/"' in response.content
        assert b'hx-get="/ui/dashboard/partials/table/"' in response.content

    def test_workspace_requires_authentication(self):
        """Test: El workspace requiere autenticación."""
        from rest_framework.test import APIClient

        unauthenticated_client = APIClient(HTTP_HOST=self.domain.domain)
        response = unauthenticated_client.get("/workspace/")
        assert response.status_code == 302  # Redirect to login
