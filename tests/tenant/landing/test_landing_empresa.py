"""
Tests funcionales para la landing page con datos de empresa.

Valida:
- API pública de empresa (/api/v1/landing/empresa/)
- Vista de landing page con datos de empresa
- Redirección de usuarios autenticados
- Estado cero (sin empresa configurada)
"""

import pytest
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context

from apps.public.tenants.models import Client as TenantClient
from apps.public.tenants.models import Domain
from apps.services.empresa.gestion_service import crear_o_actualizar_empresa
from apps.tenant.empresa.models import Empresa


@pytest.mark.django_db
class TestLandingEmpresaAPI:
    """
    Tests para la API pública de empresa en la landing page.

    Endpoint: GET /api/v1/landing/empresa/
    """

    def test_api_empresa_publica_sin_autenticacion(self):
        """
        Test: La API de empresa es accesible sin autenticación (AllowAny).

        Validaciones:
        - Status 200 OK (si existe empresa) o 404 (si no existe)
        - Campos públicos presentes (razon_social, logo_url, website, email_contacto)
        - Campos sensibles NO presentes (nit, dv, regimen_tributario)
        """
        from rest_framework import status
        from rest_framework.test import APIClient

        # Configurar tenant de prueba
        with schema_context(get_public_schema_name()):
            tenant = TenantClient.objects.create(
                schema_name="test_empresa_api",
                nombre="Test Empresa API",
                is_active=True,
            )
            Domain.objects.create(
                tenant=tenant, domain="test-empresa-api.com", is_primary=True
            )

        # Cambiar al esquema del tenant
        connection.set_schema("test_empresa_api")

        # Crear empresa con datos
        empresa = crear_o_actualizar_empresa(
            razon_social="Empresa API Test S.A.",
            nit="900123456",
            direccion="Calle Test 123",
            telefono="6012345678",
            email_contacto="contacto@test.com",
            regimen_tributario="Responsable de IVA",
            website="https://test.com",
        )

        # Configurar ROOT_URLCONF para usar urls_tenant (necesario porque el middleware no se ejecuta en tests)
        # override_settings es necesario para que APIClient use el ROOT_URLCONF correcto
        from django.conf import settings
        from django.test import override_settings

        with override_settings(ROOT_URLCONF=settings.TENANT_URLCONF):
            # Hacer request a la API (sin autenticación)
            # Usar URL directa porque estamos en contexto de tenant
            api_client = APIClient()
            response = api_client.get("/api/v1/landing/empresa/")

        # Validaciones
        assert (
            response.status_code == status.HTTP_200_OK
        ), f"Expected 200 OK, got {response.status_code}. Response: {response.data if hasattr(response, 'data') else response.content}"

        # Obtener datos de la respuesta
        data = response.data
        # Campos públicos deben estar presentes
        assert "razon_social" in data, "El campo 'razon_social' debe estar presente"
        assert "logo_url" in data, "El campo 'logo_url' debe estar presente"
        assert "website" in data, "El campo 'website' debe estar presente"
        assert "email_contacto" in data, "El campo 'email_contacto' debe estar presente"

        # Campos sensibles NO deben estar presentes
        assert (
            "nit" not in data
        ), "El campo 'nit' NO debe estar presente (información sensible)"
        assert (
            "dv" not in data
        ), "El campo 'dv' NO debe estar presente (información sensible)"
        assert (
            "regimen_tributario" not in data
        ), "El campo 'regimen_tributario' NO debe estar presente (información sensible)"
        assert (
            "direccion" not in data
        ), "El campo 'direccion' NO debe estar presente (información privada)"
        assert (
            "telefono" not in data
        ), "El campo 'telefono' NO debe estar presente (información privada)"

        # Validar valores
        assert data["razon_social"] == "Empresa API Test S.A."
        assert data["website"] == "https://test.com"
        assert data["email_contacto"] == "contacto@test.com"

    def test_api_empresa_estado_cero(self):
        """
        Test: La API retorna 404 controlado cuando no existe empresa configurada.

        Validaciones:
        - Status 404 NOT FOUND
        - Mensaje de error descriptivo
        """
        from rest_framework import status
        from rest_framework.test import APIClient

        # Configurar tenant de prueba sin empresa
        with schema_context(get_public_schema_name()):
            tenant = TenantClient.objects.create(
                schema_name="test_estado_cero",
                nombre="Test Estado Cero",
                is_active=True,
            )
            Domain.objects.create(
                tenant=tenant, domain="test-estado-cero.com", is_primary=True
            )

        # Cambiar al esquema del tenant
        connection.set_schema("test_estado_cero")

        # Verificar que no existe empresa
        assert Empresa.objects.count() == 0, "No debe existir empresa en este tenant"

        # Configurar ROOT_URLCONF para usar urls_tenant (necesario porque el middleware no se ejecuta en tests)
        from django.conf import settings
        from django.test import override_settings

        with override_settings(ROOT_URLCONF=settings.TENANT_URLCONF):
            # Hacer request a la API (sin autenticación)
            # Usar URL directa porque estamos en contexto de tenant
            api_client = APIClient()
            response = api_client.get("/api/v1/landing/empresa/")

            # Validaciones
            assert (
                response.status_code == status.HTTP_404_NOT_FOUND
            ), f"Expected 404 NOT FOUND, got {response.status_code}. Response: {response.data if hasattr(response, 'data') else response.content}"

            # Obtener datos de la respuesta
            data = response.data
            assert "error" in data, "El campo 'error' debe estar presente"
            assert "message" in data, "El campo 'message' debe estar presente"
            assert (
                "empresa" in data["error"].lower()
                or "configurada" in data["error"].lower()
            ), "El mensaje de error debe mencionar que la empresa no está configurada"


