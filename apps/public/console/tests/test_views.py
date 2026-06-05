"""
Tests de vistas HTML para apps/public/console/.

Cubre:
- Control de acceso (anonimo → 302, no-staff → 403, staff → 200)
- Templates correctos para dashboard, tenants, users
- Context data basico

Convenciones del proyecto:
- Host: 'localhost' (resuelve al schema public en django-tenants)
- Autenticacion: client.force_login() para sesiones
"""
from django.test import TestCase
from django.urls import reverse

from .conftest import make_normal_user, make_staff_user


class DashboardViewAccessTest(TestCase):
    """Control de acceso a /console/ (DashboardView)."""

    def setUp(self) -> None:
        self.url: str = reverse("console:dashboard")
        self.normal_user = make_normal_user("dash_normal@t.test")
        self.staff_user = make_staff_user("dash_staff@t.test")
        # django-tenants: usar localhost que resuelve al schema public
        self.client.defaults["SERVER_NAME"] = "localhost"

    def test_anonymous_redirects_to_login(self) -> None:
        """Un usuario anonimo recibe HTTP 302 hacia la pagina de login."""
        response = self.client.get(self.url, SERVER_NAME="localhost")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_non_staff_receives_403(self) -> None:
        """Un usuario autenticado sin is_staff=True recibe HTTP 403."""
        self.client.force_login(self.normal_user)
        response = self.client.get(self.url, SERVER_NAME="localhost")
        self.assertEqual(response.status_code, 403)

    def test_staff_receives_200_and_correct_template(self) -> None:
        """Un usuario staff recibe HTTP 200 y renderiza el template del dashboard."""
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url, SERVER_NAME="localhost")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "console/dashboard.html")

    def test_staff_context_has_user(self) -> None:
        """El contexto del dashboard expone el usuario autenticado."""
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url, SERVER_NAME="localhost")
        self.assertEqual(response.status_code, 200)
        self.assertIn("user", response.context)
        self.assertEqual(response.context["user"].pk, self.staff_user.pk)


class TenantsListViewAccessTest(TestCase):
    """Control de acceso a /console/tenants/ (TenantsListView)."""

    def setUp(self) -> None:
        self.url: str = reverse("console:tenants-list")
        self.normal_user = make_normal_user("tlist_normal@t.test")
        self.staff_user = make_staff_user("tlist_staff@t.test")

    def test_anonymous_redirects_to_login(self) -> None:
        """Anonimo → 302 hacia login."""
        response = self.client.get(self.url, SERVER_NAME="localhost")
        self.assertEqual(response.status_code, 302)

    def test_non_staff_receives_403(self) -> None:
        """No-staff → 403."""
        self.client.force_login(self.normal_user)
        response = self.client.get(self.url, SERVER_NAME="localhost")
        self.assertEqual(response.status_code, 403)

    def test_staff_receives_200_and_correct_template(self) -> None:
        """Staff → 200 con template de lista de tenants."""
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url, SERVER_NAME="localhost")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "console/pages/tenants/list.html")

    def test_staff_context_has_api_url(self) -> None:
        """El contexto expone la URL del endpoint DataTables de tenants."""
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url, SERVER_NAME="localhost")
        self.assertIn("api_url", response.context)
        self.assertIn("/api/admin/v1/console/dt/tenants/", response.context["api_url"])


class UsersListViewAccessTest(TestCase):
    """Control de acceso a /console/users/ (UsersListView)."""

    def setUp(self) -> None:
        self.url: str = reverse("console:users-list")
        self.normal_user = make_normal_user("ulist_normal@t.test")
        self.staff_user = make_staff_user("ulist_staff@t.test")

    def test_anonymous_redirects_to_login(self) -> None:
        """Anonimo → 302 hacia login."""
        response = self.client.get(self.url, SERVER_NAME="localhost")
        self.assertEqual(response.status_code, 302)

    def test_non_staff_receives_403(self) -> None:
        """No-staff → 403."""
        self.client.force_login(self.normal_user)
        response = self.client.get(self.url, SERVER_NAME="localhost")
        self.assertEqual(response.status_code, 403)

    def test_staff_receives_200_and_correct_template(self) -> None:
        """Staff → 200 con template de lista de usuarios."""
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url, SERVER_NAME="localhost")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "console/pages/users/list.html")

    def test_staff_context_has_api_url(self) -> None:
        """El contexto expone la URL del endpoint DataTables de usuarios."""
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url, SERVER_NAME="localhost")
        self.assertIn("api_url", response.context)
        self.assertIn("/api/admin/v1/console/dt/users/", response.context["api_url"])


class TenantsNewViewAccessTest(TestCase):
    """Control de acceso a /console/tenants/new/ (TenantsNewView)."""

    def setUp(self) -> None:
        self.url: str = reverse("console:tenants-new")
        self.normal_user = make_normal_user("tnew_normal@t.test")
        self.staff_user = make_staff_user("tnew_staff@t.test")

    def test_anonymous_redirects(self) -> None:
        """Anonimo → 302."""
        response = self.client.get(self.url, SERVER_NAME="localhost")
        self.assertEqual(response.status_code, 302)

    def test_non_staff_receives_403(self) -> None:
        """No-staff → 403."""
        self.client.force_login(self.normal_user)
        response = self.client.get(self.url, SERVER_NAME="localhost")
        self.assertEqual(response.status_code, 403)

    def test_staff_receives_200(self) -> None:
        """Staff → 200."""
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url, SERVER_NAME="localhost")
        self.assertEqual(response.status_code, 200)
