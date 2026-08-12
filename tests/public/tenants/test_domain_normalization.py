"""
Suite de Tests Funcionales - Normalización de Dominios (QA)

Valida que la lógica de normalización de dominios funciona correctamente
en el proceso de onboarding de tenants:

- Normalización de protocolo y case (HTTPS://Mi.Empresa.Com/ → mi.empresa.com)
- Normalización de WWW (www.cliente.com → cliente.com)
- Regresión CRUD básico (verificar que sigue funcionando)
- Validación de dominios inválidos (debe retornar 400)
"""

import pytest
from django.db import connection

# Imports dentro de funciones para evitar problemas de configuración de Django
# Los modelos, factories y APIClient se importan dentro de las funciones que los usan
# El fixture api_client está definido en conftest.py


@pytest.mark.django_db
class TestDomainNormalizationProtocolAndCase:
    """
    Test de Normalización: Protocolo y Case.

    Escenario: Enviar dominio con protocolo HTTPS, mayúsculas y barra final.
    Validar que se normaliza correctamente a FQDN limpio.
    """

    def test_normalize_https_uppercase_with_slash(self, api_client):
        """
        Test: Normalizar dominio con HTTPS, mayúsculas y barra final.

        Input: "HTTPS://Mi.Empresa.Com/"
        Expected: "mi.empresa.com"
        """
        from django.contrib.auth import get_user_model
        from django.urls import reverse
        from rest_framework import status

        from tests.public.tenants.factories import UserFactory

        User = get_user_model()

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear usuario staff para autenticación
        staff_user = UserFactory(is_staff=True, is_superuser=True)
        api_client.force_authenticate(user=staff_user)

        # Crear usuario admin para el tenant
        admin_user = UserFactory()

        # Payload con dominio "sucio"
        payload = {
            "nombre": "Mi Empresa Test",
            "dominio": "HTTPS://Mi.Empresa.Com/",
            "admin_user_id": admin_user.id,
        }

        # Enviar POST al endpoint de onboard
        # F29-002: nombre real "tenant-onboard" desde Fase 5-BIS.
        url = reverse("tenant-onboard")
        response = api_client.post(url, payload, format="json")

        # Assert: Debe crear exitosamente
        assert (
            response.status_code == status.HTTP_201_CREATED
        ), f"Expected 201, got {response.status_code}. Response: {response.data}"

        # Assert Crítico: El dominio en la respuesta debe estar normalizado
        domain_in_response = response.data.get("domain", {}).get("domain", "")
        assert domain_in_response == "mi.empresa.com", (
            f"Expected 'mi.empresa.com', got '{domain_in_response}'. "
            f"Full response: {response.data}"
        )

        # Assert: Verificar en la base de datos que el dominio se guardó normalizado
        from apps.public.tenants.models import Domain

        domain_in_db = Domain.objects.filter(domain="mi.empresa.com").first()
        assert (
            domain_in_db is not None
        ), "El dominio 'mi.empresa.com' debe existir en la base de datos"
        assert (
            domain_in_db.domain == "mi.empresa.com"
        ), f"El dominio en BD debe ser 'mi.empresa.com', got '{domain_in_db.domain}'"

        # Limpieza: Eliminar el tenant creado
        if domain_in_db:
            domain_in_db.tenant.delete(force_drop=True)


@pytest.mark.django_db
class TestDomainNormalizationWWW:
    """
    Test de Normalización: Prefijo WWW.

    Escenario: Enviar dominio con prefijo www.
    Validar que se elimina el prefijo www. según la regla definida.
    """

    def test_normalize_www_prefix(self, api_client):
        """
        Test: Normalizar dominio con prefijo www.

        Input: "www.cliente.com"
        Expected: "cliente.com" (www. eliminado)
        """
        from django.urls import reverse
        from rest_framework import status

        from tests.public.tenants.factories import UserFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear usuario admin para el tenant
        admin_user = UserFactory()

        # Payload con dominio con www
        payload = {
            "nombre": "Cliente Test",
            "dominio": "www.cliente.com",
            "admin_user_id": admin_user.id,
        }

        # Enviar POST al endpoint de onboard
        # F29-002: nombre real "tenant-onboard" desde Fase 5-BIS.
        url = reverse("tenant-onboard")
        response = api_client.post(url, payload, format="json")

        # Assert: Debe crear exitosamente
        assert (
            response.status_code == status.HTTP_201_CREATED
        ), f"Expected 201, got {response.status_code}. Response: {response.data}"

        # Assert: El dominio debe estar normalizado (sin www)
        domain_in_response = response.data.get("domain", {}).get("domain", "")
        assert domain_in_response == "cliente.com", (
            f"Expected 'cliente.com', got '{domain_in_response}'. "
            f"Full response: {response.data}"
        )

        # Limpieza: Eliminar el tenant creado
        from apps.public.tenants.models import Domain

        domain_in_db = Domain.objects.filter(domain="cliente.com").first()
        if domain_in_db:
            domain_in_db.tenant.delete(force_drop=True)


