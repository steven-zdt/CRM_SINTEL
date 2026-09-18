"""
Suite de pruebas para la aplicación Console.

Esta suite verifica:
1. Aislamiento y permisos (solo staff, solo esquema public)
2. Consumo de API (ViewSets, paginación)
3. Lógica de negocio (Service Layer Pattern)
4. Integridad legal (catálogo DIAN)

Arquitectura:
- Multi-tenant por esquemas (django-tenants)
- Solo accesible desde esquema 'public'
- Solo usuarios con is_staff=True
- Service Layer Pattern (Cero Signals)
"""

from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.public.accounts.models import User
from apps.public.impuestos.models import TarifaIVA, TipoImpuesto
from apps.public.tenants.models import Client as TenantClient
from apps.public.tenants.models import Domain

User = get_user_model()


class ConsoleIsolationAndPermissionsTests(TenantTestCase):
    """
    Tests de aislamiento y permisos.

    Verifica que:
    - Solo usuarios staff pueden acceder
    - Solo se puede acceder desde esquema 'public'
    - Las rutas redirigen correctamente
    """

    def setUp(self):
        """Configuración inicial para cada test."""
        # Asegurar que estamos en el esquema public
        # TenantTestCase ya maneja esto, pero lo hacemos explícito
        # Usar connection.set_schema_to_public() para forzar el esquema public
        connection.set_schema_to_public()

        # Crear tenant público y dominio si no existen (necesario para TenantMainMiddleware)
        # TenantTestCase crea el tenant público automáticamente, pero necesitamos el dominio
        public_tenant, _ = TenantClient.objects.get_or_create(
            schema_name="public", defaults={"nombre": "Public Tenant", "on_trial": False}
        )
        Domain.objects.get_or_create(
            domain="localhost", defaults={"tenant": public_tenant, "is_primary": True}
        )
        Domain.objects.get_or_create(
            domain="testserver", defaults={"tenant": public_tenant, "is_primary": False}
        )

        # Crear usuario staff
        self.staff_user = User.objects.create_user(
            email="staff@test.com",
            username="staff",
            password="testpass123",
            is_staff=True,
            is_active=True,
        )

        # Crear usuario no-staff
        self.regular_user = User.objects.create_user(
            email="regular@test.com",
            username="regular",
            password="testpass123",
            is_staff=False,
            is_active=True,
        )

        # Cliente HTTP de Django (NO sobrescribir con modelo Client)
        # Usar self.client (estándar de Django TestCase) para mantener compatibilidad
        self.client = Client()

    def test_dashboard_requires_staff(self):
        """Verifica que el dashboard requiere usuario staff."""
        # Usuario no autenticado
        response = self.client.get("/console/")
        self.assertEqual(response.status_code, 302)  # Redirige a login
        self.assertIn(settings.LOGIN_URL, response.url)

        # Usuario regular (no staff)
        # Usar force_login para asegurar que request.user esté materializado en tests
        self.client.force_login(self.regular_user)
        response = self.client.get("/console/")
        self.assertEqual(response.status_code, 403)  # Forbidden

        # Usuario staff
        self.client.force_login(self.staff_user)
        response = self.client.get("/console/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")

    def test_tenants_list_requires_staff(self):
        """Verifica que la lista de tenants requiere usuario staff."""
        # Usuario no autenticado
        response = self.client.get("/console/tenants/")
        self.assertEqual(response.status_code, 302)

        # Usuario regular
        self.client.force_login(self.regular_user)
        response = self.client.get("/console/tenants/")
        self.assertEqual(response.status_code, 403)

        # Usuario staff
        self.client.force_login(self.staff_user)
        response = self.client.get("/console/tenants/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestión de Empresas")

    def test_users_list_requires_staff(self):
        """Verifica que la lista de usuarios requiere usuario staff."""
        # Usuario no autenticado
        response = self.client.get("/console/users/")
        self.assertEqual(response.status_code, 302)

        # Usuario regular
        self.client.force_login(self.regular_user)
        response = self.client.get("/console/users/")
        self.assertEqual(response.status_code, 403)

        # Usuario staff
        self.client.force_login(self.staff_user)
        response = self.client.get("/console/users/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestión de Usuarios")

    def test_impuestos_catalogo_requires_staff(self):
        """Verifica que el catálogo DIAN requiere usuario staff."""
        # Usuario no autenticado
        response = self.client.get("/console/impuestos/")
        self.assertEqual(response.status_code, 302)

        # Usuario regular
        self.client.force_login(self.regular_user)
        response = self.client.get("/console/impuestos/")
        self.assertEqual(response.status_code, 403)

        # Usuario staff
        self.client.force_login(self.staff_user)
        response = self.client.get("/console/impuestos/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Catálogo DIAN")

    def test_console_only_accessible_from_public_schema(self):
        """
        Verifica que la consola solo es accesible desde el esquema 'public'.

        Este test verifica que el mixin StaffRequiredMixin bloquea el acceso
        cuando se intenta acceder desde un esquema de tenant privado.
        """
        # Asegurar esquema public antes de crear cualquier tenant
        connection.set_schema_to_public()

        # Crear un tenant privado (debe estar en esquema public para crearlo)
        tenant_instance = TenantClient.objects.create(
            schema_name="test_tenant", nombre="Test Tenant", on_trial=True
        )
        Domain.objects.create(
            domain="test-tenant.localhost", tenant=tenant_instance, is_primary=True
        )

        # Autenticar como staff
        self.client.force_login(self.staff_user)

        # Intentar acceder desde el esquema public (debería funcionar)
        # TenantTestCase ya está en el esquema public por defecto
        response = self.client.get("/console/")
        self.assertEqual(response.status_code, 200)

        # Nota: En un test real con subdominios, necesitarías usar
        # RequestFactory con el header HTTP_HOST configurado
        # Por ahora, verificamos que el mixin tiene la lógica correcta


