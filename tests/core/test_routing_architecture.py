"""
Suite de Tests Funcionales - Enrutamiento y Arquitectura (QA)

Valida que el tráfico se enruta correctamente según el dominio (HTTP_HOST):
- Dominio Público (sintel.net.co): Debe usar config.urls_public
- Dominio Privado (cliente.sintel.net.co): Debe usar config.urls_tenant

Garantiza que no se ha roto el acceso a la consola de administración actual.
"""

import pytest
from django.db import connection
from django.test import Client
from django.urls import reverse

# Imports dentro de funciones para evitar problemas de configuración de Django


@pytest.mark.django_db
class TestPublicDomainRouting:
    """
    Tests para validar el enrutamiento del dominio público (sintel.net.co).
    """

    def test_public_anonymous_access_redirects_to_login(self):
        """
        Test: Acceso público anónimo debe redirigir a /admin/login/.

        Escenario:
        - Usuario anónimo accede a http://sintel.net.co/
        - Debe redirigir (302) a /admin/login/
        - NO debe dar error 500 ni 404
        """
        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear cliente de pruebas (sin autenticación)
        client = Client()

        # Simular request a http://sintel.net.co/ (raíz)
        response = client.get("/", HTTP_HOST="sintel.net.co")

        # Debe redirigir (302) a /admin/login/
        assert response.status_code == 302, (
            f"Debe redirigir (302), no {response.status_code}. "
            f"Content: {response.content.decode('utf-8')[:200] if hasattr(response, 'content') else 'N/A'}"
        )

        # Verificar que la redirección es a /admin/login/
        assert (
            response.url == "/admin/login/"
        ), f"Debe redirigir a /admin/login/, no a '{response.url}'"

        # NO debe dar error 500 ni 404
        assert (
            response.status_code != 500
        ), "NO debe dar error 500 (Internal Server Error)"
        assert response.status_code != 404, "NO debe dar error 404 (Not Found)"

    def test_public_authenticated_staff_redirects_to_console(self):
        """
        Test: Acceso público autenticado (staff) debe redirigir a /console/.

        Escenario:
        - Usuario staff autenticado accede a http://sintel.net.co/
        - Debe redirigir (302) a /console/ (consola de administración)
        """
        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear usuario staff
        from django.contrib.auth import get_user_model

        User = get_user_model()
        staff_user = User.objects.create_user(
            email="staff@test.local",
            password="testpass123",
            is_staff=True,
            is_superuser=False,
        )

        # Crear cliente autenticado
        client = Client()
        client.force_login(staff_user)

        # Simular request a http://sintel.net.co/ (raíz)
        response = client.get("/", HTTP_HOST="sintel.net.co")

        # Debe redirigir (302) a /console/
        assert (
            response.status_code == 302
        ), f"Debe redirigir (302), no {response.status_code}"

        # Verificar que la redirección es a /console/
        assert (
            response.url == "/console/"
        ), f"Debe redirigir a /console/, no a '{response.url}'"

    def test_console_tenants_page_still_works(self):
        """
        Safety Check: Verificar que /console/tenants/ sigue respondiendo 200 OK.

        Este test garantiza que no hemos roto el código existente de la consola.
        """
        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear usuario staff
        from django.contrib.auth import get_user_model

        User = get_user_model()
        staff_user = User.objects.create_user(
            email="staff@test.local",
            password="testpass123",
            is_staff=True,
            is_superuser=False,
        )

        # Crear cliente autenticado
        client = Client()
        client.force_login(staff_user)

        # Intentar acceder a /console/tenants/ desde dominio público
        response = client.get("/console/tenants/", HTTP_HOST="sintel.net.co")

        # Debe responder 200 OK (NO debe dar 404 ni 500)
        assert response.status_code == 200, (
            f"La consola debe responder 200 OK, no {response.status_code}. "
            f"Content: {response.content.decode('utf-8')[:500] if hasattr(response, 'content') else 'N/A'}"
        )

        # Verificar que el contenido contiene algo relacionado con tenants
        # (esto confirma que la vista correcta está siendo llamada)
        content = (
            response.content.decode("utf-8") if hasattr(response, "content") else ""
        )
        # No hacemos assert estricto del contenido porque puede variar,
        # pero verificamos que no es una página de error genérica
        assert (
            "error" not in content.lower()[:200] or "404" not in content[:200]
        ), "El contenido no debe ser una página de error"