@pytest.mark.django_db
class TestDomainNormalizationRegression:
    """
    Test de Regresión: CRUD Básico.

    Escenario: Verificar que la creación de tenants sigue funcionando
    correctamente con un payload estándar válido.
    """

    def test_onboard_with_valid_domain(self, api_client):
        """
        Test: Crear tenant con dominio válido y verificar respuesta completa.

        Verifica que:
        - La creación funciona correctamente
        - Se devuelven los campos esperados (client, domain, login_url)
        - El dominio se guarda correctamente en BD
        """
        from django.urls import reverse
        from rest_framework import status

        from tests.public.tenants.factories import UserFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear usuario admin para el tenant
        admin_user = UserFactory()

        # Payload estándar válido
        payload = {
            "nombre": "Empresa Regresión",
            "dominio": "empresa.test.com",
            "admin_user_id": admin_user.id,
        }

        # Enviar POST al endpoint de onboard
        # F29-002: nombre real "tenant-onboard" desde Fase 5-BIS.
        url = reverse("tenant-onboard")
        response = api_client.post(url, payload, format="json")

        # Assert: Debe crear exitosamente
        assert (
            response.status_code == status.HTTP_201_CREATED
        ), f"Expected 201, got {response.status_code}. Response: {response.data}"

        # Assert: Verificar estructura de respuesta
        assert "client" in response.data, "La respuesta debe incluir 'client'"
        assert "domain" in response.data, "La respuesta debe incluir 'domain'"
        assert "login_url" in response.data, "La respuesta debe incluir 'login_url'"

        # Assert: Verificar campos del client
        client_data = response.data["client"]
        assert "id" in client_data, "client debe incluir 'id'"
        assert "nombre" in client_data, "client debe incluir 'nombre'"
        assert (
            client_data["nombre"] == "Empresa Regresión"
        ), f"Expected 'Empresa Regresión', got '{client_data['nombre']}'"

        # Assert: Verificar campos del domain
        domain_data = response.data["domain"]
        assert "id" in domain_data, "domain debe incluir 'id'"
        assert "domain" in domain_data, "domain debe incluir 'domain'"
        assert (
            domain_data["domain"] == "empresa.test.com"
        ), f"Expected 'empresa.test.com', got '{domain_data['domain']}'"

        # Assert: Verificar login_url
        login_url = response.data["login_url"]
        assert isinstance(login_url, str), "login_url debe ser una cadena"
        assert len(login_url) > 0, "login_url no debe estar vacío"
        # [WARNING] REGLA DE NEGOCIO: login_url debe apuntar a la raíz (/) - landing page
        assert login_url.endswith(
            "/"
        ), f"login_url debe terminar en '/', got '{login_url}'"
        assert (
            "/login" not in login_url
        ), f"login_url NO debe contener '/login', got '{login_url}'"

        # Limpieza: Eliminar el tenant creado
        from apps.public.tenants.models import Domain

        domain_in_db = Domain.objects.filter(domain="empresa.test.com").first()
        if domain_in_db:
            domain_in_db.tenant.delete(force_drop=True)


