"""
Tests funcionales del enrutamiento privado del tenant (Landing + Login + Dashboard).

Arquitectura v2.19:
- TenantMainMiddleware resuelve el tenant por dominio.
- TENANT_URLCONF = 'config.urls_tenant' para dominios privados.
- apps.tenant.landing actúa como router principal para /, /login/ y /logout/.
"""

from django.test import Client as TestClient
from django.urls import reverse

from tests.tenant.base_test import SintelTenantTestCase


class TenantLandingRoutingTests(SintelTenantTestCase):
    """
    Verifica el comportamiento de routing en un tenant privado:

    1. Anónimo en "/" → Landing Page (200) con nombre del tenant y link de login correcto.
    2. Autenticado en "/" → Redirección 302 a "/dashboard/".
    3. Acceso a "/login/" → Vista de login del tenant (200).
    """

    def test_anonymous_root_loads_landing_with_tenant_name_and_login_link(self):
        """
        Escenario 1 (Anónimo):
        - GET / sobre dominio de tenant privado.
        - Debe responder 200, renderizar la landing e incluir el nombre del tenant y el link de login.
        """
        domain_host = self.domain.domain

        anonymous_client = TestClient(HTTP_HOST=domain_host)

        response = anonymous_client.get("/")

        self.assertEqual(
            response.status_code,
            200,
            f"Root de tenant {domain_host} debe devolver 200 para anónimos.",
        )
        # Verificar que se está usando el template de landing
        self.assertTemplateUsed(response, "tenant/landing/index.html")

        # El nombre del tenant debe aparecer en la página (cuando Empresa esté configurada se reflejará ahí;
        # mientras tanto, usamos el nombre del tenant de prueba en los asserts de contenido de forma laxa)
        self.assertIn(
            self.tenant.schema_name.split("_")[0], response.content.decode().lower()
        )

        # Link de login debe apuntar a la URL namespaced del tenant
        expected_login_url = reverse("tenant_landing:login")
        self.assertIn(
            expected_login_url,
            response.content.decode(),
            "La landing debe contener un link hacia la URL de login del tenant.",
        )

    def test_authenticated_root_redirects_to_dashboard(self):
        """
        Escenario 2 (Autenticado):
        - Usuario autenticado accede a "/" en el dominio del tenant.
        - Debe redirigir 302 a "/dashboard/" (vista principal del tenant).
        """
        # self.client ya está autenticado y tiene HTTP_HOST=self.domain.domain
        response = self.client.get("/", follow=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("tenant_dashboard:index"),
            "Un usuario autenticado debe ser redirigido desde '/' a '/dashboard/'.",
        )

    def test_login_route_loads_login_view(self):
        """
        Escenario 3 (Ruta Login):
        - Acceder a "/login/" en el dominio del tenant.
        - Debe cargar la vista de login del tenant (200 OK).
        """
        domain_host = self.domain.domain
        anonymous_client = TestClient(HTTP_HOST=domain_host)

        response = anonymous_client.get(reverse("tenant_landing:login"))

        self.assertEqual(
            response.status_code,
            200,
            f"/login/ en dominio {domain_host} debe devolver 200.",
        )
