"""
Smoke tests para partials de landing.

Verifica que los partials HTML se sirven correctamente y contienen los marcadores esperados.
"""
import pytest
from tests.tenant.base_test import SintelTenantTestCase


@pytest.mark.django_db
class TestLandingPartials(SintelTenantTestCase):
    """Tests para partials HTML de landing."""
    
    def test_header_partial(self):
        """Verifica que el partial de header se sirve correctamente."""
        self.login_as_tenant_admin()
        r = self.client.get("/ui/landing/partials/header/", HTTP_HOST=self.tenant_domain)
        assert r.status_code == 200
        assert b'data-partial="landing-header"' in r.content
        assert b'landing_subtitle' in r.content
    
    def test_auth_partial(self):
        """Verifica que el partial de auth se sirve correctamente."""
        self.login_as_tenant_admin()
        r = self.client.get("/ui/landing/partials/auth/", HTTP_HOST=self.tenant_domain)
        assert r.status_code == 200
        assert b'data-partial="landing-auth"' in r.content
        assert b'landing_login_form' in r.content
        assert b'landing_activate_form' in r.content
    
    def test_info_partial(self):
        """Verifica que el partial de info se sirve correctamente."""
        self.login_as_tenant_admin()
        r = self.client.get("/ui/landing/partials/info/", HTTP_HOST=self.tenant_domain)
        assert r.status_code == 200
        assert b'data-partial="landing-info"' in r.content
        assert b'landing_info' in r.content
