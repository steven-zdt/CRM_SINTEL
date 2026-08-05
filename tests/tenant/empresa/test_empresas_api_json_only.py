"""
Pruebas de humo para garantizar que el endpoint /api/v1/empresas/
retorna SOLO JSON (sin HTML navegable).

[WARNING] POLÍTICA API-First: Los endpoints DRF NUNCA deben devolver HTML.
"""

from rest_framework import status

from tests.tenant.base_test import SintelTenantTestCase


class TestEmpresasAPIJSONOnly(SintelTenantTestCase):
    """
    Pruebas para verificar que el endpoint de empresas retorna solo JSON.
    """

    def test_empresas_endpoint_returns_json(self):
        """
        Verifica que GET /api/v1/empresas/ retorna 200 OK con Content-Type application/json.
        """
        response = self.api_client.get("/api/v1/empresas/")

        # Verificar status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verificar Content-Type
        self.assertIn("application/json", response["Content-Type"])

        # Verificar que la respuesta es JSON válido
        data = response.json()
        self.assertIsInstance(data, (list, dict))

    def test_empresas_endpoint_no_html(self):
        """
        Verifica que GET /api/v1/empresas/ NO contiene etiquetas HTML.
        """
        response = self.api_client.get("/api/v1/empresas/")

        # Verificar status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Obtener contenido como texto
        content = response.content.decode("utf-8")

        # Verificar que NO contiene etiquetas HTML comunes del BrowsableAPIRenderer
        html_tags = ["<html", "<pre", "json-formatter-container", "<body", "<head"]
        for tag in html_tags:
            self.assertNotIn(
                tag,
                content.lower(),
                f"El endpoint contiene HTML ({tag}). Debe retornar solo JSON.",
            )

    def test_empresas_endpoint_structure(self):
        """
        Verifica la estructura básica de la respuesta JSON.
        """
        response = self.api_client.get("/api/v1/empresas/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # La respuesta debe ser un array (puede estar vacío o contener empresas)
        self.assertIsInstance(data, list)

        # Si hay empresas, verificar estructura
        if len(data) > 0:
            empresa = data[0]
            self.assertIn("id", empresa)
            self.assertIn("razon_social", empresa)
            self.assertIn("nit", empresa)

    def test_empresas_endpoint_authentication_required(self):
        """
        Verifica que el endpoint requiere autenticación (401 si no está autenticado).
        """
        from rest_framework.test import APIClient

        # Cliente no autenticado
        client = APIClient()
        response = client.get("/api/v1/empresas/")

        # Debe retornar 401 Unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
