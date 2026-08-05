"""
Smoke tests para Core Landing API (v2.30).

[WARNING] POLÍTICA: Validar que Core expone correctamente los servicios de Landing
y que todos los flujos funcionan end-to-end.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django_tenants.utils import tenant_context
from rest_framework import status
from rest_framework.test import APIClient

from apps.public.tenants.models import Client, Domain, TenantMembership

User = get_user_model()


class CoreLandingSmokeTestCase(TestCase):
    """Smoke tests para Core Landing API."""

    @classmethod
    def setUpTestData(cls):
        """Configuración inicial para todos los tests."""
        # Crear tenant de prueba
        cls.tenant = Client.objects.create(
            schema_name="test_tenant",
            nombre="Test Tenant",
            is_active=True,
        )

        # Crear dominio para el tenant
        with tenant_context(cls.tenant):
            Domain.objects.create(
                domain="test-tenant.localhost",
                tenant=cls.tenant,
                is_primary=True,
            )

        # Crear usuario de prueba
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

        # Crear membresía
        TenantMembership.objects.create(
            client=cls.tenant,
            user=cls.user,
            is_active=True,
        )

    def setUp(self):
        """Configuración antes de cada test."""
        self.client = APIClient()
        # Configurar hostname para routing por tenant
        self.client.defaults["HTTP_HOST"] = "test-tenant.localhost"

    def test_core_landing_info_200(self):
        """GET /api/v1/core/landing/info/ → 200 con contenido mínimo."""
        response = self.client.get("/api/v1/core/landing/info/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("application/json", response["Content-Type"])

        data = response.json()
        self.assertIn("nombre", data)
        self.assertIn("schema_name", data)
        self.assertEqual(data["nombre"], "Test Tenant")
        self.assertEqual(data["schema_name"], "test_tenant")

    def test_core_landing_activate_get_invalid_token_400(self):
        """GET /api/v1/core/landing/auth/activate/?token=invalid → 400."""
        response = self.client.get("/api/v1/core/landing/auth/activate/?token=invalid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn("detail", data)

    def test_core_landing_activate_get_no_token_400(self):
        """GET /api/v1/core/landing/auth/activate/ sin token → 400."""
        response = self.client.get("/api/v1/core/landing/auth/activate/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn("detail", data)
        self.assertIn("Token", data["detail"])

    def test_core_auth_login_200(self):
        """POST /api/v1/core/auth/login/ → 200 con redirect_url."""
        response = self.client.post(
            "/api/v1/core/auth/login/",
            {
                "email": "test@example.com",
                "password": "testpass123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("redirect_url", data)
        self.assertIn("detail", data)
        self.assertIn("user", data)
        self.assertIn("tenant", data)

    def test_core_auth_login_invalid_credentials_401(self):
        """POST /api/v1/core/auth/login/ con credenciales inválidas → 401."""
        response = self.client.post(
            "/api/v1/core/auth/login/",
            {
                "email": "test@example.com",
                "password": "wrongpassword",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertIn("detail", data)

    def test_core_auth_logout_200(self):
        """POST /api/v1/core/auth/logout/ → 200 con redirect_url."""
        # Primero hacer login
        self.client.post(
            "/api/v1/core/auth/login/",
            {
                "email": "test@example.com",
                "password": "testpass123",
            },
            format="json",
        )

        # Luego logout
        response = self.client.post("/api/v1/core/auth/logout/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("redirect_url", data)
        self.assertEqual(data["redirect_url"], "/")
        self.assertIn("detail", data)

    def test_core_auth_password_reset_request_200(self):
        """POST /api/v1/core/auth/password-reset/request/ → 200 (idempotente)."""
        response = self.client.post(
            "/api/v1/core/auth/password-reset/request/",
            {
                "email": "test@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("detail", data)

    def test_core_auth_password_reset_validate_invalid_400(self):
        """POST /api/v1/core/auth/password-reset/validate/ con token inválido → 400."""
        response = self.client.post(
            "/api/v1/core/auth/password-reset/validate/",
            {
                "uid": "invalid",
                "token": "invalid",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn("detail", data)

    def test_core_landing_activate_post_no_token_400(self):
        """POST /api/v1/core/landing/auth/activate/ sin token → 400."""
        response = self.client.post(
            "/api/v1/core/landing/auth/activate/",
            {
                "password1": "newpass123",
                "password2": "newpass123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn("detail", data)
        self.assertIn("Token", data["detail"])

    def test_core_landing_activate_post_no_passwords_400(self):
        """POST /api/v1/core/landing/auth/activate/?token=... sin passwords → 400."""
        response = self.client.post(
            "/api/v1/core/landing/auth/activate/?token=test", {}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn("detail", data)
        self.assertIn("contraseñas", data["detail"])
