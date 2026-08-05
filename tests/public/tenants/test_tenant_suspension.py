"""
Suite de Tests Funcionales - Suspensión de Tenants (QA)

Valida la funcionalidad de bloqueo de tenants suspendidos:
- Modelo Client: Campo is_active (default=True)
- Middleware TenantSecurityMiddleware: Bloquea acceso (403) si is_active=False
- API: Endpoint toggle_status para activar/desactivar
- Seguridad: Tenant público nunca debe bloquearse
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, RequestFactory
from django.urls import reverse

# Imports dentro de funciones para evitar problemas de configuración de Django
# Los modelos y factories se importan dentro de las funciones que los usan


@pytest.mark.django_db
class TestTenantSuspensionRegression:
    """
    Test de Regresión: Verificar que el estado por defecto funciona correctamente.

    Escenario: Crear un nuevo tenant y verificar que:
    - is_active es True por defecto
    - El tenant responde con 200 OK (acceso permitido)
    """

    def test_new_tenant_is_active_by_default(self):
        """Test: Verificar que is_active es True por defecto al crear un tenant."""
        from apps.public.tenants.models import Client as TenantClient

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear tenant
        tenant = TenantClient.objects.create(
            nombre="Empresa Activa", schema_name="empresa_activa"
        )

        # Verificar que is_active es True por defecto
        assert tenant.is_active is True, "is_active debe ser True por defecto"

        # Recargar desde BD para asegurar persistencia
        tenant.refresh_from_db()
        assert tenant.is_active is True, "is_active debe persistir como True"

    def test_active_tenant_allows_access(self):
        """Test: Verificar que un tenant activo permite acceso (200 OK)."""
        from tests.public.tenants.factories import ClientFactory, DomainFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear tenant con dominio
        tenant = ClientFactory(nombre="Empresa Activa", schema_name="empresa_activa")
        domain = DomainFactory(
            tenant=tenant, domain="empresa-activa.localhost", is_primary=True
        )

        # Verificar que is_active es True
        assert tenant.is_active is True

        # Simular request al tenant usando Client de Django
        # Nota: django-tenants resuelve el tenant basado en el hostname
        client = Client()

        # Hacer request a cualquier URL del tenant
        # Usamos el dominio del tenant en el hostname
        response = client.get("/", HTTP_HOST=domain.domain)

        # El tenant activo debe permitir acceso (no debe retornar 403)
        # Nota: Puede retornar 200, 302, 404, etc., pero NO 403
        assert (
            response.status_code != 403
        ), f"Tenant activo no debe retornar 403. Status: {response.status_code}"


@pytest.mark.django_db
class TestTenantSuspensionBlocking:
    """
    Test de Bloqueo: Verificar que el middleware bloquea acceso a tenants suspendidos.

    Escenario: Suspender un tenant y verificar que:
    - El middleware retorna 403 Forbidden
    - El mensaje contiene "Servicio Suspendido"
    """

    def test_suspended_tenant_blocks_access(self):
        """Test: Verificar que un tenant suspendido bloquea acceso (403)."""
        from tests.public.tenants.factories import ClientFactory, DomainFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear tenant con dominio
        tenant = ClientFactory(
            nombre="Empresa Suspendida", schema_name="empresa_suspendida"
        )
        domain = DomainFactory(
            tenant=tenant, domain="empresa-suspendida.localhost", is_primary=True
        )

        # Suspender el tenant
        tenant.is_active = False
        tenant.save()

        # Verificar que está suspendido
        tenant.refresh_from_db()
        assert tenant.is_active is False

        # Simular request al tenant suspendido
        client = Client()
        response = client.get("/", HTTP_HOST=domain.domain)

        # Debe retornar 403 Forbidden
        assert (
            response.status_code == 403
        ), f"Tenant suspendido debe retornar 403. Status: {response.status_code}"

        # El contenido debe contener el mensaje de suspensión
        assert "Servicio Suspendido" in response.content.decode(
            "utf-8"
        ) or "Service Suspended" in response.content.decode(
            "utf-8"
        ), "La respuesta debe contener el mensaje de suspensión"

    def test_middleware_directly_blocks_suspended_tenant(self):
        """Test: Verificar que el middleware bloquea directamente un tenant suspendido."""
        from apps.public.tenants.middleware import TenantSecurityMiddleware
        from tests.public.tenants.factories import ClientFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear tenant suspendido
        tenant = ClientFactory(
            nombre="Test Suspendido", schema_name="test_suspendido", is_active=False
        )

        # Crear mock request factory
        factory = RequestFactory()
        request = factory.get("/")

        # Simular que TenantMainMiddleware ya inyectó el tenant
        request.tenant = tenant

        # Crear middleware
        def mock_get_response(req):
            from django.http import HttpResponse

            return HttpResponse("OK")

        middleware = TenantSecurityMiddleware(mock_get_response)

        # Procesar request
        response = middleware(request)

        # Debe retornar 403
        assert (
            response.status_code == 403
        ), f"Middleware debe retornar 403 para tenant suspendido. Status: {response.status_code}"

        # Verificar contenido
        content = response.content.decode("utf-8")
        assert (
            "Servicio Suspendido" in content or "Service Suspended" in content
        ), "El middleware debe retornar el mensaje de suspensión"


@pytest.mark.django_db
class TestPublicTenantSecurity:
    """
    Test de Seguridad Crítica: Verificar que el tenant público nunca se bloquea.

    Escenario: Incluso si forzamos is_active=False en BD, el middleware debe
    permitir acceso al tenant público.
    """

    def test_public_tenant_never_blocks_access(self):
        """Test: Verificar que el tenant público siempre permite acceso."""
        from apps.public.tenants.models import Client as TenantClient

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Obtener o crear tenant público
        public_tenant = TenantClient.objects.filter(schema_name="public").first()
        if not public_tenant:
            public_tenant = TenantClient.objects.create(
                nombre="SINTEL Global", schema_name="public"
            )

        # Verificar que existe
        assert public_tenant.schema_name == "public"

        # Simular request al tenant público
        client = Client()
        response = client.get("/", HTTP_HOST="localhost")

        # Debe permitir acceso (no debe retornar 403)
        assert (
            response.status_code != 403
        ), f"Tenant público nunca debe retornar 403. Status: {response.status_code}"

    def test_public_tenant_middleware_ignores_is_active_false(self):
        """Test Edge Case: Middleware ignora is_active=False para tenant público."""
        from apps.public.tenants.middleware import TenantSecurityMiddleware
        from apps.public.tenants.models import Client as TenantClient

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Obtener tenant público
        public_tenant = TenantClient.objects.filter(schema_name="public").first()
        if not public_tenant:
            public_tenant = TenantClient.objects.create(
                nombre="SINTEL Global", schema_name="public"
            )

        # FORZAR is_active=False en BD (algo que la API no debería permitir)
        public_tenant.is_active = False
        public_tenant.save()

        # Verificar que está False en BD
        public_tenant.refresh_from_db()
        assert public_tenant.is_active is False

        # Crear mock request factory
        factory = RequestFactory()
        request = factory.get("/")

        # Simular que TenantMainMiddleware ya inyectó el tenant público
        request.tenant = public_tenant

        # Crear middleware
        def mock_get_response(req):
            from django.http import HttpResponse

            return HttpResponse("OK")

        middleware = TenantSecurityMiddleware(mock_get_response)

        # Procesar request
        response = middleware(request)

        # Debe permitir acceso (NO debe retornar 403)
        assert (
            response.status_code != 403
        ), f"Tenant público debe permitir acceso incluso con is_active=False. Status: {response.status_code}"

        # Debe retornar la respuesta normal (200 OK del mock)
        assert (
            response.status_code == 200
        ), "El middleware debe permitir el paso para tenant público"


@pytest.mark.django_db
class TestToggleStatusAPI:
    """
    Test de API: Verificar que el endpoint toggle_status funciona correctamente.

    Escenario: Usar un usuario admin autenticado y:
    - Llamar al endpoint POST /api/admin/v1/tenants/{id}/toggle-status/
    - Verificar que el estado cambia de True a False y viceversa
    - Verificar que no se puede hacer toggle al tenant público
    """

    def test_toggle_status_activates_tenant(self, admin_user):
        """Test: Activar un tenant suspendido."""
        from rest_framework import status
        from rest_framework.test import APIClient

        from tests.public.tenants.factories import ClientFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear tenant suspendido
        tenant = ClientFactory(
            nombre="Empresa Suspendida",
            schema_name="empresa_suspendida",
            is_active=False,
        )

        # Verificar estado inicial
        assert tenant.is_active is False

        # Crear APIClient autenticado
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        # Llamar al endpoint toggle_status
        url = reverse("admin-tenants-toggle-status", kwargs={"pk": tenant.id})
        response = api_client.post(url)

        # Debe retornar 200 OK
        assert (
            response.status_code == status.HTTP_200_OK
        ), f"toggle_status debe retornar 200. Status: {response.status_code}, Data: {response.data}"

        # Verificar respuesta
        data = response.data
        assert data["is_active"] is True, "El tenant debe estar activado"
        assert "message" in data, "Debe incluir mensaje descriptivo"
        assert (
            "activado" in data["message"].lower()
            or "activated" in data["message"].lower()
        )

        # Verificar en BD
        tenant.refresh_from_db()
        assert tenant.is_active is True, "El estado debe persistir en BD"

    def test_toggle_status_suspends_tenant(self, admin_user):
        """Test: Suspender un tenant activo."""
        from rest_framework import status
        from rest_framework.test import APIClient

        from tests.public.tenants.factories import ClientFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear tenant activo
        tenant = ClientFactory(
            nombre="Empresa Activa", schema_name="empresa_activa", is_active=True
        )

        # Verificar estado inicial
        assert tenant.is_active is True

        # Crear APIClient autenticado
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        # Llamar al endpoint toggle_status
        url = reverse("admin-tenants-toggle-status", kwargs={"pk": tenant.id})
        response = api_client.post(url)

        # Debe retornar 200 OK
        assert (
            response.status_code == status.HTTP_200_OK
        ), f"toggle_status debe retornar 200. Status: {response.status_code}, Data: {response.data}"

        # Verificar respuesta
        data = response.data
        assert data["is_active"] is False, "El tenant debe estar suspendido"
        assert "message" in data, "Debe incluir mensaje descriptivo"
        assert (
            "suspendido" in data["message"].lower()
            or "suspended" in data["message"].lower()
        )

        # Verificar en BD
        tenant.refresh_from_db()
        assert tenant.is_active is False, "El estado debe persistir en BD"

    def test_toggle_status_prevents_public_tenant_deactivation(self, admin_user):
        """Test: No se puede desactivar el tenant público."""
        from rest_framework import status
        from rest_framework.test import APIClient

        from apps.public.tenants.models import Client as TenantClient

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Obtener o crear tenant público
        public_tenant = TenantClient.objects.filter(schema_name="public").first()
        if not public_tenant:
            public_tenant = TenantClient.objects.create(
                nombre="SINTEL Global", schema_name="public"
            )

        # Asegurar que está activo
        public_tenant.is_active = True
        public_tenant.save()

        # Crear APIClient autenticado
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        # Intentar desactivar el tenant público
        url = reverse("admin-tenants-toggle-status", kwargs={"pk": public_tenant.id})
        response = api_client.post(url)

        # Debe retornar error (400 Bad Request o ValidationError)
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ), f"toggle_status debe rechazar desactivar tenant público. Status: {response.status_code}, Data: {response.data}"

        # Verificar mensaje de error
        error_data = response.data
        error_message = str(error_data.get("error", error_data.get("detail", "")))
        assert (
            "público" in error_message.lower() or "public" in error_message.lower()
        ), f"El error debe mencionar que no se puede desactivar el tenant público. Error: {error_message}"

        # Verificar que el estado NO cambió en BD
        public_tenant.refresh_from_db()
        assert (
            public_tenant.is_active is True
        ), "El tenant público debe seguir activo después del intento de desactivación"

    def test_toggle_status_toggles_multiple_times(self, admin_user):
        """Test: Verificar que toggle funciona múltiples veces (True -> False -> True)."""
        from rest_framework import status
        from rest_framework.test import APIClient

        from tests.public.tenants.factories import ClientFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear tenant activo
        tenant = ClientFactory(
            nombre="Empresa Test", schema_name="empresa_test", is_active=True
        )

        # Crear APIClient autenticado
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        url = reverse("admin-tenants-toggle-status", kwargs={"pk": tenant.id})

        # Primer toggle: True -> False
        response1 = api_client.post(url)
        assert response1.status_code == status.HTTP_200_OK
        assert response1.data["is_active"] is False

        tenant.refresh_from_db()
        assert tenant.is_active is False

        # Segundo toggle: False -> True
        response2 = api_client.post(url)
        assert response2.status_code == status.HTTP_200_OK
        assert response2.data["is_active"] is True

        tenant.refresh_from_db()
        assert tenant.is_active is True

        # Tercer toggle: True -> False
        response3 = api_client.post(url)
        assert response3.status_code == status.HTTP_200_OK
        assert response3.data["is_active"] is False

        tenant.refresh_from_db()
        assert tenant.is_active is False


@pytest.mark.django_db
class TestTenantSuspensionIntegration:
    """
    Test de Integración: Verificar el flujo completo de suspensión.

    Escenario End-to-End:
    1. Crear tenant activo
    2. Verificar acceso permitido
    3. Suspender via API
    4. Verificar acceso bloqueado
    5. Reactivar via API
    6. Verificar acceso permitido nuevamente
    """

    def test_full_suspension_reactivation_flow(self, admin_user):
        """Test: Flujo completo de suspensión y reactivación."""
        from rest_framework import status
        from rest_framework.test import APIClient

        from tests.public.tenants.factories import ClientFactory, DomainFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # 1. Crear tenant activo con dominio
        tenant = ClientFactory(
            nombre="Empresa Integración",
            schema_name="empresa_integracion",
            is_active=True,
        )
        domain = DomainFactory(
            tenant=tenant, domain="empresa-integracion.localhost", is_primary=True
        )

        # 2. Verificar acceso permitido (no debe retornar 403)
        client = Client()
        response1 = client.get("/", HTTP_HOST=domain.domain)
        assert response1.status_code != 403, "Tenant activo debe permitir acceso"

        # 3. Suspender via API
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)
        url = reverse("admin-tenants-toggle-status", kwargs={"pk": tenant.id})
        response2 = api_client.post(url)
        assert response2.status_code == status.HTTP_200_OK
        assert response2.data["is_active"] is False

        # 4. Verificar acceso bloqueado (debe retornar 403)
        response3 = client.get("/", HTTP_HOST=domain.domain)
        assert response3.status_code == 403, "Tenant suspendido debe bloquear acceso"
        assert "Servicio Suspendido" in response3.content.decode(
            "utf-8"
        ) or "Service Suspended" in response3.content.decode("utf-8")

        # 5. Reactivar via API
        response4 = api_client.post(url)
        assert response4.status_code == status.HTTP_200_OK
        assert response4.data["is_active"] is True

        # 6. Verificar acceso permitido nuevamente
        response5 = client.get("/", HTTP_HOST=domain.domain)
        assert response5.status_code != 403, "Tenant reactivado debe permitir acceso"