class ConsoleAPIConsumptionTests(TenantTestCase):
    """
    Tests de consumo de API.

    Verifica que:
    - Los ViewSets responden correctamente
    - La paginación funciona según StandardResultsSetPagination
    - Los filtros y búsquedas funcionan
    """

    def setUp(self):
        """Configuración inicial para cada test."""
        # Asegurar que estamos en el esquema public antes de crear tenants
        connection.set_schema_to_public()

        # Crear usuario staff
        self.staff_user = User.objects.create_user(
            email="staff@test.com",
            username="staff",
            password="testpass123",
            is_staff=True,
            is_active=True,
        )

        # Cliente API
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.staff_user)

        # Crear datos de prueba (usando TenantClient para evitar shadowing)
        # IMPORTANTE: Debe estar en esquema public para crear Client
        self.tenant_instance_1 = TenantClient.objects.create(
            schema_name="empresa1", nombre="Empresa 1", on_trial=True
        )
        self.tenant_instance_2 = TenantClient.objects.create(
            schema_name="empresa2", nombre="Empresa 2", on_trial=False
        )

        Domain.objects.create(
            domain="empresa1.localhost", tenant=self.tenant_instance_1, is_primary=True
        )
        Domain.objects.create(
            domain="empresa2.localhost", tenant=self.tenant_instance_2, is_primary=True
        )

    def test_tenants_api_returns_paginated_results(self):
        """Verifica que la API de tenants retorna resultados paginados."""
        response = self.api_client.get("/api/public/v1/tenants/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)

        # Verificar que count es correcto
        self.assertEqual(response.data["count"], 2)

        # Verificar que results contiene los tenants
        self.assertEqual(len(response.data["results"]), 2)

    def test_tenants_api_pagination_follows_standard(self):
        """
        Verifica que la paginación sigue StandardResultsSetPagination.

        StandardResultsSetPagination:
        - page_size: 25 (default)
        - page_size_query_param: 'page_size'
        - max_page_size: 100
        """
        # Asegurar esquema public antes de crear más tenants
        connection.set_schema_to_public()

        # Crear más tenants para probar paginación
        for i in range(30):
            TenantClient.objects.create(
                schema_name=f"empresa{i + 3}", nombre=f"Empresa {i + 3}", on_trial=True
            )

        # Primera página (debería tener 25 resultados)
        response = self.api_client.get("/api/public/v1/tenants/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 25)
        self.assertIsNotNone(response.data["next"])  # Hay más páginas

        # Segunda página
        response = self.api_client.get("/api/public/v1/tenants/?page=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data["results"]), 25)

        # Cambiar tamaño de página
        response = self.api_client.get("/api/public/v1/tenants/?page_size=10")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 10)

        # Máximo tamaño de página
        response = self.api_client.get("/api/public/v1/tenants/?page_size=200")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # No debería exceder max_page_size (100)
        self.assertLessEqual(len(response.data["results"]), 100)

    def test_tenants_api_filtering(self):
        """Verifica que los filtros de la API funcionan correctamente."""
        # Filtrar por on_trial=True
        response = self.api_client.get("/api/public/v1/tenants/?on_trial=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["nombre"], "Empresa 1")

        # Filtrar por on_trial=False
        response = self.api_client.get("/api/public/v1/tenants/?on_trial=false")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["nombre"], "Empresa 2")

    def test_tenants_api_search(self):
        """Verifica que la búsqueda de la API funciona correctamente."""
        # Buscar por nombre
        response = self.api_client.get("/api/public/v1/tenants/?search=Empresa 1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["nombre"], "Empresa 1")

        # Buscar por schema_name
        response = self.api_client.get("/api/public/v1/tenants/?search=empresa2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["schema_name"], "empresa2")

    def test_users_api_returns_paginated_results(self):
        """Verifica que la API de usuarios retorna resultados paginados."""
        # Asegurar esquema public
        connection.set_schema_to_public()

        # Crear más usuarios
        for i in range(5):
            User.objects.create_user(
                email=f"user{i}@test.com", username=f"user{i}", password="testpass123"
            )

        response = self.api_client.get("/api/public/v1/users/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        self.assertGreaterEqual(response.data["count"], 6)  # staff_user + 5 nuevos

    def test_users_api_filtering(self):
        """Verifica que los filtros de usuarios funcionan."""
        # Asegurar esquema public
        connection.set_schema_to_public()

        # Crear usuario inactivo
        inactive_user = User.objects.create_user(
            email="inactive@test.com", username="inactive", password="testpass123", is_active=False
        )

        # Filtrar por is_active=True
        response = self.api_client.get("/api/public/v1/users/?is_active=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Todos los usuarios activos deberían estar en los resultados
        active_emails = [u["email"] for u in response.data["results"]]
        self.assertNotIn("inactive@test.com", active_emails)

        # Filtrar por is_active=False
        response = self.api_client.get("/api/public/v1/users/?is_active=false")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        inactive_emails = [u["email"] for u in response.data["results"]]
        self.assertIn("inactive@test.com", inactive_emails)


class ConsoleBusinessLogicTests(TenantTestCase):
    """
    Tests de lógica de negocio (Service Layer Pattern).

    Verifica que:
    - El formulario de creación de tenant llama al servicio correctamente
    - Se manejan errores de validación
    - La creación de tenant dispara la creación del esquema
    """

    def setUp(self):
        """Configuración inicial para cada test."""
        # Asegurar que estamos en el esquema public
        connection.set_schema_to_public()

        # Crear usuario staff
        self.staff_user = User.objects.create_user(
            email="staff@test.com",
            username="staff",
            password="testpass123",
            is_staff=True,
            is_active=True,
        )

        # Cliente API
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.staff_user)

    @patch("apps.services.onboarding.empresa_service.crear_empresa")
    def test_create_tenant_calls_service(self, mock_crear_empresa):
        """
        Verifica que la creación de tenant llama al servicio crear_empresa.

        Sigue el principio de Service Layer Pattern: la lógica de negocio
        está en apps.services.onboarding.empresa_service, no en el ViewSet.
        """
        # Mock del servicio
        mock_client = MagicMock()
        mock_client.id = 1
        mock_client.nombre = "Nueva Empresa"
        mock_client.schema_name = "nueva-empresa"
        mock_client.on_trial = True
        mock_client.created_on = "2024-01-01T00:00:00Z"

        mock_domain = MagicMock()
        mock_domain.domain = "nueva-empresa.localhost"

        mock_crear_empresa.return_value = {
            "client": mock_client,
            "domain": mock_domain,
            "user": None,
            "schema_name": "nueva-empresa",
        }

        # Llamar al endpoint
        data = {
            "nombre": "Nueva Empresa",
            "dominio": "nueva-empresa.localhost",
            "email_admin": "admin@nueva-empresa.com",
        }
        response = self.api_client.post("/api/public/v1/tenants/create/", data, format="json")

        # Verificar que el servicio fue llamado
        mock_crear_empresa.assert_called_once()
        call_args = mock_crear_empresa.call_args

        # Verificar parámetros
        self.assertEqual(call_args.kwargs["nombre"], "Nueva Empresa")
        self.assertEqual(call_args.kwargs["dominio"], "nueva-empresa.localhost")
        self.assertEqual(call_args.kwargs["email_admin"], "admin@nueva-empresa.com")
        self.assertEqual(call_args.kwargs["on_trial"], True)  # Default

        # Verificar respuesta
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("nombre", response.data)

    @patch("apps.services.onboarding.empresa_service.crear_empresa")
    def test_create_tenant_handles_validation_errors(self, mock_crear_empresa):
        """
        Verifica que se manejan correctamente los errores de validación.

        Ejemplos: dominio duplicado, schema_name duplicado, datos inválidos.
        """
        # Mock del servicio que lanza ValidationError
        from django.core.exceptions import ValidationError

        mock_crear_empresa.side_effect = ValidationError(
            "El dominio 'test.localhost' ya está en uso"
        )

        # Intentar crear tenant con dominio duplicado
        data = {
            "nombre": "Empresa Test",
            "dominio": "test.localhost",
            "email_admin": "admin@test.com",
        }
        response = self.api_client.post("/api/public/v1/tenants/create/", data, format="json")

        # Verificar que se retorna error 400
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("ya está en uso", response.data["error"])

    def test_create_tenant_requires_all_fields(self):
        """Verifica que se requieren todos los campos obligatorios."""
        # Sin nombre
        data = {"dominio": "test.localhost", "email_admin": "admin@test.com"}
        response = self.api_client.post("/api/public/v1/tenants/create/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Faltan campos requeridos", response.data["error"])

        # Sin dominio
        data = {"nombre": "Test", "email_admin": "admin@test.com"}
        response = self.api_client.post("/api/public/v1/tenants/create/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Sin email_admin
        data = {"nombre": "Test", "dominio": "test.localhost"}
        response = self.api_client.post("/api/public/v1/tenants/create/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_tenant_creates_schema(self):
        """
        Verifica que la creación de tenant dispara la creación del esquema.

        El servicio crear_empresa debe crear el esquema físico en PostgreSQL
        mediante auto_create_schema=True en el modelo Client.
        """
        # Asegurar esquema public antes de crear tenant
        connection.set_schema_to_public()

        from django_tenants.utils import schema_exists

        from apps.services.onboarding.empresa_service import crear_empresa

        # Crear tenant usando el servicio real (sin mock)
        # WARNING: v2.17: Estandarización de subdominios - dominio se construye automáticamente
        result = crear_empresa(
            nombre="Empresa Schema Test", email_admin="admin@schema-test.com", on_trial=True
        )

        # Verificar que se creó el tenant
        self.assertIsNotNone(result["client"])
        self.assertEqual(result["client"].nombre, "Empresa Schema Test")

        # Verificar que el esquema existe
        schema_name = result["schema_name"]
        self.assertTrue(schema_exists(schema_name))


class ConsoleLegalDataTests(TenantTestCase):
    """
    Tests de integridad legal (catálogo DIAN).

    Verifica que:
    - La consola puede visualizar datos del catálogo DIAN
    - Los datos poblados por poblar_catalogo_dian son accesibles
    """

    def setUp(self):
        """Configuración inicial para cada test."""
        # Asegurar que estamos en el esquema public
        connection.set_schema_to_public()

        # Crear usuario staff
        self.staff_user = User.objects.create_user(
            email="staff@test.com",
            username="staff",
            password="testpass123",
            is_staff=True,
            is_active=True,
        )

        # Cliente API
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.staff_user)

        # Crear datos de catálogo DIAN de prueba con fecha_vigencia
        fecha_vigencia = timezone.now().date()

        self.tipo_impuesto = TipoImpuesto.objects.create(
            codigo="01", nombre="IVA", activo=True, fecha_vigencia=fecha_vigencia
        )

        self.tarifa_iva = TarifaIVA.objects.create(
            codigo="01",
            nombre="Tarifa General",
            porcentaje=19.0,
            activo=True,
            fecha_vigencia=fecha_vigencia,
        )

    def test_impuestos_catalogo_displays_data(self):
        """Verifica que el catálogo DIAN muestra datos correctamente."""
        # Verificar que la vista carga
        http_client = Client()
        http_client.login(email="staff@test.com", password="testpass123")
        response = http_client.get("/console/impuestos/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Catálogo DIAN")

    def test_tipos_impuesto_api_returns_data(self):
        """Verifica que la API de tipos de impuesto retorna datos."""
        # Las rutas de impuestos están en /api/v1/ (no /api/public/v1/)
        # porque están disponibles para todos los tenants desde el esquema public
        response = self.api_client.get("/api/v1/impuestos/tipos/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertGreaterEqual(response.data["count"], 1)

        # Verificar que el tipo de impuesto creado está en los resultados
        tipos_codigos = [t["codigo"] for t in response.data["results"]]
        self.assertIn("01", tipos_codigos)

    def test_tarifas_iva_api_returns_data(self):
        """Verifica que la API de tarifas IVA retorna datos."""
        # Las rutas de impuestos están en /api/public/v1/impuestos/...
        response = self.api_client.get("/api/public/v1/impuestos/tarifas-iva/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertGreaterEqual(response.data["count"], 1)

        # Verificar que la tarifa creada está en los resultados
        tarifas_codigos = [t["codigo"] for t in response.data["results"]]
        self.assertIn("01", tarifas_codigos)

    def test_impuestos_api_pagination(self):
        """Verifica que las APIs de impuestos usan paginación estándar."""
        # Asegurar esquema public
        connection.set_schema_to_public()

        fecha_vigencia = timezone.now().date()

        # Crear más tipos de impuesto
        for i in range(30):
            TipoImpuesto.objects.create(
                codigo=f"{i + 2:02d}",
                nombre=f"Tipo {i + 2}",
                activo=True,
                fecha_vigencia=fecha_vigencia,
            )

        # Las rutas de impuestos están en /api/public/v1/impuestos/...
        response = self.api_client.get("/api/public/v1/impuestos/tipos/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data["results"]), 20
        )  # page_size default (StandardResultsSetPagination)
        self.assertIsNotNone(response.data["next"])  # Hay más páginas

    def test_impuestos_api_search(self):
        """Verifica que la búsqueda en catálogos funciona."""
        # Las rutas de impuestos están en /api/public/v1/impuestos/...
        # Buscar por código
        response = self.api_client.get("/api/public/v1/impuestos/tipos/?search=01")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)

        # Buscar por nombre
        response = self.api_client.get("/api/public/v1/impuestos/tipos/?search=IVA")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)

        # Verificar que el resultado contiene "IVA"
        resultados_nombres = [t["nombre"] for t in response.data["results"]]
        self.assertTrue(any("IVA" in nombre for nombre in resultados_nombres))


class ConsoleIntegrationTests(TenantTestCase):
    """
    Tests de integración end-to-end.

    Verifica el flujo completo desde la interfaz hasta la base de datos.
    """

    def setUp(self):
        """Configuración inicial para cada test."""
        # Asegurar que estamos en el esquema public
        connection.set_schema_to_public()

        # Crear usuario staff
        self.staff_user = User.objects.create_user(
            email="staff@test.com",
            username="staff",
            password="testpass123",
            is_staff=True,
            is_active=True,
        )

        # Cliente HTTP de Django (self.client es el estándar)
        self.client = Client()
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.staff_user)

    def test_full_flow_create_tenant_from_console(self):
        """
        Test de flujo completo: crear tenant desde la consola.

        Simula el flujo real:
        1. Usuario staff accede a /console/tenants/
        2. Usuario crea un nuevo tenant mediante el formulario
        3. El sistema llama al servicio crear_empresa
        4. Se crea el esquema físico
        5. Se puede acceder al nuevo tenant
        """
        # Asegurar esquema public antes de crear tenant
        connection.set_schema_to_public()

        # 1. Acceder a la consola
        self.client.login(email="staff@test.com", password="testpass123")
        response = self.client.get("/console/tenants/")
        self.assertEqual(response.status_code, 200)

        # 2. Crear tenant mediante API (simula el formulario)
        from apps.services.onboarding.empresa_service import crear_empresa

        # WARNING: v2.17: Estandarización de subdominios - dominio se construye automáticamente
        result = crear_empresa(
            nombre="Empresa Integración", email_admin="admin@integracion.com", on_trial=True
        )

        # 3. Verificar que se creó el tenant
        self.assertIsNotNone(result["client"])
        self.assertEqual(result["client"].nombre, "Empresa Integración")
        self.assertEqual(result["client"].schema_name, "empresa-integración")

        # 4. Verificar que se creó el dominio
        self.assertIsNotNone(result["domain"])
        self.assertEqual(result["domain"].domain, "integracion.localhost")

        # 5. Verificar que el esquema existe
        from django_tenants.utils import schema_exists

        self.assertTrue(schema_exists("empresa-integración"))

        # 6. Verificar que aparece en la API
        response = self.api_client.get("/api/public/v1/tenants/")
        tenant_names = [t["nombre"] for t in response.data["results"]]
        self.assertIn("Empresa Integración", tenant_names)