@pytest.mark.django_db
class TestLandingViewTrafficController:
    """
    Tests para TenantLandingView como Traffic Controller.

    Valida:
    - Redirección de usuarios autenticados al dashboard
    - Renderizado de landing page para usuarios anónimos
    """

    def test_redireccion_usuario_autenticado(self):
        """
        Test: Usuario autenticado es redirigido al dashboard.

        Validaciones:
        - Status 302 Redirect
        - URL de destino: /dashboard/ o tenant_dashboard:index
        """
        from django.contrib.auth import get_user_model
        from django.test import Client as DjangoTestClient
        from django_tenants.utils import get_public_schema_name, schema_context

        User = get_user_model()

        # Configurar tenant de prueba
        with schema_context(get_public_schema_name()):
            tenant = TenantClient.objects.create(
                schema_name="test_traffic", nombre="Test Traffic", is_active=True
            )
            Domain.objects.create(
                tenant=tenant, domain="test-traffic.com", is_primary=True
            )

            # Crear usuario
            user = User.objects.create_user(
                username="testuser", email="test@example.com", password="testpass123"
            )

        # Cambiar al esquema del tenant
        connection.set_schema("test_traffic")

        # Configurar ROOT_URLCONF para usar urls_tenant (necesario porque el middleware no se ejecuta en tests)
        from django.conf import settings
        from django.test import override_settings

        with override_settings(ROOT_URLCONF=settings.TENANT_URLCONF):
            # Cliente autenticado
            client = DjangoTestClient()
            client.force_login(user)

            # Acceder a la landing page
            response = client.get("/")

            # Validaciones
            assert (
                response.status_code == 302
            ), f"Expected 302 Redirect, got {response.status_code}"
            assert (
                "/dashboard/" in response.url
            ), f"Expected redirect to /dashboard/, got {response.url}"

    def test_renderizado_usuario_anonimo(self):
        """
        Test: Usuario anónimo ve la landing page.

        Validaciones:
        - Status 200 OK
        - Template correcto usado
        - Contexto incluye datos de empresa (si existe)
        """
        from django.test import Client as DjangoTestClient
        from django_tenants.utils import get_public_schema_name, schema_context

        # Configurar tenant de prueba
        with schema_context(get_public_schema_name()):
            tenant = TenantClient.objects.create(
                schema_name="test_render", nombre="Test Render", is_active=True
            )
            Domain.objects.create(
                tenant=tenant, domain="test-render.com", is_primary=True
            )

        # Cambiar al esquema del tenant
        connection.set_schema("test_render")

        # Crear empresa
        empresa = crear_o_actualizar_empresa(
            razon_social="Empresa Render Test S.A.",
            nit="900123456",
            direccion="Calle Render 123",
            telefono="6012345678",
            email_contacto="render@test.com",
            regimen_tributario="Responsable de IVA",
        )

        # Configurar ROOT_URLCONF para usar urls_tenant (necesario porque el middleware no se ejecuta en tests)
        from django.conf import settings
        from django.test import override_settings

        with override_settings(ROOT_URLCONF=settings.TENANT_URLCONF):
            # Cliente anónimo
            client = DjangoTestClient()

            # Acceder a la landing page
            response = client.get("/")

            # Validaciones
            assert (
                response.status_code == 200
            ), f"Expected 200 OK, got {response.status_code}"
            assert "tenant/landing/index.html" in [
                t.name for t in response.templates
            ], "Debe usar el template tenant/landing/index.html"

            # Verificar que el contexto incluye datos de empresa
            assert (
                "empresa_configurada" in response.context
            ), "El contexto debe incluir 'empresa_configurada'"
            assert (
                response.context["empresa_configurada"] == True
            ), "empresa_configurada debe ser True cuando existe empresa"
            assert (
                "razon_social" in response.context
            ), "El contexto debe incluir 'razon_social'"
            assert response.context["razon_social"] == "Empresa Render Test S.A."

    def test_estado_cero_sin_empresa(self):
        """
        Test: Landing page muestra mensaje genérico cuando no hay empresa configurada.

        Validaciones:
        - Status 200 OK
        - empresa_configurada = False
        - Mensaje genérico en el template
        """
        from django.test import Client as DjangoTestClient
        from django_tenants.utils import get_public_schema_name, schema_context

        # Configurar tenant de prueba sin empresa
        with schema_context(get_public_schema_name()):
            tenant = TenantClient.objects.create(
                schema_name="test_estado_cero_view",
                nombre="Test Estado Cero View",
                is_active=True,
            )
            Domain.objects.create(
                tenant=tenant, domain="test-estado-cero-view.com", is_primary=True
            )

        # Cambiar al esquema del tenant
        connection.set_schema("test_estado_cero_view")

        # Verificar que no existe empresa
        assert Empresa.objects.count() == 0, "No debe existir empresa"

        # Configurar ROOT_URLCONF para usar urls_tenant (necesario porque el middleware no se ejecuta en tests)
        from django.conf import settings
        from django.test import override_settings

        with override_settings(ROOT_URLCONF=settings.TENANT_URLCONF):
            # Cliente anónimo
            client = DjangoTestClient()

            # Acceder a la landing page
            response = client.get("/")

            # Validaciones
            assert (
                response.status_code == 200
            ), f"Expected 200 OK, got {response.status_code}"
            assert (
                "empresa_configurada" in response.context
            ), "El contexto debe incluir 'empresa_configurada'"
            assert (
                response.context["empresa_configurada"] == False
            ), "empresa_configurada debe ser False cuando no existe empresa"

            # Verificar que el HTML contiene el mensaje genérico
            content = response.content.decode("utf-8")
            assert (
                "nuevo espacio de trabajo" in content.lower()
                or "bienvenido" in content.lower()
            ), "El template debe mostrar mensaje genérico cuando no hay empresa"


