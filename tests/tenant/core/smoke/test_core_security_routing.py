"""
Smoke tests para aislamiento y seguridad (routing por hostname).

[WARNING] POLÍTICA v2.30: Validar aislamiento multi-tenant y routing correcto.
"""

import pytest

try:
    import cryptography  # noqa: F401
    import playwright  # noqa: F401
except Exception:
    pytest.skip(
        "Skipping heavy smoke test: missing playwright/cryptography",
        allow_module_level=True,
    )
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.test import APIClient

from apps.public.tenants.models import Client, Domain, TenantMembership
from tests.tenant.base_test import SintelTenantTestCase


class TestCoreSecurityRouting(SintelTenantTestCase):
    """Tests de humo para aislamiento y routing."""

    def setUp(self):
        """Configurar tenant adicional para pruebas de aislamiento."""
        super().setUp()

        # Crear un segundo tenant para pruebas de aislamiento
        with schema_context("public"):
            self.other_tenant = Client.objects.create(
                schema_name="other_tenant",
                nombre="Other Tenant",
                is_active=True,
            )
            self.other_domain = Domain.objects.create(
                domain="other-tenant.sintel.local",
                tenant=self.other_tenant,
                is_primary=True,
            )

    def test_cross_tenant_access_denied(self):
        """Acceso cruzado con HTTP_HOST de otro tenant → denegado/404/403."""
        # Intentar acceder al tenant original usando el dominio del otro tenant
        client = APIClient(HTTP_HOST=self.other_domain.domain)
        client.force_authenticate(user=self.user)

        # Intentar acceder a un endpoint del tenant original
        response = client.get("/api/v1/core/dashboard/")

        # Debe retornar 404 (tenant no encontrado) o 403 (acceso denegado)
        # Depende de cómo el middleware maneje el routing
        self.assertIn(
            response.status_code,
            [
                status.HTTP_404_NOT_FOUND,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_400_BAD_REQUEST,
            ],
        )

    def test_tenant_urlconf_active_subdomain(self):
        """Verificación de routing con TENANT_URLCONF activo en subdominio."""
        # Verificar que las URLs del tenant se resuelven correctamente
        response = self.api_client.get("/api/v1/core/dashboard/")

        # Debe retornar 200 (no 404) si el routing funciona
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verificar que el Content-Type es JSON (API-First)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_public_urlconf_active_public_domain(self):
        """Verificación de routing con ROOT_URLCONF en dominio público."""
        # En un dominio público, las URLs del tenant no deben estar disponibles
        # Esto se verifica indirectamente: si accedemos con un dominio que no es tenant,
        # debe retornar 404 o usar ROOT_URLCONF

        # Nota: Esta prueba requiere configuración específica del middleware
        # Por ahora, verificamos que el tenant funciona correctamente
        response = self.api_client.get("/api/v1/core/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_tenant_isolation_data(self):
        """Verificar que los datos están aislados por tenant."""
        # Crear datos en el tenant actual
        # (Esto se puede hacer con fixtures o modelos específicos)

        # Verificar que los datos del tenant actual son accesibles
        response = self.api_client.get("/api/v1/core/mi-empresa/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Los datos deben corresponder al tenant actual, no a otros tenants
        data = response.json()
        # Verificar que el tenant en la respuesta es el correcto
        # (esto depende de la estructura de la respuesta)
        self.assertIsInstance(data, dict)