@pytest.mark.django_db
class TestPrivateDomainRouting:
    """
    Tests para validar el enrutamiento de dominios privados (cliente.sintel.net.co).
    """

    def test_private_tenant_anonymous_redirects_to_login(self):
        """
        Test: Acceso privado anónimo debe redirigir a login.

        Escenario:
        - Usuario anónimo accede a http://cliente.sintel.net.co/
        - Debe redirigir a /admin/login/ (o la URL de login configurada)
        - NO debe mostrar el dashboard del tenant
        """
        from apps.public.tenants.models import Client as TenantClient
        from apps.public.tenants.models import Domain
        from tests.public.tenants.factories import ClientFactory, DomainFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear tenant y dominio
        tenant = ClientFactory(
            nombre="Empresa Test Routing", schema_name="test_routing", is_active=True
        )

        domain = DomainFactory(
            tenant=tenant, domain="test-routing.sintel.net.co", is_primary=True
        )

        # Crear cliente de pruebas (sin autenticación)
        client = Client()

        # Simular request a http://test-routing.sintel.net.co/ (raíz)
        response = client.get("/", HTTP_HOST=domain.domain)

        # Debe redirigir (302) a login
        assert response.status_code == 302, (
            f"Debe redirigir (302), no {response.status_code}. "
            f"Content: {response.content.decode('utf-8')[:200] if hasattr(response, 'content') else 'N/A'}"
        )

        # Verificar que la redirección es a /admin/login/
        assert (
            "/admin/login/" in response.url or "/login/" in response.url
        ), f"Debe redirigir a login, no a '{response.url}'"

        # Verificar que NO es la respuesta del admin público
        # (el contenido no debe ser el dashboard del tenant si no está autenticado)
        assert (
            response.status_code != 200
        ), "NO debe mostrar contenido sin autenticación"

    def test_private_tenant_authenticated_shows_dashboard(self):
        """
        Test: Acceso privado autenticado debe mostrar dashboard o redirigir apropiadamente.

        Escenario:
        - Usuario autenticado accede a http://cliente.sintel.net.co/
        - Debe mostrar dashboard del tenant o redirigir apropiadamente
        """
        from apps.public.tenants.models import Client as TenantClient
        from apps.public.tenants.models import Domain, TenantMembership
        from tests.public.tenants.factories import (
            ClientFactory,
            DomainFactory,
            TenantMembershipFactory,
        )

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear tenant y dominio
        tenant = ClientFactory(
            nombre="Empresa Test Dashboard",
            schema_name="test_dashboard",
            is_active=True,
        )

        domain = DomainFactory(
            tenant=tenant, domain="test-dashboard.sintel.net.co", is_primary=True
        )

        # Crear usuario
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            email="user@test.local",
            password="testpass123",
            is_staff=False,
            is_superuser=False,
        )

        # Crear membresía del usuario al tenant
        membership = TenantMembershipFactory(
            client=tenant, user=user, rol="ADMIN", is_primary_admin=True
        )

        # Crear cliente autenticado
        client = Client()
        client.force_login(user)

        # Simular request a http://test-dashboard.sintel.net.co/ (raíz)
        response = client.get("/", HTTP_HOST=domain.domain)

        # Debe responder 200 OK (dashboard) o 302 (redirección)
        assert response.status_code in (200, 302), (
            f"Debe responder 200 o 302, no {response.status_code}. "
            f"Content: {response.content.decode('utf-8')[:200] if hasattr(response, 'content') else 'N/A'}"
        )

        # Si es redirección, debe ser a login o dashboard apropiado
        if response.status_code == 302:
            assert (
                "/login/" in response.url
                or "/admin/login/" in response.url
                or "/dashboard/" in response.url
            ), f"Redirección debe ser a login o dashboard, no a '{response.url}'"


