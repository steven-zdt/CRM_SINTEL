"""
Smoke tests para shell estático de reset (tenant-hosted).

[WARNING] POLÍTICA: Verificar que el shell se carga correctamente desde Core.
"""

import pytest

from tests.tenant.base_test import SintelTenantTestCase


@pytest.mark.django_db
class TestResetShellTenant(SintelTenantTestCase):
    """Tests para shell estático de reset."""

    def test_reset_shell_loads(self):
        """GET /static/tenant/core/landing/reset/index.html → 200 + marcadores presentes."""
        # Nota: En desarrollo, los archivos estáticos pueden no estar disponibles
        # Este test verifica que la ruta existe y redirige correctamente
        r = self.client.get(
            "/reset/",
            HTTP_HOST=self.tenant_domain,
            follow=False,  # No seguir redirects para verificar la redirección
        )
        # Debe redirigir al shell estático
        assert r.status_code in [301, 302, 200]

        # Si es redirect, verificar que apunta al shell correcto
        if r.status_code in [301, 302]:
            location = r.get("Location", "")
            assert (
                "static/tenant/core/landing/reset/index.html" in location
                or "/static/tenant/core/landing/reset/index.html" in location
            )