@pytest.mark.django_db
class TestDomainNormalizationInvalid:
    """
    Test de Validación: Dominios Inválidos.

    Escenario: Enviar dominios inválidos (con espacios, caracteres ilegales, etc.).
    Validar que se retorna 400 Bad Request con mensaje de error apropiado.
    """

    def test_invalid_domain_with_spaces(self, api_client):
        """
        Test: Validar que dominios con espacios retornan 400.

        Input: "not a domain"
        Expected: 400 Bad Request
        """
        from django.urls import reverse
        from rest_framework import status

        from tests.public.tenants.factories import UserFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear usuario admin para el tenant
        admin_user = UserFactory()

        # Payload con dominio inválido (espacios)
        payload = {
            "nombre": "Empresa Inválida",
            "dominio": "not a domain",
            "admin_user_id": admin_user.id,
        }

        # Enviar POST al endpoint de onboard
        # F29-002: nombre real "tenant-onboard" desde Fase 5-BIS.
        url = reverse("tenant-onboard")
        response = api_client.post(url, payload, format="json")

        # Assert: Debe retornar 400 Bad Request
        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), f"Expected 400, got {response.status_code}. Response: {response.data}"

        # Assert: Debe incluir mensaje de error relacionado con dominio
        # El error puede estar en 'dominio' o en el nivel raíz
        error_data = response.data
        has_domain_error = (
            "dominio" in error_data
            or any("dominio" in str(key).lower() for key in error_data.keys())
            or any("fqdn" in str(value).lower() for value in error_data.values())
            or any("válido" in str(value).lower() for value in error_data.values())
        )
        assert has_domain_error, (
            f"La respuesta debe incluir un error relacionado con el dominio. "
            f"Response: {error_data}"
        )

    def test_invalid_domain_empty_string(self, api_client):
        """
        Test: Validar que dominios vacíos retornan 400.

        Input: ""
        Expected: 400 Bad Request
        """
        from django.urls import reverse
        from rest_framework import status

        from tests.public.tenants.factories import UserFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear usuario admin para el tenant
        admin_user = UserFactory()

        # Payload con dominio vacío
        payload = {
            "nombre": "Empresa Sin Dominio",
            "dominio": "",
            "admin_user_id": admin_user.id,
        }

        # Enviar POST al endpoint de onboard
        # F29-002: nombre real "tenant-onboard" desde Fase 5-BIS.
        url = reverse("tenant-onboard")
        response = api_client.post(url, payload, format="json")

        # Assert: Debe retornar 400 Bad Request
        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), f"Expected 400, got {response.status_code}. Response: {response.data}"

    def test_invalid_domain_no_dot(self, api_client):
        """
        Test: Validar que dominios sin punto (no FQDN) retornan 400.

        Input: "notafqdn"
        Expected: 400 Bad Request (debe ser FQDN válido)
        """
        from django.urls import reverse
        from rest_framework import status

        from tests.public.tenants.factories import UserFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear usuario admin para el tenant
        admin_user = UserFactory()

        # Payload con dominio sin punto (no es FQDN)
        payload = {
            "nombre": "Empresa Sin FQDN",
            "dominio": "notafqdn",
            "admin_user_id": admin_user.id,
        }

        # Enviar POST al endpoint de onboard
        # F29-002: nombre real "tenant-onboard" desde Fase 5-BIS.
        url = reverse("tenant-onboard")
        response = api_client.post(url, payload, format="json")

        # Assert: Debe retornar 400 Bad Request
        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), f"Expected 400, got {response.status_code}. Response: {response.data}"


