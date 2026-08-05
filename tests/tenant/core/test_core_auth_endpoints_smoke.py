"""
Smoke tests para Core Auth Endpoints.

[WARNING] POLÍTICA: Verificar que los endpoints de auth centralizados funcionan correctamente.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()


@pytest.mark.django_db
class TestCoreAuthEndpoints(SintelTenantTestCase):
    """Tests para endpoints Core de autenticación."""

    def test_login_endpoint_accessible_anon(self):
        """POST /api/v1/core/auth/login/ (anon) → 200 con redirect_url o 401/403."""
        r = self.client.post(
            "/api/v1/core/auth/login/",
            {"email": "nonexistent@example.com", "password": "wrongpass"},
            HTTP_HOST=self.tenant_domain,
            content_type="application/json",
        )
        # Debe retornar 401 (credenciales inválidas) o 403 (sin membresía)
        assert r.status_code in [
            200,
            401,
            403,
        ], f"Status code inesperado: {r.status_code}"
        data = r.json()
        assert "detail" in data

    def test_login_success(self):
        """POST /api/v1/core/auth/login/ con credenciales válidas → 200 con redirect_url."""
        # Usar el usuario creado por SintelTenantTestCase
        if not self.user.has_usable_password():
            self.user.set_password("testpass123")
            self.user.save()

        r = self.client.post(
            "/api/v1/core/auth/login/",
            {"email": self.user.email, "password": "testpass123"},
            HTTP_HOST=self.tenant_domain,
            content_type="application/json",
        )
        assert r.status_code == 200
        data = r.json()
        assert "detail" in data
        assert "redirect_url" in data
        assert isinstance(data["redirect_url"], str)

    def test_logout_endpoint_accessible_auth(self):
        """POST /api/v1/core/auth/logout/ (auth) → 200."""
        self.login_as_tenant_admin()
        r = self.client.post(
            "/api/v1/core/auth/logout/",
            {},
            HTTP_HOST=self.tenant_domain,
            content_type="application/json",
        )
        assert r.status_code == 200
        data = r.json()
        assert "detail" in data
        assert "redirect_url" in data

    def test_password_reset_request_anon(self):
        """POST /api/v1/core/auth/password-reset/request/ (anon) → 200/204 genérico."""
        r = self.client.post(
            "/api/v1/core/auth/password-reset/request/",
            {"email": "nonexistent@example.com"},
            HTTP_HOST=self.tenant_domain,
            content_type="application/json",
        )
        # Idempotente: siempre retorna 200
        assert r.status_code == 200
        data = r.json()
        assert "detail" in data

    def test_password_reset_validate_anon(self):
        """POST /api/v1/core/auth/password-reset/validate/ (anon) → 200 con shape."""
        r = self.client.post(
            "/api/v1/core/auth/password-reset/validate/",
            {"uid": "invalid", "token": "invalid"},
            HTTP_HOST=self.tenant_domain,
            content_type="application/json",
        )
        # Debe retornar 400 (token inválido) o 200 (si es válido)
        assert r.status_code in [200, 400]
        data = r.json()
        assert "detail" in data or "valid" in data

    def test_password_reset_confirm_anon(self):
        """POST /api/v1/core/auth/password-reset/confirm/ (anon) → 200 con redirect_url."""
        r = self.client.post(
            "/api/v1/core/auth/password-reset/confirm/",
            {
                "uid": "invalid",
                "token": "invalid",
                "password1": "newpass123",
                "password2": "newpass123",
            },
            HTTP_HOST=self.tenant_domain,
            content_type="application/json",
        )
        # Debe retornar 400 (token inválido) o 200 (si es válido)
        assert r.status_code in [200, 400]
        data = r.json()
        assert "detail" in data
        if r.status_code == 200:
            assert "redirect_url" in data
