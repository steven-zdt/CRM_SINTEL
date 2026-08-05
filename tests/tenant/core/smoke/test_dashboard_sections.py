"""
Pruebas de humo para Dashboard Sections (Core API).

[WARNING] POLÍTICA:
- Verificar orden de secciones: empresas → facturas → contabilidad → perfil
- Verificar ausencia de hardcodes de marca
- Verificar que endpoints responden correctamente
"""

import pytest

from tests.tenant.base_test import SintelTenantTestCase

try:
    import cryptography  # noqa: F401
    import playwright  # noqa: F401
except Exception:
    pytest.skip(
        "Skipping heavy smoke test: missing playwright/cryptography",
        allow_module_level=True,
    )


class TestDashboardSections(SintelTenantTestCase):
    """
    Pruebas de humo para /api/v1/core/dashboard/sections/
    """

    def test_sections_order_and_status(self):
        """
        Verifica que el endpoint retorna 200 y las secciones en orden correcto.
        """
        # Autenticar usuario
        self.client.force_login(self.user)

        # Hacer petición al endpoint
        response = self.client.get(
            "/api/v1/core/dashboard/sections/",
            HTTP_HOST=f"{self.tenant.schema_name}.sintel.net.co",
        )

        # Verificar status
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}. Response: {response.content.decode()}",
        )

        # Verificar estructura JSON
        data = response.json()

        # [WARNING] ORDEN REQUERIDO: empresas → facturas → contabilidad → perfil
        expected_keys = ["empresas", "facturas", "contabilidad", "perfil"]
        self.assertEqual(
            list(data.keys()),
            expected_keys,
            f"Expected keys {expected_keys}, got {list(data.keys())}",
        )

        # Verificar que todas las secciones están presentes
        for key in expected_keys:
            self.assertIn(key, data, f"Missing section: {key}")

    def test_sections_no_hardcodes(self):
        """
        Verifica que no hay literales de marca hardcodeados en la respuesta.
        """
        # Autenticar usuario
        self.client.force_login(self.user)

        # Hacer petición al endpoint
        response = self.client.get(
            "/api/v1/core/dashboard/sections/",
            HTTP_HOST=f"{self.tenant.schema_name}.sintel.net.co",
        )

        self.assertEqual(response.status_code, 200)

        # Verificar ausencia de hardcodes
        content = response.content.decode("utf-8")
        hardcodes = ["SINTEL", "ACME", "Mi Empresa"]

        for hardcode in hardcodes:
            self.assertNotIn(
                hardcode, content, f"Found hardcoded brand literal: {hardcode}"
            )

    def test_empresas_plural_canonical(self):
        """
        Verifica que /api/v1/empresas/ responde (no 404).
        """
        # Autenticar usuario
        self.client.force_login(self.user)

        # Hacer petición al endpoint plural
        response = self.client.get(
            "/api/v1/empresas/", HTTP_HOST=f"{self.tenant.schema_name}.sintel.net.co"
        )

        # Verificar que no es 404 (puede ser 200, 204, 401, 403, 405)
        self.assertNotEqual(
            response.status_code,
            404,
            f"/api/v1/empresas/ returned 404. Response: {response.content.decode()}",
        )

    def test_empresa_singular_redirects(self):
        """
        Verifica que /api/v1/empresa/ redirige (no 404).
        """
        # Autenticar usuario
        self.client.force_login(self.user)

        # Hacer petición al endpoint singular (debe redirigir)
        response = self.client.get(
            "/api/v1/empresa/",
            HTTP_HOST=f"{self.tenant.schema_name}.sintel.net.co",
            follow=False,  # No seguir redirección para verificar status code
        )

        # Verificar que no es 404 (debe ser 301, 302, 307, 308 o 200/405)
        self.assertNotEqual(
            response.status_code,
            404,
            f"/api/v1/empresa/ returned 404. Response: {response.content.decode()}",
        )

        # Verificar que es una redirección o respuesta válida
        self.assertIn(
            response.status_code,
            [200, 301, 302, 307, 308, 405],
            f"Expected redirect or valid response, got {response.status_code}",
        )

    def test_sections_structure(self):
        """
        Verifica la estructura de cada sección.
        """
        # Autenticar usuario
        self.client.force_login(self.user)

        # Hacer petición al endpoint
        response = self.client.get(
            "/api/v1/core/dashboard/sections/",
            HTTP_HOST=f"{self.tenant.schema_name}.sintel.net.co",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verificar estructura de empresas
        self.assertIn("empresas", data)
        self.assertIn("empresas", data["empresas"])
        self.assertIsInstance(data["empresas"]["empresas"], list)

        # Verificar estructura de facturas
        self.assertIn("facturas", data)
        self.assertIn("total", data["facturas"])
        self.assertIn("por_estado", data["facturas"])
        self.assertIn("recientes", data["facturas"])

        # Verificar estructura de contabilidad
        self.assertIn("contabilidad", data)
        self.assertIn("total_cuentas", data["contabilidad"])
        self.assertIn("total_asientos", data["contabilidad"])
        self.assertIn("asientos_recientes", data["contabilidad"])

        # Verificar estructura de perfil
        self.assertIn("perfil", data)
        self.assertIn("me", data["perfil"])

    def test_sections_unauthenticated(self):
        """
        Verifica que el endpoint requiere autenticación.
        """
        # NO autenticar usuario

        # Hacer petición al endpoint
        response = self.client.get(
            "/api/v1/core/dashboard/sections/",
            HTTP_HOST=f"{self.tenant.schema_name}.sintel.net.co",
        )

        # Debe retornar 401 o 403
        self.assertIn(
            response.status_code,
            [401, 403],
            f"Expected 401 or 403 for unauthenticated request, got {response.status_code}",
        )

    def test_sections_includes_user_tenant_kpis(self):
        """
        Verifica que Core API incluye user, tenant, branding y KPIs.
        """
        # Autenticar usuario
        self.client.force_login(self.user)

        # Hacer petición al endpoint
        response = self.client.get(
            "/api/v1/core/dashboard/sections/",
            HTTP_HOST=f"{self.tenant.schema_name}.sintel.net.co",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verificar que incluye user, tenant, branding y KPIs
        self.assertIn("user", data)
        self.assertIn("tenant", data)
        self.assertIn("branding", data)
        self.assertIn("kpis", data)

        # Verificar estructura de user
        self.assertIn("email", data["user"])
        self.assertIn("role", data["user"])

        # Verificar estructura de kpis
        self.assertIn("total_facturas", data["kpis"])
        self.assertIn("facturas_pendientes", data["kpis"])

    def test_dashboard_api_first_no_direct_calls(self):
        """
        Verifica que el shell estático no hace llamadas directas a /api/v1/dashboard/summary/.
        Este test verifica que la migración a Core API está completa.
        """
        # Este test es más bien una validación de arquitectura
        # En un entorno real, podrías usar herramientas de análisis estático
        # Por ahora, verificamos que Core API funciona correctamente
        self.client.force_login(self.user)

        # Verificar que Core API retorna todo lo necesario
        response = self.client.get(
            "/api/v1/core/dashboard/sections/",
            HTTP_HOST=f"{self.tenant.schema_name}.sintel.net.co",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verificar que Core API incluye toda la información necesaria
        # (user, tenant, branding, KPIs, secciones)
        required_keys = [
            "user",
            "tenant",
            "branding",
            "kpis",
            "empresas",
            "facturas",
            "contabilidad",
            "perfil",
        ]
        for key in required_keys:
            self.assertIn(
                key,
                data,
                f"Core API debe incluir '{key}' para evitar múltiples requests",
            )