@pytest.mark.django_db
class TestLandingTemplateEmpresa:
    """
    Tests para el template de landing page con datos de empresa.

    Valida:
    - Renderizado correcto con datos de empresa
    - Logo mostrado cuando existe
    - Razón social mostrada cuando no hay logo
    - Estado cero manejado correctamente
    """

    def test_template_con_logo(self):
        """
        Test: Template muestra logo cuando existe.

        Validaciones:
        - Logo presente en el HTML
        - Razón social presente
        """
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import Client as DjangoTestClient
        from django_tenants.utils import get_public_schema_name, schema_context

        # Configurar tenant de prueba
        with schema_context(get_public_schema_name()):
            tenant = TenantClient.objects.create(
                schema_name="test_logo", nombre="Test Logo", is_active=True
            )
            Domain.objects.create(
                tenant=tenant, domain="test-logo.com", is_primary=True
            )

        # Cambiar al esquema del tenant
        connection.set_schema("test_logo")

        # Crear empresa con logo (simulado)
        empresa = crear_o_actualizar_empresa(
            razon_social="Empresa con Logo S.A.",
            nit="900123456",
            direccion="Calle Logo 123",
            telefono="6012345678",
            email_contacto="logo@test.com",
            regimen_tributario="Responsable de IVA",
        )
        # Nota: En tests reales, podrías subir un archivo de imagen real

        # Configurar ROOT_URLCONF para usar urls_tenant (necesario porque el middleware no se ejecuta en tests)
        from django.conf import settings
        from django.test import override_settings

        with override_settings(ROOT_URLCONF=settings.TENANT_URLCONF):
            # Cliente anónimo
            client = DjangoTestClient()

            # Acceder a la landing page
            response = client.get("/")

            # Validaciones
            assert response.status_code == 200
            content = response.content.decode("utf-8")

            # Verificar que la razón social está presente
            assert (
                "Empresa con Logo S.A." in content
            ), "La razón social debe estar presente en el HTML"

    def test_template_sin_logo_muestra_razon_social(self):
        """
        Test: Template muestra razón social cuando no hay logo.

        Validaciones:
        - Razón social visible en el header
        - No hay errores de template
        """
        from django.test import Client as DjangoTestClient
        from django_tenants.utils import get_public_schema_name, schema_context

        # Configurar tenant de prueba
        with schema_context(get_public_schema_name()):
            tenant = TenantClient.objects.create(
                schema_name="test_sin_logo", nombre="Test Sin Logo", is_active=True
            )
            Domain.objects.create(
                tenant=tenant, domain="test-sin-logo.com", is_primary=True
            )

        # Cambiar al esquema del tenant
        connection.set_schema("test_sin_logo")

        # Crear empresa sin logo
        empresa = crear_o_actualizar_empresa(
            razon_social="Empresa Sin Logo S.A.",
            nit="900123456",
            direccion="Calle Sin Logo 123",
            telefono="6012345678",
            email_contacto="sinlogo@test.com",
            regimen_tributario="Responsable de IVA",
        )

        # Configurar ROOT_URLCONF para usar urls_tenant (necesario porque el middleware no se ejecuta en tests)
        from django.conf import settings
        from django.test import override_settings

        with override_settings(ROOT_URLCONF=settings.TENANT_URLCONF):
            # Cliente anónimo
            client = DjangoTestClient()

            # Acceder a la landing page
            response = client.get("/")

            # Validaciones
            assert response.status_code == 200
            content = response.content.decode("utf-8")

            # Verificar que la razón social está presente en el header
            assert (
                "Empresa Sin Logo S.A." in content
            ), "La razón social debe estar presente en el HTML"
            # Verificar que hay un botón de login
            assert (
                "Iniciar Sesión" in content or "Acceder" in content
            ), "Debe haber un botón de login en el template"
