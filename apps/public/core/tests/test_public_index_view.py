"""
Smoke tests — PublicIndexView (/  en el esquema publico).

Verifica que la logica de redireccion inteligente del SSoT de enrutamiento
no falle silenciosamente ante cambios en permisos, URL patterns o middlewares.

Comportamiento actual de PublicIndexView:
  - Anonimo              → 200 (renderiza landing page)
  - Staff / superuser    → 302 → console:dashboard
  - Autenticado normal   → 302 → admin:login (independientemente de membresias)

Test 3 y 4 documentan ademas el comportamiento esperado a futuro (membresia
activa → workspace del tenant), marcado con FUTURE para rastrear la evolucion.
"""

from django.contrib.auth import get_user_model
from django.test import Client as HttpClient
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class TestPublicIndexView(TestCase):
    """Suite de smoke tests para PublicIndexView (SSoT de redireccion del dominio publico)."""

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    def setUp(self) -> None:
        super().setUp()
        self.http = HttpClient()
        self.url = reverse("public_index")

        self.normal_user = User.objects.create_user(
            username="normal@sintel.net.co",
            email="normal@sintel.net.co",
            password="S3cur3Pass!",
            is_active=True,
        )
        self.staff_user = User.objects.create_user(
            username="staff@sintel.net.co",
            email="staff@sintel.net.co",
            password="S3cur3Pass!",
            is_staff=True,
            is_active=True,
        )

    # ------------------------------------------------------------------
    # Test 1 — Usuario anonimo
    # ------------------------------------------------------------------

    def test_anonymous_user_redirect(self) -> None:
        """
        Un usuario no autenticado recibe la landing page (HTTP 200).

        La landing page es el punto de entrada natural del dominio publico;
        no se fuerza un redirect al login para no romper el flujo de marketing.
        Este test falla si alguien agrega un redirect incorrecto para anonimos.
        """
        response = self.http.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "public/core/index.html")

    # ------------------------------------------------------------------
    # Test 2 — Usuario staff
    # ------------------------------------------------------------------

    def test_staff_user_redirect(self) -> None:
        """
        Un usuario autenticado con is_staff=True recibe HTTP 302 hacia /console/.

        La consola de administracion es el destino natural para el equipo interno.
        Si este test falla, check: console:dashboard URL name, is_staff flag, dispatch logic.
        """
        self.http.force_login(self.staff_user)
        response = self.http.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("console:dashboard"),
            fetch_redirect_response=False,
        )

    # ------------------------------------------------------------------
    # Test 3 — Miembro activo de un tenant
    # ------------------------------------------------------------------

    def test_tenant_member_redirect(self) -> None:
        """
        Un usuario autenticado con TenantMembership activa recibe HTTP 302.

        Comportamiento actual: redirige a admin:login (ruta de redireccion
        inteligente configurada para usuarios normales autenticados).

        FUTURE: cuando PublicIndexView detecte membresias, este test debe
        actualizarse para verificar redirect al workspace del tenant:
            expected = f"http://{domain}/workspace/"
            self.assertRedirects(response, expected, fetch_redirect_response=False)
        """
        from apps.public.tenants.models import Client, Domain, TenantMembership

        # Crear Client (tenant) en el esquema publico
        tenant = Client.objects.create(
            schema_name="testmember",
            nombre="Test Member Co",
            is_active=True,
        )
        Domain.objects.create(
            tenant=tenant,
            domain="testmember.sintel.net.co",
            is_primary=True,
        )
        TenantMembership.objects.create(
            client=tenant,
            user=self.normal_user,
            rol="ADMIN",
            is_primary_admin=True,
            is_active=True,
        )

        self.http.force_login(self.normal_user)
        response = self.http.get(self.url)

        # Comportamiento actual configurado: cualquier usuario no-staff va a admin:login
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("admin:login"),
            fetch_redirect_response=False,
        )

    # ------------------------------------------------------------------
    # Test 4 — Autenticado sin membresias
    # ------------------------------------------------------------------

    def test_authenticated_user_no_membership(self) -> None:
        """
        Un usuario autenticado sin TenantMemberships activas recibe HTTP 302.

        Comportamiento actual: redirige a admin:login.
        Sin membresía no se puede ingresar a ningun workspace, por lo que la
        vista de login es el fallback correcto hasta que se implemente /onboard/.

        FUTURE: si se agrega vista /onboard/, actualizar la asercion a:
            self.assertRedirects(response, "/onboard/", fetch_redirect_response=False)
        """
        # Verificar que este usuario no tiene membresias
        from apps.public.tenants.models import TenantMembership

        self.assertEqual(
            TenantMembership.objects.filter(user=self.normal_user, is_active=True).count(),
            0,
            "El usuario de prueba no debe tener membresias al inicio del test.",
        )

        self.http.force_login(self.normal_user)
        response = self.http.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("admin:login"),
            fetch_redirect_response=False,
        )
