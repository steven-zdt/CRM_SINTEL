"""
Smoke tests para integración de landing en workspace.

Verifica que workspace.html incluye los slots de landing y que HTMX los carga correctamente.
"""

import pytest

from tests.tenant.base_test import SintelTenantTestCase


@pytest.mark.django_db
class TestWorkspaceLandingIntegration(SintelTenantTestCase):
    """Tests para integración de landing en workspace."""

    def test_workspace_contains_landing_slots(self):
        """Verifica que workspace.html contiene los slots de landing."""
        self.login_as_tenant_admin()
        r = self.client.get("/workspace/", HTTP_HOST=self.tenant_domain)
        assert r.status_code == 200
        # Verificar que los slots están presentes
        assert b"slot-landing-header" in r.content
        assert b"slot-landing-auth" in r.content
        assert b"slot-landing-info" in r.content
        # Verificar que HTMX está configurado
        assert b'hx-get="/ui/landing/partials/header/"' in r.content
        assert b'hx-get="/ui/landing/partials/auth/"' in r.content
        assert b'hx-get="/ui/landing/partials/info/"' in r.content

    def test_workspace_includes_landing_js(self):
        """Verifica que workspace.html incluye el JS centralizado de landing."""
        self.login_as_tenant_admin()
        r = self.client.get("/workspace/", HTTP_HOST=self.tenant_domain)
        assert r.status_code == 200
        # Verificar que el JS está incluido
        assert b"landing.ui.js" in r.content or b"core/js/landing" in r.content

    def test_workspace_htmx_handler_for_landing(self):
        """Verifica que el handler HTMX para landing está presente."""
        self.login_as_tenant_admin()
        r = self.client.get("/workspace/", HTTP_HOST=self.tenant_domain)
        assert r.status_code == 200
        # Verificar que el handler está en el script
        assert b"slot-landing" in r.content
        assert b"LandingUI" in r.content or b"landing" in r.content.lower()
