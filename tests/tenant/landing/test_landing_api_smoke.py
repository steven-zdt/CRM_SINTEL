"""
Smoke tests para APIs JSON de landing.

Verifica que los endpoints JSON funcionan correctamente.
"""

import pytest

from tests.tenant.base_test import SintelTenantTestCase


@pytest.mark.django_db
class TestLandingAPI(SintelTenantTestCase):
    """Tests para APIs JSON de landing."""

    def test_info_json(self):
        """Verifica que el endpoint de info retorna JSON válido."""
        self.login_as_tenant_admin()
        r = self.client.get("/api/v1/landing/info/", HTTP_HOST=self.tenant_domain)
        assert r.status_code == 200
        data = r.json()
        assert "nombre" in data or "status" in data
        # Verificar que es JSON, no HTML
        content_type = r.get("Content-Type", "")
        assert "json" in content_type.lower() or "application/json" in content_type

    def test_info_json_public(self):
        """Verifica que el endpoint de info es público (AllowAny)."""
        # Sin autenticación
        r = self.client.get("/api/v1/landing/info/", HTTP_HOST=self.tenant_domain)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)
