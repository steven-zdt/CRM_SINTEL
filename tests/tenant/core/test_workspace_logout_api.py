"""
Tests de humo para el logout API-First desde el dropdown.

Verifica que:
- POST /api/v1/core/auth/logout/ funciona correctamente con CSRF
- Retorna redirect_url en la respuesta JSON
- El logout funciona sin sesión (idempotente)
"""

from django.test import Client
from rest_framework import status

from tests.tenant.base_test import SintelTenantTestCase


class TestWorkspaceLogoutAPI(SintelTenantTestCase):
    """
    Tests de humo para verificar el logout API-First desde el dropdown.
    """

    def test_logout_post_returns_200_with_redirect_url(self):
        """
        Verifica que POST /api/v1/core/auth/logout/ retorna 200 con redirect_url.
        """
        # Obtener CSRF token
        csrf_client = self.client
        csrf_client.get("/workspace/")  # Obtener cookie de sesión y CSRF

        # Obtener token CSRF de la cookie
        csrftoken = csrf_client.cookies.get("csrftoken")

        # Hacer POST al endpoint de logout
        response = self.api_client.post(
            "/api/v1/core/auth/logout/",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrftoken.value if csrftoken else None,
        )

        # Debe retornar 200 OK con redirect_url
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("redirect_url", data)
        self.assertIn("detail", data)

    def test_logout_get_also_works(self):
        """
        Verifica que GET /api/v1/core/auth/logout/ también funciona (redirige directamente).
        """
        response = self.client.get("/api/v1/core/auth/logout/")

        # GET debe redirigir (302) o retornar 200
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_302_FOUND])

    def test_logout_without_session_is_idempotent(self):
        """
        Verifica que el logout es idempotente (funciona sin sesión).
        """
        # Crear cliente sin autenticar
        anon_client = Client(HTTP_HOST=self.domain.domain)

        # Intentar logout sin sesión (debe funcionar)
        response = anon_client.post(
            "/api/v1/core/auth/logout/", {}, content_type="application/json"
        )

        # Debe retornar 200 o 400 (pero no 500)
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
        )
