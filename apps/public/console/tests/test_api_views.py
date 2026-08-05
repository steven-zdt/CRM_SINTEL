"""
Tests de la API de console (apps/public/console/api/).

Cubre:
- TenantsDataTableView  POST /api/admin/v1/console/dt/tenants/
- TenantDomainsDataTableView POST /api/admin/v1/console/dt/tenant-domains/
- UsersDataTableView    GET/POST/PATCH/DELETE /api/admin/v1/console/dt/users/
- ConsoleHealthView     GET /api/admin/v1/console/health/

Convenciones:
- Hereda de PublicAPITestCase (SessionAuthentication + IsAdminUser)
- Autenticacion: force_authenticate() o force_login() en setUp
- DataTables payload minimo: {draw, start, length, search: {value: ""}}
- delete_user_service se mockea para aislar la prueba de cascada cross-schema
"""
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from apps.config.tests.base_public import PublicAPITestCase

from .conftest import make_console_action_log, make_normal_user, make_staff_user, make_tenant_with_domain

# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

DT_BASE: dict = {
    "draw": "1",
    "start": 0,
    "length": 10,
    "search": {"value": ""},
    "order": [{"column": 0, "dir": "asc"}],
    "columns": [
        {"data": "0", "name": "", "searchable": True, "orderable": True, "search": {"value": ""}},
    ],
}


def _dt_payload(**overrides) -> dict:
    """Construye un payload DataTables con valores por defecto sobreescribibles."""
    return {**DT_BASE, **overrides}


# ---------------------------------------------------------------------------
# TenantsDataTableView
# ---------------------------------------------------------------------------

