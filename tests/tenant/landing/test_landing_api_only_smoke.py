"""
Smoke tests para verificar que apps/tenant/landing solo expone APIs JSON.

Verifica que:
1. Las APIs de landing responden JSON (200)
2. No hay vistas HTML en apps/tenant/landing
3. El redirect /landing/ funciona correctamente
"""

import pytest

from tests.tenant.base_test import SintelTenantTestCase


@pytest.mark.django_db
class TestLandingAPIOnly(SintelTenantTestCase):
    """Tests de smoke para verificar que landing solo expone APIs JSON."""

    def test_landing_info_api_returns_json(self):
        """Test: GET /api/v1/landing/info/ retorna JSON (200)"""
        from rest_framework.test import APIClient

        client = APIClient(HTTP_HOST=self.domain.domain)
        response = client.get("/api/v1/landing/info/")
        assert response.status_code == 200
        assert response["Content-Type"].startswith("application/json")
        data = response.json()
        assert "nombre" in data or "detail" in data

    def test_landing_route_redirects_to_public_core_shell(self):
        """Test: GET /landing/ redirige a /static/public/core/landing/index.html"""
        response = self.api_client.get("/landing/")
        assert response.status_code == 302
        assert "/static/public/core/landing/index.html" in response.url

    def test_root_route_redirects_to_public_core_landing_for_anonymous(self):
        """Test: GET / (root) redirige a /static/public/core/landing/index.html para usuarios anónimos"""
        from rest_framework.test import APIClient

        client = APIClient(HTTP_HOST=self.domain.domain)
        # No autenticar (usuario anónimo)
        response = client.get("/")
        assert response.status_code == 302
        assert "/static/public/core/landing/index.html" in response.url

    def test_no_html_views_in_landing_app(self):
        """Test: No hay vistas HTML en apps/tenant/landing (solo APIs)"""
        # Intentar acceder a rutas que no deberían existir
        from rest_framework.test import APIClient

        client = APIClient(HTTP_HOST=self.domain.domain)

        # Estas rutas no deberían existir (404)
        response = client.get("/ui/landing/")
        assert response.status_code == 404

        # Verificar que las APIs sí existen
        response = client.get("/api/v1/landing/info/")
        assert response.status_code == 200
