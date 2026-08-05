"""
Test de Garantía: Routing de Landing Page Pública (Sección 9.6).

[WARNING] OBJETIVO CRÍTICO: Garantizar que la raíz de un tenant (/) siempre muestre
la Landing Page Pública con status 200 OK para usuarios anónimos, sin redirección
automática al login.

[WARNING] REQUISITO DE NEGOCIO:
- Usuario anónimo accediendo a http://tenant.com/ → 200 OK (Landing Page)
- Usuario autenticado accediendo a http://tenant.com/ → 302 (Redirige a /dashboard/)
- NUNCA debe redirigir automáticamente a /admin/login/ para usuarios anónimos

Este test es INQUEBRANTABLE: Si alguien rompe esta regla en el futuro, el test fallará.
"""

from django.test import Client
from django.urls import reverse

from apps.public.tenants.models import Client as TenantClient
from apps.public.tenants.models import Domain
from tests.tenant.base_test import SintelTenantTestCase


class TestRoutingGuarantee(SintelTenantTestCase):
    """
    Test de Garantía para el Routing de Landing Page.

    Este test valida estrictamente que:
    1. La raíz (/) muestra la landing page pública (200 OK) para usuarios anónimos
    2. NO hay redirección automática al login (status no es 301 ni 302)
    3. El template correcto se renderiza (tenant/landing/index.html)
    4. Usuarios autenticados son redirigidos al dashboard (302)

    [WARNING] INQUEBRANTABLE: Este test debe pasar SIEMPRE. Si falla, significa que
    se violó la regla de negocio de la Sección 9.6.
    """

    @classmethod
    def setup_tenant(cls, tenant_user=None):
        """
        Crea un tenant específico para este test de garantía.

        Usa el dominio 'garantia.com' para que sea claro que es un test de garantía.
        """
        # Crear tenant con schema_name específico
        tenant = TenantClient.objects.create(
            schema_name="garantia",
            nombre="Tenant de Garantía",
            is_active=True,
            on_trial=False,
        )
        return tenant

    @classmethod
    def setup_domain(cls, domain):
        """
        Configura el dominio específico para este test.

        Usa 'garantia.com' como dominio para que sea claro en los tests.
        """
        domain.domain = "garantia.com"
        domain.is_primary = True
        domain.save()
        return domain

    def setUp(self):
        """
        Setup: Configurar tenant y cliente HTTP.

        Crea un cliente HTTP sin autenticación para probar acceso anónimo.
        """
        # Llamar al setUp del padre (crea tenant, domain, user, membership)
        super().setUp()

        # Crear cliente HTTP anónimo (sin autenticación)
        # [WARNING] VITAL: Configurar HTTP_HOST para que el middleware de routing funcione
        self.anonymous_client = Client(HTTP_HOST=self.domain.domain)

        # Cliente autenticado ya está disponible en self.client (del setUp del padre)
        # Pero también podemos usar self.client para el caso autenticado

    def test_anonymous_user_root_access_200_ok(self):
        """
        CASO 1 (LA GARANTÍA): Usuario anónimo accediendo a la raíz.

        [WARNING] ASSERT OBLIGATORIO 1: Status debe ser 200 OK
        [WARNING] ASSERT OBLIGATORIO 2: Template debe ser tenant/landing/index.html
        [WARNING] ASSERT DE NEGACIÓN: NO debe haber redirección (status no es 301 ni 302)

        Este es el test MÁS IMPORTANTE: Garantiza que usuarios anónimos
        pueden ver la landing page sin ser redirigidos al login.
        """
        # Hacer GET a la raíz sin autenticación
        response = self.anonymous_client.get("/")

        # [WARNING] ASSERT OBLIGATORIO 1: Status debe ser 200 OK
        self.assertEqual(
            response.status_code,
            200,
            "[ERROR] VIOLACIÓN DE REGLA: La raíz debe retornar 200 OK para usuarios anónimos. "
            "Si recibes 302 o 301, significa que hay una redirección automática al login. "
            "Esto está PROHIBIDO según la Sección 9.6 de arquitectura_general.md",
        )

        # [WARNING] ASSERT DE NEGACIÓN: NO debe haber redirección
        self.assertNotIn(
            response.status_code,
            [301, 302],
            "[ERROR] VIOLACIÓN DE REGLA: La raíz NO debe redirigir (301/302) a usuarios anónimos. "
            "Si recibes una redirección, significa que hay un middleware o vista "
            "forzando el login automáticamente. Esto está PROHIBIDO.",
        )

        # [WARNING] ASSERT OBLIGATORIO 2: Template debe ser tenant/landing/index.html
        # Verificar que se usó el template correcto
        self.assertTemplateUsed(
            response,
            "tenant/landing/index.html",
            msg_prefix="[ERROR] VIOLACIÓN DE REGLA: El template usado debe ser 'tenant/landing/index.html'. "
            "Si se usa otro template, significa que la vista no está configurada correctamente.",
        )

        # Verificación adicional: El contenido debe ser HTML (no una redirección)
        self.assertIn(
            "text/html",
            response.get("Content-Type", ""),
            "[ERROR] VIOLACIÓN DE REGLA: La respuesta debe ser HTML, no una redirección.",
        )

    def test_anonymous_user_no_redirect_to_login(self):
        """
        CASO 1B: Verificación adicional de que NO hay redirección al login.

        Este test verifica explícitamente que la respuesta NO es una redirección
        a /admin/login/ o cualquier otra URL de login.
        """
        response = self.anonymous_client.get("/")

        # Verificar que NO es una redirección
        self.assertNotEqual(
            response.status_code,
            302,
            "[ERROR] VIOLACIÓN DE REGLA: La raíz NO debe redirigir (302) a usuarios anónimos.",
        )

        # Verificar que la URL de respuesta NO es una redirección al login
        if hasattr(response, "url"):
            self.assertNotIn(
                "login",
                response.url.lower(),
                "[ERROR] VIOLACIÓN DE REGLA: La respuesta NO debe redirigir a ninguna URL de login. "
                "Si redirige a /admin/login/ o /login/, significa que hay una configuración "
                "incorrecta que fuerza el login automáticamente.",
            )

        # Verificar que el Location header NO está presente (no hay redirección)
        self.assertNotIn(
            "Location",
            response,
            "[ERROR] VIOLACIÓN DE REGLA: La respuesta NO debe tener header 'Location' "
            "(indica redirección). Si tiene Location, significa que hay una redirección automática.",
        )

    def test_authenticated_user_redirects_to_dashboard(self):
        """
        CASO 2: Usuario autenticado accediendo a la raíz.

        [WARNING] ASSERT: Debe redirigir (302) a /dashboard/

        Este test valida que usuarios autenticados son redirigidos correctamente
        al dashboard, no a la landing page.
        """
        # self.client ya está autenticado (del setUp del padre)
        # Hacer GET a la raíz con usuario autenticado
        response = self.client.get("/")

        # [WARNING] ASSERT: Debe redirigir (302) al dashboard
        self.assertEqual(
            response.status_code,
            302,
            "[ERROR] VIOLACIÓN DE REGLA: Usuarios autenticados deben ser redirigidos (302) "
            "al dashboard cuando acceden a la raíz. Si recibes 200, significa que "
            "la vista no está redirigiendo correctamente.",
        )

        # Verificar que la redirección es al dashboard
        self.assertIn(
            "/dashboard/",
            response.url,
            "[ERROR] VIOLACIÓN DE REGLA: La redirección debe ser a '/dashboard/', no a otra URL. "
            f"URL recibida: {response.url}",
        )

    def test_anonymous_user_can_access_landing_template(self):
        """
        CASO 1C: Verificación adicional del contenido del template.

        Verifica que el template se renderiza correctamente y contiene
        elementos esperados de la landing page.
        """
        response = self.anonymous_client.get("/")

        # Verificar que el status es 200
        self.assertEqual(response.status_code, 200)

        # Verificar que el template se usó
        self.assertTemplateUsed(response, "tenant/landing/index.html")

        # Verificar que el contenido es HTML válido (contiene elementos básicos)
        content = response.content.decode("utf-8").lower()

        # El template debe contener al menos algunos elementos básicos
        # (esto depende de tu template, pero al menos debe tener HTML básico)
        has_html = "<html" in content or "<body" in content or "<!doctype" in content
        self.assertTrue(
            has_html,
            "[ERROR] VIOLACIÓN DE REGLA: El template debe renderizar HTML válido. "
            "Si no contiene HTML básico, significa que hay un problema con el template.",
        )

    def test_root_url_resolves_to_landing_view(self):
        """
        CASO 1D: Verificación de que la URL raíz resuelve correctamente.

        Verifica que la configuración de URLs está correcta y que la raíz
        apunta a TenantLandingView.
        """
        from django.urls import resolve

        from apps.tenant.landing.views import TenantLandingView

        # Resolver la URL raíz
        match = resolve("/")

        # Verificar que la vista es TenantLandingView
        self.assertEqual(
            match.func.view_class,
            TenantLandingView,
            "[ERROR] VIOLACIÓN DE REGLA: La URL raíz (/) debe resolver a TenantLandingView. "
            "Si resuelve a otra vista, significa que la configuración de URLs está incorrecta.",
        )

        # Verificar que el nombre de la URL es correcto
        self.assertEqual(
            match.url_name,
            "index",
            "[ERROR] VIOLACIÓN DE REGLA: El nombre de la URL debe ser 'index'. "
            "Si es otro nombre, significa que la configuración de URLs está incorrecta.",
        )

        # Verificar que el app_name es correcto
        self.assertEqual(
            match.app_name,
            "tenant_landing",
            "[ERROR] VIOLACIÓN DE REGLA: El app_name debe ser 'tenant_landing'. "
            "Si es otro nombre, significa que la configuración de URLs está incorrecta.",
        )
