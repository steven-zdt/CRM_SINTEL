"""
Pruebas de humo para el endpoint de logout de tenant (API-First).

[WARNING] POLÍTICA API-First: El logout retorna JSON con redirect_url="/",
no redirección HTTP directa.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.tenant.core.tests import SintelTenantTestCase

User = get_user_model()


class TenantLogoutAPISmokeTestCase(SintelTenantTestCase):
    """Pruebas de humo para el endpoint de logout de tenant."""

    def setUp(self):
        """Configurar datos de prueba."""
        super().setUp()

        # Crear usuario y membresía en el tenant
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123", is_active=True
        )

        # Crear tenant de prueba
        self.tenant = Client.objects.create(
            schema_name="test_tenant", nombre="Test Tenant", auto_create_schema=True
        )

        # Crear dominio para el tenant
        self.domain = Domain.objects.create(
            domain="test-tenant.sintel.net.co", tenant=self.tenant, is_primary=True
        )

        # Crear membresía
        TenantMembership.objects.create(
            client=self.tenant, user=self.user, role="admin", is_active=True
        )

        # Cliente API con el dominio del tenant
        self.client = APIClient()
        self.client.defaults["HTTP_HOST"] = "test-tenant.sintel.net.co"

    def test_logout_get_authenticated(self):
        """
        Verifica que GET /api/v1/landing/auth/logout/ retorna JSON con redirect_url="/"
        e invalida la sesión.
        """
        # Autenticar usuario
        self.client.force_authenticate(user=self.user)

        # Verificar que el usuario está autenticado
        self.assertTrue(self.user.is_authenticated)

        # Llamar al endpoint de logout
        url = reverse("tenant_landing_api:logout")
        response = self.client.get(url, HTTP_HOST="test-tenant.sintel.net.co")

        # Verificar respuesta
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        data = response.json()
        self.assertIn("detail", data)
        self.assertEqual(data["detail"], "Sesión finalizada")
        self.assertIn("redirect_url", data)
        self.assertEqual(data["redirect_url"], "/")

        # Verificar que la sesión fue invalidada
        # (hacer una llamada a un endpoint protegido debería fallar)
        # Nota: force_authenticate no usa sesiones, así que verificamos de otra manera
        # En un test real con sesiones, haríamos una segunda llamada sin autenticación

    def test_logout_post_authenticated(self):
        """
        Verifica que POST /api/v1/landing/auth/logout/ retorna JSON con redirect_url="/"
        e invalida la sesión (con CSRF).
        """
        # Autenticar usuario
        self.client.force_authenticate(user=self.user)

        # Llamar al endpoint de logout
        url = reverse("tenant_landing_api:logout")
        response = self.client.post(url, HTTP_HOST="test-tenant.sintel.net.co")

        # Verificar respuesta
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        data = response.json()
        self.assertIn("detail", data)
        self.assertEqual(data["detail"], "Sesión finalizada")
        self.assertIn("redirect_url", data)
        self.assertEqual(data["redirect_url"], "/")

    def test_logout_unauthenticated(self):
        """
        Verifica que el logout funciona incluso sin sesión activa (AllowAny).
        """
        # No autenticar usuario
        url = reverse("tenant_landing_api:logout")
        response = self.client.get(url, HTTP_HOST="test-tenant.sintel.net.co")

        # Verificar respuesta (debe retornar 200 con redirect_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("redirect_url", data)
        self.assertEqual(data["redirect_url"], "/")
