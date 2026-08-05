"""
Tests para prevenir UnboundLocalError en TenantLoginAPIView.

Valida que redirect_url esté siempre definida antes de usarse y que
todas las ramas de ejecución manejen correctamente los errores.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.test import APIClient

from apps.public.tenants.models import Client, Domain, TenantMembership

User = get_user_model()


@pytest.mark.django_db
class TestTenantLoginUnboundLocalError:
    """
    Tests para prevenir UnboundLocalError en TenantLoginAPIView.
    """

    def setup_method(self):
        """Configuración inicial para cada test."""
        self.client = APIClient()
        self.factory = RequestFactory()

        # Crear tenant de prueba
        with schema_context("public"):
            self.tenant = Client.objects.create(
                schema_name="test_tenant",
                nombre="Test Tenant",
            )
            self.domain = Domain.objects.create(
                domain="test.localhost",
                tenant=self.tenant,
                is_primary=True,
            )

    def test_login_credenciales_invalidas_no_usa_redirect_url(self):
        """
        Test: Credenciales inválidas → 400 sin tocar redirect_url.

        Valida que no se produzca UnboundLocalError cuando las credenciales
        son inválidas y redirect_url nunca se calcula.
        """
        url = "/api/v1/landing/auth/login/"

        # Intentar login con credenciales inválidas
        response = self.client.post(
            url,
            {
                "email": "nonexistent@test.com",
                "password": "wrongpassword",
            },
            HTTP_HOST="test.localhost",
            format="json",
        )

        # Debe retornar 400 sin UnboundLocalError
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data or "non_field_errors" in response.data
        # No debe haber redirect_url en la respuesta
        assert "redirect_url" not in response.data

    def test_login_sin_membresia_no_usa_redirect_url(self):
        """
        Test: Sin membresía → 400 sin tocar redirect_url.

        Valida que no se produzca UnboundLocalError cuando el usuario
        no tiene membresía en el tenant y redirect_url nunca se calcula.
        """
        with schema_context("public"):
            # Crear usuario sin membresía en el tenant
            user = User.objects.create_user(
                email="user@test.com",
                username="user",
                password="testpass123",
            )

        url = "/api/v1/landing/auth/login/"

        # Intentar login con usuario sin membresía
        response = self.client.post(
            url,
            {
                "email": "user@test.com",
                "password": "testpass123",
            },
            HTTP_HOST="test.localhost",
            format="json",
        )

        # Debe retornar 400 sin UnboundLocalError
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data or "non_field_errors" in response.data
        # No debe haber redirect_url en la respuesta
        assert "redirect_url" not in response.data

    def test_login_exitoso_retorna_redirect_url(self):
        """
        Test: Éxito → 200 con redirect_url no vacío.

        Valida que cuando el login es exitoso, redirect_url esté definida
        y sea una URL absoluta válida.
        """
        with schema_context("public"):
            # Crear usuario con membresía
            user = User.objects.create_user(
                email="admin@test.com",
                username="admin",
                password="testpass123",
            )
            TenantMembership.objects.create(
                client=self.tenant,
                user=user,
                rol="ADMIN",
                is_active=True,
            )

        url = "/api/v1/landing/auth/login/"

        # Login exitoso
        response = self.client.post(
            url,
            {
                "email": "admin@test.com",
                "password": "testpass123",
            },
            HTTP_HOST="test.localhost",
            format="json",
        )

        # Debe retornar 200 con redirect_url
        assert response.status_code == status.HTTP_200_OK
        assert "redirect_url" in response.data
        assert response.data["redirect_url"] is not None
        assert response.data["redirect_url"] != ""
        # redirect_url debe ser absoluta (contener http:// o https://)
        assert response.data["redirect_url"].startswith(("http://", "https://"))

    def test_login_payload_invalido_no_usa_redirect_url(self):
        """
        Test: Payload inválido → 400 sin tocar redirect_url.

        Valida que no se produzca UnboundLocalError cuando el payload
        es inválido (falta email o password).
        """
        url = "/api/v1/landing/auth/login/"

        # Intentar login sin email
        response = self.client.post(
            url,
            {
                "password": "testpass123",
            },
            HTTP_HOST="test.localhost",
            format="json",
        )

        # Debe retornar 400 sin UnboundLocalError
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # No debe haber redirect_url en la respuesta
        assert "redirect_url" not in response.data

        # Intentar login sin password
        response = self.client.post(
            url,
            {
                "email": "test@test.com",
            },
            HTTP_HOST="test.localhost",
            format="json",
        )

        # Debe retornar 400 sin UnboundLocalError
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # No debe haber redirect_url en la respuesta
        assert "redirect_url" not in response.data

    def test_login_excepcion_no_usa_redirect_url(self, monkeypatch):
        """
        Test: Excepción simulada → 500 sin redirect_url.

        Valida que cuando ocurre una excepción no controlada, no se
        produzca UnboundLocalError y se retorne 500 sin redirect_url.
        """

        # Simular excepción en el serializer
        def mock_is_valid(*args, **kwargs):
            raise Exception("Error simulado para testing")

        from apps.tenant.landing.api.serializers import TenantLoginSerializer
        from apps.tenant.landing.api.views import TenantLoginAPIView

        # Monkeypatch del serializer para forzar excepción
        original_is_valid = TenantLoginSerializer.is_valid

        try:
            TenantLoginSerializer.is_valid = mock_is_valid

            url = "/api/v1/landing/auth/login/"

            response = self.client.post(
                url,
                {
                    "email": "test@test.com",
                    "password": "testpass123",
                },
                HTTP_HOST="test.localhost",
                format="json",
            )

            # Debe retornar 500 sin UnboundLocalError
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "detail" in response.data
            # No debe haber redirect_url en la respuesta
            assert "redirect_url" not in response.data
        finally:
            # Restaurar método original
            TenantLoginSerializer.is_valid = original_is_valid

    def test_redirect_url_siempre_definida_en_exito(self):
        """
        Test: Validar que redirect_url esté siempre definida en caso de éxito.

        Valida que en ningún caso de éxito, redirect_url sea None o no esté definida.
        """
        with schema_context("public"):
            # Crear usuarios con diferentes roles
            admin_user = User.objects.create_user(
                email="admin@test.com",
                username="admin",
                password="testpass123",
            )
            TenantMembership.objects.create(
                client=self.tenant,
                user=admin_user,
                rol="ADMIN",
                is_active=True,
            )

            staff_user = User.objects.create_user(
                email="staff@test.com",
                username="staff",
                password="testpass123",
            )
            TenantMembership.objects.create(
                client=self.tenant,
                user=staff_user,
                rol="STAFF",
                is_active=True,
            )

            user_user = User.objects.create_user(
                email="user@test.com",
                username="user",
                password="testpass123",
            )
            TenantMembership.objects.create(
                client=self.tenant,
                user=user_user,
                rol="USER",
                is_active=True,
            )

        url = "/api/v1/landing/auth/login/"

        # Probar con cada rol
        for email, expected_role in [
            ("admin@test.com", "ADMIN"),
            ("staff@test.com", "STAFF"),
            ("user@test.com", "USER"),
        ]:
            response = self.client.post(
                url,
                {
                    "email": email,
                    "password": "testpass123",
                },
                HTTP_HOST="test.localhost",
                format="json",
            )

            # Debe retornar 200 con redirect_url definida
            assert (
                response.status_code == status.HTTP_200_OK
            ), f"Login falló para {email}"
            assert (
                "redirect_url" in response.data
            ), f"redirect_url no está en respuesta para {email}"
            assert (
                response.data["redirect_url"] is not None
            ), f"redirect_url es None para {email}"
            assert (
                response.data["redirect_url"] != ""
            ), f"redirect_url está vacía para {email}"
            # redirect_url debe contener la ruta correspondiente al rol
            if expected_role == "ADMIN":
                assert "/dashboard/admin/" in response.data["redirect_url"]
            elif expected_role == "STAFF":
                assert "/dashboard/staff/" in response.data["redirect_url"]
            elif expected_role == "USER":
                assert "/dashboard/user/" in response.data["redirect_url"]