@pytest.mark.django_db
class TestDomainNormalizationEdgeCases:
    """
    Test de Casos Límite: Normalización de Dominios.

    Escenarios adicionales para validar robustez de la normalización.
    """

    def test_normalize_domain_with_port(self, api_client):
        """
        Test: Normalizar dominio con puerto.

        Input: "cliente.com:8000"
        Expected: "cliente.com" (puerto eliminado)
        """
        from django.urls import reverse
        from rest_framework import status

        from tests.public.tenants.factories import UserFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear usuario admin para el tenant
        admin_user = UserFactory()

        # Payload con dominio con puerto
        payload = {
            "nombre": "Cliente Con Puerto",
            "dominio": "cliente.com:8000",
            "admin_user_id": admin_user.id,
        }

        # Enviar POST al endpoint de onboard
        # F29-002: nombre real "tenant-onboard" desde Fase 5-BIS.
        url = reverse("tenant-onboard")
        response = api_client.post(url, payload, format="json")

        # Assert: Debe crear exitosamente
        assert (
            response.status_code == status.HTTP_201_CREATED
        ), f"Expected 201, got {response.status_code}. Response: {response.data}"

        # Assert: El dominio debe estar normalizado (sin puerto)
        domain_in_response = response.data.get("domain", {}).get("domain", "")
        assert domain_in_response == "cliente.com", (
            f"Expected 'cliente.com', got '{domain_in_response}'. "
            f"Full response: {response.data}"
        )

        # Limpieza: Eliminar el tenant creado
        from apps.public.tenants.models import Domain

        domain_in_db = Domain.objects.filter(domain="cliente.com").first()
        if domain_in_db:
            domain_in_db.tenant.delete(force_drop=True)

    def test_normalize_domain_with_path(self, api_client):
        """
        Test: Normalizar dominio con ruta.

        Input: "cliente.com/admin/login/"
        Expected: "cliente.com" (ruta eliminada)
        """
        from django.urls import reverse
        from rest_framework import status

        from tests.public.tenants.factories import UserFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear usuario admin para el tenant
        admin_user = UserFactory()

        # Payload con dominio con ruta
        payload = {
            "nombre": "Cliente Con Ruta",
            "dominio": "cliente.com/admin/login/",
            "admin_user_id": admin_user.id,
        }

        # Enviar POST al endpoint de onboard
        # F29-002: nombre real "tenant-onboard" desde Fase 5-BIS.
        url = reverse("tenant-onboard")
        response = api_client.post(url, payload, format="json")

        # Assert: Debe crear exitosamente
        assert (
            response.status_code == status.HTTP_201_CREATED
        ), f"Expected 201, got {response.status_code}. Response: {response.data}"

        # Assert: El dominio debe estar normalizado (sin ruta)
        domain_in_response = response.data.get("domain", {}).get("domain", "")
        assert domain_in_response == "cliente.com", (
            f"Expected 'cliente.com', got '{domain_in_response}'. "
            f"Full response: {response.data}"
        )

        # Limpieza: Eliminar el tenant creado
        from apps.public.tenants.models import Domain

        domain_in_db = Domain.objects.filter(domain="cliente.com").first()
        if domain_in_db:
            domain_in_db.tenant.delete(force_drop=True)

    def test_normalize_domain_complex(self, api_client):
        """
        Test: Normalizar dominio complejo con múltiples elementos.

        Input: "HTTPS://WWW.Test-Tenant-01.Sintel.Com:8000/Admin/Login/"
        Expected: "test-tenant-01.sintel.net.co" (todo normalizado)
        """
        from django.urls import reverse
        from rest_framework import status

        from tests.public.tenants.factories import UserFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear usuario admin para el tenant
        admin_user = UserFactory()

        # Payload con dominio complejo
        payload = {
            "nombre": "Test Tenant Normalization Complex",
            "dominio": "HTTPS://WWW.Test-Tenant-01.Sintel.Com:8000/Admin/Login/",
            "admin_user_id": admin_user.id,
        }

        # Enviar POST al endpoint de onboard
        # F29-002: nombre real "tenant-onboard" desde Fase 5-BIS.
        url = reverse("tenant-onboard")
        response = api_client.post(url, payload, format="json")

        # Assert: Debe crear exitosamente
        assert (
            response.status_code == status.HTTP_201_CREATED
        ), f"Expected 201, got {response.status_code}. Response: {response.data}"

        # Assert: El dominio debe estar completamente normalizado
        domain_in_response = response.data.get("domain", {}).get("domain", "")
        assert domain_in_response == "test-tenant-01.sintel.net.co", (
            f"Expected 'test-tenant-01.sintel.net.co', got '{domain_in_response}'. "
            f"Full response: {response.data}"
        )

        # Limpieza: Eliminar el tenant creado
        from apps.public.tenants.models import Domain

        domain_in_db = Domain.objects.filter(domain="test-tenant-01.sintel.net.co").first()
        if domain_in_db:
            domain_in_db.tenant.delete(force_drop=True)
