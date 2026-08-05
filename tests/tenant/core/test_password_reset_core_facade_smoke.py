"""
Smoke tests para Core Facade de Password Reset.

[WARNING] POLÍTICA: Verificar que Core Facade consume landing.services correctamente.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()


@pytest.mark.django_db
class TestPasswordResetCoreFacade(SintelTenantTestCase):
    """Tests para endpoints Core de password reset."""

    def test_request_reset_200_generic(self):
        """POST /api/v1/core/auth/password-reset/request/ → 200 genérico (idempotente)."""
        r = self.client.post(
            "/api/v1/core/auth/password-reset/request/",
            {"email": "nonexistent@example.com"},
            HTTP_HOST=self.tenant_domain,
            content_type="application/json",
        )
        assert r.status_code == 200
        data = r.json()
        assert "detail" in data
        # Idempotente: no revela si el email existe

    def test_validate_token_invalid(self):
        """POST /api/v1/core/auth/password-reset/validate/ con token inválido → 400."""
        r = self.client.post(
            "/api/v1/core/auth/password-reset/validate/",
            {"uid": "invalid", "token": "invalid"},
            HTTP_HOST=self.tenant_domain,
            content_type="application/json",
        )
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data

    def test_confirm_reset_invalid_token(self):
        """POST /api/v1/core/auth/password-reset/confirm/ con token inválido → 400."""
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
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data

    def test_confirm_reset_password_mismatch(self):
        """POST /api/v1/core/auth/password-reset/confirm/ con contraseñas que no coinciden → 400."""
        # Crear token válido para un usuario
        # Nota: SintelTenantTestCase ya crea self.user, pero necesitamos asegurar que tenga password usable
        if not self.user.has_usable_password():
            self.user.set_password("testpass123")
            self.user.save()
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        r = self.client.post(
            "/api/v1/core/auth/password-reset/confirm/",
            {
                "uid": uidb64,
                "token": token,
                "password1": "newpass123",
                "password2": "different123",
            },
            HTTP_HOST=self.tenant_domain,
            content_type="application/json",
        )
        assert r.status_code == 400
        data = r.json()
        assert "password2" in data or "detail" in data

    def test_confirm_reset_password_too_short(self):
        """POST /api/v1/core/auth/password-reset/confirm/ con contraseña muy corta → 400."""
        # Nota: SintelTenantTestCase ya crea self.user
        if not self.user.has_usable_password():
            self.user.set_password("testpass123")
            self.user.save()
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        r = self.client.post(
            "/api/v1/core/auth/password-reset/confirm/",
            {
                "uid": uidb64,
                "token": token,
                "password1": "short",
                "password2": "short",
            },
            HTTP_HOST=self.tenant_domain,
            content_type="application/json",
        )
        assert r.status_code == 400
        data = r.json()
        assert "password1" in data or "detail" in data