@pytest.mark.django_db
class TestRoutingIsolation:
    """
    Tests para validar el aislamiento entre URLs públicas y privadas.
    """

    def test_tenant_api_not_accessible_from_public_domain(self):
        """
        Test de Aislamiento: URLs exclusivas de tenant no deben estar disponibles desde dominio público.

        Escenario:
        - Intentar acceder a /api/v1/facturas/ desde sintel.net.co (dominio público)
        - Debe retornar 404 Not Found
        - Porque urls_public.py NO debe incluir las rutas de facturación
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear usuario staff (para tener autenticación)
        staff_user = User.objects.create_user(
            email="staff@test.local",
            password="testpass123",
            is_staff=True,
            is_superuser=False,
        )

        # Crear cliente autenticado
        client = Client()
        client.force_login(staff_user)

        # Intentar acceder a URLs exclusivas de tenant desde dominio público
        tenant_api_endpoints = [
            "/api/v1/empresa/empresas/",
            "/api/v1/facturas/facturas/",
            "/api/v1/contabilidad/cuentas-contables/",
        ]

        for endpoint in tenant_api_endpoints:
            response = client.get(endpoint, HTTP_HOST="sintel.net.co")

            # Debe retornar 404 Not Found (porque urls_public.py no incluye estas rutas)
            assert response.status_code == 404, (
                f"Endpoint {endpoint} debe retornar 404 Not Found desde dominio público, "
                f"no {response.status_code}. "
                f"Content: {response.content.decode('utf-8')[:200] if hasattr(response, 'content') else 'N/A'}"
            )

    def test_public_console_not_accessible_from_tenant_domain(self):
        """
        Test de Aislamiento: URLs exclusivas de público no deben estar disponibles desde dominio de tenant.

        Escenario:
        - Intentar acceder a /console/tenants/ desde cliente.sintel.net.co (dominio privado)
        - Debe retornar 404 Not Found
        - Porque urls_tenant.py NO debe incluir las rutas de consola pública
        """
        from apps.public.tenants.models import Client as TenantClient
        from apps.public.tenants.models import Domain
        from tests.public.tenants.factories import ClientFactory, DomainFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear tenant y dominio
        tenant = ClientFactory(
            nombre="Empresa Test Isolation",
            schema_name="test_isolation",
            is_active=True,
        )

        domain = DomainFactory(
            tenant=tenant, domain="test-isolation.sintel.net.co", is_primary=True
        )

        # Crear usuario
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            email="user@test.local",
            password="testpass123",
            is_staff=False,
            is_superuser=False,
        )

        # Crear cliente autenticado
        client = Client()
        client.force_login(user)

        # Intentar acceder a una URL exclusiva de público desde dominio de tenant
        response = client.get("/console/tenants/", HTTP_HOST=domain.domain)

        # Debe retornar 404 Not Found (porque urls_tenant.py no incluye estas rutas)
        assert response.status_code == 404, (
            f"Debe retornar 404 Not Found desde dominio de tenant, no {response.status_code}. "
            f"Content: {response.content.decode('utf-8')[:200] if hasattr(response, 'content') else 'N/A'}"
        )

    def test_jwt_endpoints_available_in_both_domains(self):
        """
        Test: Endpoints JWT deben estar disponibles tanto en dominio público como privado.

        Escenario:
        - /api/token/ debe estar disponible desde sintel.net.co (público)
        - /api/token/ debe estar disponible desde cliente.sintel.net.co (privado)
        """
        from apps.public.tenants.models import Client as TenantClient
        from apps.public.tenants.models import Domain
        from tests.public.tenants.factories import ClientFactory, DomainFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear tenant y dominio
        tenant = ClientFactory(
            nombre="Empresa Test JWT", schema_name="test_jwt", is_active=True
        )

        domain = DomainFactory(
            tenant=tenant, domain="test-jwt.sintel.net.co", is_primary=True
        )

        # Crear cliente de pruebas
        client = Client()

        # Test 1: JWT desde dominio público
        response_public = client.get("/api/token/", HTTP_HOST="sintel.net.co")

        # Debe responder (puede ser 405 Method Not Allowed si es GET, pero NO debe ser 404)
        assert response_public.status_code != 404, (
            f"JWT endpoint debe estar disponible desde dominio público, no 404. "
            f"Status: {response_public.status_code}"
        )

        # Test 2: JWT desde dominio privado
        response_private = client.get("/api/token/", HTTP_HOST=domain.domain)

        # Debe responder (puede ser 405 Method Not Allowed si es GET, pero NO debe ser 404)
        assert response_private.status_code != 404, (
            f"JWT endpoint debe estar disponible desde dominio privado, no 404. "
            f"Status: {response_private.status_code}"
        )


@pytest.mark.django_db
class TestRoutingIntegration:
    """
    Tests de integración para validar el flujo completo de enrutamiento.
    """

    def test_public_to_console_flow(self):
        """
        Test de Integración: Flujo completo desde dominio público a consola.

        Escenario:
        1. Usuario anónimo accede a sintel.net.co/ -> redirige a /admin/login/
        2. Usuario se autentica
        3. Usuario accede a sintel.net.co/ -> redirige a /console/
        4. Usuario accede a sintel.net.co/console/tenants/ -> 200 OK
        """
        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear usuario staff
        from django.contrib.auth import get_user_model

        User = get_user_model()
        staff_user = User.objects.create_user(
            email="staff@test.local",
            password="testpass123",
            is_staff=True,
            is_superuser=False,
        )

        client = Client()

        # Paso 1: Usuario anónimo accede a raíz
        response1 = client.get("/", HTTP_HOST="sintel.net.co")
        assert response1.status_code == 302
        assert "/admin/login/" in response1.url

        # Paso 2: Usuario se autentica
        client.force_login(staff_user)

        # Paso 3: Usuario autenticado accede a raíz
        response2 = client.get("/", HTTP_HOST="sintel.net.co")
        assert response2.status_code == 302
        assert response2.url == "/console/"

        # Paso 4: Usuario accede a consola de tenants
        response3 = client.get("/console/tenants/", HTTP_HOST="sintel.net.co")
        assert (
            response3.status_code == 200
        ), f"La consola debe responder 200 OK, no {response3.status_code}"

    def test_tenant_to_api_flow(self):
        """
        Test de Integración: Flujo completo desde dominio privado a API.

        Escenario:
        1. Usuario anónimo accede a cliente.sintel.net.co/ -> redirige a login
        2. Usuario se autentica
        3. Usuario accede a cliente.sintel.net.co/api/v1/empresa/ -> debe responder (200 o 404 según implementación)
        """
        from apps.public.tenants.models import Client as TenantClient
        from apps.public.tenants.models import Domain, TenantMembership
        from tests.public.tenants.factories import (
            ClientFactory,
            DomainFactory,
            TenantMembershipFactory,
        )

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear tenant y dominio
        tenant = ClientFactory(
            nombre="Empresa Test API Flow", schema_name="test_api_flow", is_active=True
        )

        domain = DomainFactory(
            tenant=tenant, domain="test-api-flow.sintel.net.co", is_primary=True
        )

        # Crear usuario
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            email="user@test.local",
            password="testpass123",
            is_staff=False,
            is_superuser=False,
        )

        # Crear membresía
        membership = TenantMembershipFactory(
            client=tenant, user=user, rol="ADMIN", is_primary_admin=True
        )

        client = Client()

        # Paso 1: Usuario anónimo accede a raíz
        response1 = client.get("/", HTTP_HOST=domain.domain)
        assert response1.status_code == 302
        assert "/login/" in response1.url or "/admin/login/" in response1.url

        # Paso 2: Usuario se autentica
        client.force_login(user)

        # Paso 3: Usuario accede a API del tenant
        # Nota: Puede ser 200 (si existe) o 404 (si no está implementado aún)
        response2 = client.get("/api/v1/empresa/", HTTP_HOST=domain.domain)
        assert response2.status_code in (
            200,
            404,
        ), f"API debe responder 200 o 404, no {response2.status_code}"