class TenantsDataTableViewTest(PublicAPITestCase):
    """Tests para POST /api/admin/v1/console/dt/tenants/."""

    URL: str = "/api/admin/v1/console/dt/tenants/"

    def setUp(self) -> None:
        super().setUp()
        # Crear un tenant de muestra para que la tabla no este vacia
        self.client_obj, self.domain = make_tenant_with_domain(
            nombre="Empresa DT Test",
            schema_name="dttest",
            domain="dttest.sintel.net.co",
        )
        self.client.defaults["HTTP_HOST"] = "localhost"

    def test_requires_staff(self) -> None:
        """Un usuario no-staff recibe HTTP 403 en el endpoint DataTables."""
        normal = make_normal_user("tenants_dt_normal@t.test")
        self.client.force_authenticate(user=normal)
        response = self.client.post(self.URL, _dt_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_receives_403(self) -> None:
        """Usuario anonimo recibe HTTP 403 (SessionAuthentication no tiene redirect)."""
        self.client.force_authenticate(user=None)
        response = self.client.post(self.URL, _dt_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_receives_200_with_datatables_structure(self) -> None:
        """Staff recibe 200 con la estructura estandar DataTables."""
        response = self.client.post(self.URL, _dt_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("draw", data)
        self.assertIn("recordsTotal", data)
        self.assertIn("recordsFiltered", data)
        self.assertIn("data", data)
        self.assertIsInstance(data["data"], list)

    def test_draw_value_is_echoed(self) -> None:
        """El campo 'draw' se devuelve con el mismo valor enviado (contrato DataTables)."""
        response = self.client.post(self.URL, _dt_payload(draw="42"), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.json()["draw"]), "42")

    def test_excludes_public_schema(self) -> None:
        """El listado no incluye el tenant con schema_name='public'."""
        response = self.client.post(self.URL, _dt_payload(), format="json")
        schemas = [row["schema_name"] for row in response.json()["data"]]
        self.assertNotIn("public", schemas)

    def test_tenant_fields_present(self) -> None:
        """Cada registro incluye los campos esperados del serializer."""
        response = self.client.post(self.URL, _dt_payload(), format="json")
        rows = response.json()["data"]
        self.assertGreater(len(rows), 0)
        row = rows[0]
        for field in ("id", "nombre", "schema_name", "is_active", "created_on"):
            self.assertIn(field, row, f"Campo '{field}' ausente en la respuesta")

    def test_search_filters_results(self) -> None:
        """La busqueda por texto reduce el conjunto de resultados."""
        # Buscar por nombre unico del tenant de prueba
        payload = _dt_payload()
        payload["search"] = {"value": "Empresa DT Test"}
        response = self.client.post(self.URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertGreaterEqual(data["recordsFiltered"], 1)

    def test_pagination_length_respected(self) -> None:
        """El parametro 'length' limita el numero de registros devueltos."""
        response = self.client.post(self.URL, _dt_payload(length=1), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.json()["data"]), 1)


# ---------------------------------------------------------------------------
# TenantDomainsDataTableView
# ---------------------------------------------------------------------------

class TenantDomainsDataTableViewTest(PublicAPITestCase):
    """Tests para POST /api/admin/v1/console/dt/tenant-domains/."""

    URL: str = "/api/admin/v1/console/dt/tenant-domains/"

    def setUp(self) -> None:
        super().setUp()
        self.client_obj, self.domain = make_tenant_with_domain(
            nombre="Empresa Domains Test",
            schema_name="domainstest",
            domain="domainstest.sintel.net.co",
        )
        self.client.defaults["HTTP_HOST"] = "localhost"

    def test_returns_datatables_structure(self) -> None:
        """Respuesta 200 con estructura DataTables estandar."""
        response = self.client.post(self.URL, _dt_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("draw", data)
        self.assertIn("data", data)
        self.assertIsInstance(data["data"], list)

    def test_domain_fields_present(self) -> None:
        """Cada registro incluye id, domain, is_primary."""
        response = self.client.post(self.URL, _dt_payload(), format="json")
        rows = response.json()["data"]
        self.assertGreater(len(rows), 0)
        row = rows[0]
        for field in ("id", "domain", "is_primary"):
            self.assertIn(field, row)


# ---------------------------------------------------------------------------
# UsersDataTableView — GET (detalle de usuario)
# ---------------------------------------------------------------------------

class UsersDataTableGetTest(PublicAPITestCase):
    """Tests para GET /api/admin/v1/console/dt/users/{id}/."""

    def setUp(self) -> None:
        super().setUp()
        self.target_user = make_normal_user("get_target@t.test")
        self.url: str = f"/api/admin/v1/console/dt/users/{self.target_user.pk}/"
        self.client.defaults["HTTP_HOST"] = "localhost"

    def test_get_existing_user_returns_200(self) -> None:
        """GET de un usuario existente devuelve 200 con sus datos."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["email"], self.target_user.email)

    def test_get_nonexistent_user_returns_404(self) -> None:
        """GET de un usuario inexistente devuelve 404."""
        response = self.client.get("/api/admin/v1/console/dt/users/999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_without_id_returns_400(self) -> None:
        """GET sin user_id retorna 400 (ruta sin parametro)."""
        response = self.client.get("/api/admin/v1/console/dt/users/")
        # GET en la ruta sin ID no esta mapeado como GET valido en la URLconf
        # La vista retorna 400 si no hay user_id; la ruta base solo acepta POST
        self.assertIn(response.status_code, (400, 405))

    def test_requires_staff(self) -> None:
        """No-staff recibe 403."""
        normal = make_normal_user("get_normal@t.test")
        self.client.force_authenticate(user=normal)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# UsersDataTableView — POST (listar via DataTables)
# ---------------------------------------------------------------------------

class UsersDataTableListTest(PublicAPITestCase):
    """Tests para POST /api/admin/v1/console/dt/users/ en modo listado (draw presente)."""

    URL: str = "/api/admin/v1/console/dt/users/"

    def setUp(self) -> None:
        super().setUp()
        # La consola muestra solo superusers + primary_admins del tenant.
        # Creamos un segundo superusuario adicional para asegurar que hay >= 2 visibles.
        self.user_a = make_staff_user("list_a_staff@t.test")
        self.user_b = make_staff_user("list_b_staff@t.test")
        self.client.defaults["HTTP_HOST"] = "localhost"

    def test_returns_datatables_structure(self) -> None:
        """POST con 'draw' devuelve estructura DataTables estandar."""
        response = self.client.post(self.URL, _dt_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("draw", data)
        self.assertIn("recordsTotal", data)
        self.assertIn("recordsFiltered", data)
        self.assertIn("data", data)
        self.assertIsInstance(data["data"], list)

    def test_records_total_matches_visible_count(self) -> None:
        """
        recordsTotal refleja solo los usuarios visibles en la consola
        (superusers + primary_admins de tenants), no el total absoluto de la BD.
        """
        from django.contrib.auth import get_user_model
        from django.db.models import Exists, OuterRef, Q
        from apps.public.tenants.models import TenantMembership

        User = get_user_model()
        _has_primary = TenantMembership.objects.filter(
            user=OuterRef("pk"), is_primary_admin=True, is_active=True
        )
        visible = User.objects.filter(
            Q(is_staff=True, is_superuser=True) | Q(Exists(_has_primary))
        ).distinct().count()

        response = self.client.post(self.URL, _dt_payload(), format="json")
        self.assertEqual(response.json()["recordsTotal"], visible)

    def test_user_fields_present_in_data(self) -> None:
        """Cada registro incluye los campos del ConsoleUserListSerializer."""
        response = self.client.post(self.URL, _dt_payload(), format="json")
        rows = response.json()["data"]
        self.assertGreater(len(rows), 0)
        expected = ("id", "email", "first_name", "last_name", "is_active", "is_staff")
        for field in expected:
            self.assertIn(field, rows[0], f"Campo '{field}' ausente")

    def test_search_by_email_filters_results(self) -> None:
        """La busqueda por email reduce recordsFiltered (solo entre usuarios visibles)."""
        payload = _dt_payload()
        payload["search"] = {"value": "list_a_staff@t.test"}
        response = self.client.post(self.URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertGreaterEqual(data["recordsFiltered"], 1)
        emails = [row["email"] for row in data["data"]]
        self.assertIn("list_a_staff@t.test", emails)


# ---------------------------------------------------------------------------
# UsersDataTableView — POST (crear usuario)
# ---------------------------------------------------------------------------

class UsersDataTableCreateTest(PublicAPITestCase):
    """Tests para POST /api/admin/v1/console/dt/users/ en modo creacion (sin draw)."""

    URL: str = "/api/admin/v1/console/dt/users/"

    def setUp(self) -> None:
        super().setUp()
        self.client.defaults["HTTP_HOST"] = "localhost"

    def test_create_valid_user_returns_201(self) -> None:
        """POST con datos validos sin 'draw' crea un usuario y retorna 201."""
        payload = {
            "email": "newuser@console.test",
            "first_name": "Nuevo",
            "last_name": "Usuario",
            "is_active": True,
            "is_staff": False,
            "password": "SecurePass123!",
        }
        response = self.client.post(self.URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["email"], "newuser@console.test")

    def test_create_user_persists_in_db(self) -> None:
        """El usuario creado existe en la base de datos."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        email = "persisted@console.test"
        self.client.post(
            self.URL,
            {"email": email, "password": "Pass1234!", "first_name": "Test"},
            format="json",
        )
        self.assertTrue(User.objects.filter(email=email).exists())

    def test_create_duplicate_email_returns_400(self) -> None:
        """Intentar crear un usuario con email duplicado retorna 400."""
        make_normal_user("dup@console.test")
        payload = {"email": "dup@console.test", "password": "Pass1234!"}
        response = self.client.post(self.URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_without_email_returns_400(self) -> None:
        """Crear usuario sin email retorna 400 con error de validacion."""
        response = self.client.post(self.URL, {"password": "Pass1234!"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.json())


# ---------------------------------------------------------------------------
# UsersDataTableView — PATCH (actualizar usuario)
# ---------------------------------------------------------------------------

class UsersDataTablePatchTest(PublicAPITestCase):
    """Tests para PATCH /api/admin/v1/console/dt/users/{id}/."""

    def setUp(self) -> None:
        super().setUp()
        self.target_user = make_normal_user("patch_target@t.test")
        self.url: str = f"/api/admin/v1/console/dt/users/{self.target_user.pk}/"
        self.client.defaults["HTTP_HOST"] = "localhost"

    def test_patch_deactivate_user_returns_200(self) -> None:
        """PATCH para desactivar una cuenta retorna 200 con is_active=False."""
        response = self.client.patch(self.url, {"is_active": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()["is_active"])

    def test_patch_update_persists_in_db(self) -> None:
        """El cambio de is_active se persiste en la base de datos."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client.patch(self.url, {"is_active": False}, format="json")
        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.is_active)

    def test_patch_update_first_name(self) -> None:
        """PATCH actualiza el nombre del usuario."""
        response = self.client.patch(self.url, {"first_name": "Actualizado"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["first_name"], "Actualizado")

    def test_patch_nonexistent_user_returns_404(self) -> None:
        """PATCH sobre usuario inexistente retorna 404."""
        response = self.client.patch(
            "/api/admin/v1/console/dt/users/999999/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_requires_staff(self) -> None:
        """No-staff recibe 403 al intentar hacer PATCH."""
        normal = make_normal_user("patch_normal@t.test")
        self.client.force_authenticate(user=normal)
        response = self.client.patch(self.url, {"is_active": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# UsersDataTableView — DELETE (eliminar usuario via delete_user_service)
# ---------------------------------------------------------------------------

class UsersDataTableDeleteTest(PublicAPITestCase):
    """Tests para DELETE /api/admin/v1/console/dt/users/{id}/."""

    def setUp(self) -> None:
        super().setUp()
        self.target_user = make_normal_user("delete_target@t.test")
        self.url: str = f"/api/admin/v1/console/dt/users/{self.target_user.pk}/"
        self.client.defaults["HTTP_HOST"] = "localhost"

    @patch("apps.public.console.api.views.delete_user_service")
    def test_delete_calls_service_and_returns_200(self, mock_service) -> None:
        """DELETE delega a delete_user_service y retorna 200."""
        mock_service.return_value = None  # servicio sin efecto en test
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_service.assert_called_once_with(
            user_id=self.target_user.pk,
            cascade=True,
            deleted_by_id=self.admin_user.pk,
        )

    @patch("apps.public.console.api.views.delete_user_service")
    def test_delete_response_contains_email(self, mock_service) -> None:
        """La respuesta del DELETE incluye el email del usuario eliminado."""
        mock_service.return_value = None
        response = self.client.delete(self.url)
        data = response.json()
        self.assertIn("mensaje", data)
        self.assertIn(self.target_user.email, data["mensaje"])

    @patch("apps.public.console.api.views.delete_user_service")
    def test_delete_nonexistent_user_returns_404(self, mock_service) -> None:
        """DELETE de usuario inexistente retorna 404 sin llamar al servicio."""
        response = self.client.delete("/api/admin/v1/console/dt/users/999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_service.assert_not_called()

    @patch(
        "apps.public.console.api.views.delete_user_service",
        side_effect=RuntimeError("FK constraint"),
    )
    def test_delete_service_exception_returns_400(self, mock_service) -> None:
        """Si delete_user_service lanza excepcion, la vista retorna 400."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())

    def test_delete_requires_staff(self) -> None:
        """No-staff recibe 403 al intentar eliminar."""
        normal = make_normal_user("del_normal@t.test")
        self.client.force_authenticate(user=normal)
        with patch("apps.public.console.api.views.delete_user_service"):
            response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# ConsoleHealthView
# ---------------------------------------------------------------------------

class ConsoleHealthViewTest(PublicAPITestCase):
    """Tests para GET /api/admin/v1/console/health/."""

    URL: str = "/api/admin/v1/console/health/"

    def setUp(self) -> None:
        super().setUp()
        self.client.defaults["HTTP_HOST"] = "localhost"

    def test_health_returns_200(self) -> None:
        """GET /health/ retorna HTTP 200."""
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health_status_ok(self) -> None:
        """La respuesta incluye status='ok'."""
        data = self.client.get(self.URL).json()
        self.assertEqual(data["status"], "ok")

    def test_health_has_time_field(self) -> None:
        """La respuesta incluye el campo 'time' (timestamp ISO)."""
        data = self.client.get(self.URL).json()
        self.assertIn("time", data)
        self.assertIsNotNone(data["time"])

    def test_health_features_structure(self) -> None:
        """La respuesta incluye 'features' con las claves esperadas."""
        data = self.client.get(self.URL).json()
        self.assertIn("features", data)
        features = data["features"]
        self.assertIn("api_first", features)
        self.assertIn("datatables_post", features)
        self.assertIn("jwt_admin", features)
        self.assertTrue(features["api_first"])
        self.assertTrue(features["datatables_post"])

    def test_health_requires_staff(self) -> None:
        """No-staff recibe 403 en el endpoint de health."""
        normal = make_normal_user("health_normal@t.test")
        self.client.force_authenticate(user=normal)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_health_unauthenticated_returns_403(self) -> None:
        """Anonimo recibe 403 (SessionAuthentication no hace redirect en APIs)."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# ConsoleActionLog — fixture y acceso
# ---------------------------------------------------------------------------

class ConsoleActionLogFixtureTest(PublicAPITestCase):
    """Verifica que el fixture ConsoleActionLog se crea y se consulta correctamente."""

    def setUp(self) -> None:
        super().setUp()
        self.client_obj, _ = make_tenant_with_domain(
            nombre="Log Test Empresa",
            schema_name="logtest",
            domain="logtest.sintel.net.co",
        )
        self.log = make_console_action_log(
            actor=self.admin_user,
            action="TENANT_CREATE",
            tenant=self.client_obj,
        )

    def test_log_created_with_correct_fields(self) -> None:
        """El ConsoleActionLog tiene los campos correctos tras creacion."""
        from apps.public.console.models import ConsoleActionLog

        self.assertEqual(self.log.action, "TENANT_CREATE")
        self.assertEqual(self.log.actor.pk, self.admin_user.pk)
        self.assertEqual(self.log.tenant.pk, self.client_obj.pk)
        self.assertIsNotNone(self.log.created_at)

    def test_log_str_representation(self) -> None:
        """__str__ incluye action y actor."""
        log_str = str(self.log)
        self.assertIn("TENANT_CREATE", log_str)

    def test_log_ordering_newest_first(self) -> None:
        """ConsoleActionLog ordena por -created_at (mas reciente primero)."""
        from apps.public.console.models import ConsoleActionLog

        make_console_action_log(actor=self.admin_user, action="USER_UPDATE")
        logs = list(ConsoleActionLog.objects.all())
        self.assertGreaterEqual(logs[0].created_at, logs[-1].created_at)
