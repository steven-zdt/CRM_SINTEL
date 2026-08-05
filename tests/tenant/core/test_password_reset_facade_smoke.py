"""
Smoke tests para Password Reset Facade (Core API).

[WARNING] POLÍTICA: Verificar que los endpoints de password reset funcionan correctamente.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()


@pytest.mark.django_db
class TestPasswordResetFacade(SintelTenantTestCase):
    """Tests para endpoints Core de password reset."""

    def test_request_reset_endpoint_accessible(self):
        """POST /api/v1/core/auth/password-reset/request/ debe ser accesible sin autenticación."""
        r = self.client.post(
            "/api/v1/core/auth/password-reset/request/",
            {"email": "test@example.com"},
            HTTP_HOST=self.tenant_domain,
            content_type="application/json",
        )
        # Debe retornar 200 (idempotente) o 400 (si falta email)
        assert r.status_code in [200, 400], f"Status code inesperado: {r.status_code}"
        data = r.json()
        assert "detail" in data, "Respuesta debe contener 'detail'"

    def test_request_reset_missing_email(self):
        """POST /api/v1/core/auth/password-reset/request/ sin email → 400."""
        r = self.client.post(
            "/api/v1/core/auth/password-reset/request/",
            {},
            HTTP_HOST=self.tenant_domain,
            content_type="application/json",
        )
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data

    def test_validate_endpoint_accessible(self):
        """POST /api/v1/core/auth/password-reset/validate/ debe ser accesible sin autenticación."""
        r = self.client.post(
            "/api/v1/core/auth/password-reset/validate/",
            {"uid": "invalid", "token": "invalid"},
            HTTP_HOST=self.tenant_domain,
            content_type="application/json",
        )
        # Debe retornar 400 (token inválido) o 400 (faltan parámetros)
        assert r.status_code == 400, f"Status code inesperado: {r.status_code}"
        data = r.json()
        assert "detail" in data, "Respuesta debe contener 'detail'"

    def test_validate_missing_params(self):
        """POST /api/v1/core/auth/password-reset/validate/ sin parámetros → 400."""
        r = self.client.post(
            "/api/v1/core/auth/password-reset/validate/",
            {},
            HTTP_HOST=self.tenant_domain,
            content_type="application/json",
        )
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data

    def test_confirm_endpoint_accessible(self):
        """POST /api/v1/core/auth/password-reset/confirm/ debe ser accesible sin autenticación."""
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
        # Debe retornar 400 (token inválido)
        assert r.status_code == 400, f"Status code inesperado: {r.status_code}"
        data = r.json()
        assert "detail" in data, "Respuesta debe contener 'detail'"

    def test_confirm_missing_params(self):
        """POST /api/v1/core/auth/password-reset/confirm/ sin parámetros → 400."""
        r = self.client.post(
            "/api/v1/core/auth/password-reset/confirm/",
            {},
            HTTP_HOST=self.tenant_domain,
            content_type="application/json",
        )
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data

    def test_confirm_password_mismatch(self):
        """POST /api/v1/core/auth/password-reset/confirm/ con contraseñas que no coinciden → 400."""
        r = self.client.post(
            "/api/v1/core/auth/password-reset/confirm/",
            {
                "uid": "test",
                "token": "test",
                "password1": "newpass123",
                "password2": "different123",
            },
            HTTP_HOST=self.tenant_domain,
            content_type="application/json",
        )
        assert r.status_code == 400
        data = r.json()
        assert "password2" in data or "detail" in data

    def test_confirm_password_too_short(self):
        """POST /api/v1/core/auth/password-reset/confirm/ con contraseña muy corta → 400."""
        r = self.client.post(
            "/api/v1/core/auth/password-reset/confirm/",
            {
                "uid": "test",
                "token": "test",
                "password1": "short",
                "password2": "short",
            },
            HTTP_HOST=self.tenant_domain,
            content_type="application/json",
        )
        assert r.status_code == 400
        data = r.json()
        assert "password1" in data or "detail" in data
