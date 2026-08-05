"""
Tests de flujo de activación para desarrollo/QA (v2.30 API-First).

[WARNING] OBJETIVO: Verificar el flujo completo de activación desde onboarding hasta activación exitosa.

Cobertura:
- Crear owner con set_unusable_password() en onboarding
- Generar token de activación válido
- GET /api/v1/landing/auth/activate/?token=... → 200 cuando unusable
- GET /api/v1/landing/auth/activate/?token=... → 409 cuando usable
- POST /api/v1/landing/auth/activate/?token=... → activación exitosa
"""

import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework import status
from rest_framework.test import APIClient

from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.public.tenants.services.invitations import (
    build_activation_url,
    generate_invitation_token,
)

User = get_user_model()


@pytest.mark.django_db
class TestActivationDevFlow:
    """Tests del flujo completo de activación para desarrollo/QA."""

    def test_onboarding_creates_owner_with_unusable_password(
        self, tenant_factory, user_factory
    ):
        """
        Verifica que el onboarding crea owners con set_unusable_password().
        """
        # Crear tenant y usuario mediante onboarding simulado
        tenant = tenant_factory(schema_name="testcorp", nombre="Test Corp SAS")
        domain = Domain.objects.create(
            domain="testcorp.localhost", tenant=tenant, is_primary=True
        )

        # Simular creación de owner como en onboarding
        user = user_factory(email="owner@testcorp.com")
        user.set_unusable_password()  # [WARNING] CRÍTICO: Como en onboarding
        user.save()

        # Verificar que NO tiene contraseña usable
        assert (
            not user.has_usable_password()
        ), "El owner debe crearse sin contraseña usable"

        # Crear membresía
        TenantMembership.objects.create(
            client=tenant,
            user=user,
            rol="ADMIN",
            is_primary_admin=True,
            is_active=True,
        )

        # Verificar que el usuario existe y está configurado correctamente
        assert user.is_active, "El usuario debe estar activo"
        assert user.email == "owner@testcorp.com"

    def test_generate_activation_token_for_unusable_user(
        self, tenant_factory, user_factory
    ):
        """
        Verifica que se puede generar un token de activación para un usuario sin contraseña usable.
        """
        tenant = tenant_factory(schema_name="testcorp", nombre="Test Corp SAS")
        domain = Domain.objects.create(
            domain="testcorp.localhost", tenant=tenant, is_primary=True
        )
        user = user_factory(email="owner@testcorp.com")
        user.set_unusable_password()
        user.save()

        TenantMembership.objects.create(
            client=tenant,
            user=user,
            rol="ADMIN",
            is_primary_admin=True,
            is_active=True,
        )

        # Generar token
        token = generate_invitation_token(user.id, tenant.id, ttl_hours=1)

        # Verificar que el token se generó
        assert token, "El token debe generarse correctamente"
        assert len(token) > 0, "El token no debe estar vacío"

        # Construir URL de activación
        activation_url = build_activation_url(domain.domain, token)

        # Verificar que la URL apunta a la API
        assert (
            "/api/v1/landing/auth/activate/" in activation_url
        ), "La URL debe apuntar a la API"
        assert f"token={token}" in activation_url, "La URL debe incluir el token"
        assert (
            "testcorp.localhost" in activation_url
        ), "La URL debe incluir el dominio del tenant"

    def test_get_activation_endpoint_with_unusable_password(
        self, tenant_factory, user_factory
    ):
        """
        Verifica que GET /api/v1/landing/auth/activate/?token=... retorna 200 cuando el usuario NO tiene contraseña usable.
        """
        tenant = tenant_factory(schema_name="testcorp", nombre="Test Corp SAS")
        domain = Domain.objects.create(
            domain="testcorp.localhost", tenant=tenant, is_primary=True
        )
        user = user_factory(email="owner@testcorp.com")
        user.set_unusable_password()
        user.save()

        TenantMembership.objects.create(
            client=tenant,
            user=user,
            rol="ADMIN",
            is_primary_admin=True,
            is_active=True,
        )

        # Generar token
        token = generate_invitation_token(user.id, tenant.id)

        # GET /api/v1/landing/auth/activate/?token=...
        client = APIClient()
        response = client.get(
            f"/api/v1/landing/auth/activate/?token={token}",
            HTTP_HOST="testcorp.localhost",
        )

        # Debe retornar 200
        assert (
            response.status_code == status.HTTP_200_OK
        ), f"Debe retornar 200 cuando el usuario NO tiene contraseña usable. Status: {response.status_code}, Response: {response.data}"

        data = response.json()
        assert data["token_valid"] is True
        assert data["user"]["email"] == "owner@testcorp.com"
        assert data["user"]["has_usable_password"] is False
        assert data["tenant"]["nombre"] == "Test Corp SAS"

    def test_get_activation_endpoint_with_usable_password_returns_409(
        self, tenant_factory, user_factory
    ):
        """
        Verifica que GET /api/v1/landing/auth/activate/?token=... retorna 409 cuando el usuario YA tiene contraseña usable.
        """
        tenant = tenant_factory(schema_name="testcorp", nombre="Test Corp SAS")
        domain = Domain.objects.create(
            domain="testcorp.localhost", tenant=tenant, is_primary=True
        )
        user = user_factory(email="owner@testcorp.com")
        user.set_password("ExistingPassword123!")  # [WARNING] Contraseña usable
        user.save()

        TenantMembership.objects.create(
            client=tenant,
            user=user,
            rol="ADMIN",
            is_primary_admin=True,
            is_active=True,
        )

        # Generar token
        token = generate_invitation_token(user.id, tenant.id)

        # GET /api/v1/landing/auth/activate/?token=...
        client = APIClient()
        response = client.get(
            f"/api/v1/landing/auth/activate/?token={token}",
            HTTP_HOST="testcorp.localhost",
        )

        # [WARNING] v2.30: Debe retornar 409 CONFLICT
        assert (
            response.status_code == status.HTTP_409_CONFLICT
        ), f"Debe retornar 409 cuando el usuario YA tiene contraseña usable. Status: {response.status_code}, Response: {response.data}"

        data = response.json()
        assert "ya fue activada" in data["detail"].lower()
        assert data["redirect_url"] == "/login/"

    def test_post_activation_endpoint_successful_activation(
        self, tenant_factory, user_factory
    ):
        """
        Verifica que POST /api/v1/landing/auth/activate/?token=... activa correctamente un usuario sin contraseña usable.
        """
        tenant = tenant_factory(schema_name="testcorp", nombre="Test Corp SAS")
        domain = Domain.objects.create(
            domain="testcorp.localhost", tenant=tenant, is_primary=True
        )
        user = user_factory(email="owner@testcorp.com")
        user.set_unusable_password()
        user.save()

        TenantMembership.objects.create(
            client=tenant,
            user=user,
            rol="ADMIN",
            is_primary_admin=True,
            is_active=True,
        )

        # Generar token
        token = generate_invitation_token(user.id, tenant.id)

        # POST /api/v1/landing/auth/activate/?token=...
        client = APIClient()
        response = client.post(
            f"/api/v1/landing/auth/activate/?token={token}",
            {
                "password1": "NewPassword123!",
                "password2": "NewPassword123!",
            },
            HTTP_HOST="testcorp.localhost",
            format="json",
        )

        # Debe retornar 200 con redirect_url absoluta
        assert (
            response.status_code == status.HTTP_200_OK
        ), f"Debe retornar 200 después de activación exitosa. Status: {response.status_code}, Response: {response.data}"

        data = response.json()
        assert "redirect_url" in data
        assert data["redirect_url"].startswith("http://") or data[
            "redirect_url"
        ].startswith("https://")
        assert "/dashboard/" in data["redirect_url"]
        assert "testcorp.localhost" in data["redirect_url"]

        # Verificar que la contraseña fue establecida
        user.refresh_from_db()
        assert (
            user.has_usable_password()
        ), "El usuario debe tener contraseña usable después de activación"
        assert user.check_password(
            "NewPassword123!"
        ), "La contraseña debe ser la establecida"

    def test_activation_url_points_to_api_endpoint(self, tenant_factory, user_factory):
        """
        Verifica que build_activation_url genera URLs que apuntan a la API (v2.30).
        """
        tenant = tenant_factory(schema_name="testcorp", nombre="Test Corp SAS")
        domain = Domain.objects.create(
            domain="testcorp.localhost", tenant=tenant, is_primary=True
        )
        user = user_factory(email="owner@testcorp.com")
        user.set_unusable_password()
        user.save()

        TenantMembership.objects.create(
            client=tenant,
            user=user,
            rol="ADMIN",
            is_primary_admin=True,
            is_active=True,
        )

        # Generar token y URL
        token = generate_invitation_token(user.id, tenant.id)
        activation_url = build_activation_url(domain.domain, token)

        # Verificar que la URL apunta a la API
        assert (
            "/api/v1/landing/auth/activate/" in activation_url
        ), f"La URL debe apuntar a la API. URL: {activation_url}"
        assert f"token={token}" in activation_url, "La URL debe incluir el token"
        assert activation_url.startswith("http://") or activation_url.startswith(
            "https://"
        ), "La URL debe ser absoluta"

        # Verificar que NO apunta a rutas HTML antiguas
        assert (
            "/activate?" not in activation_url
            or "/api/v1/landing/auth/activate/" in activation_url
        ), "La URL NO debe apuntar a rutas HTML antiguas"
        assert "/login/" not in activation_url, "La URL NO debe apuntar a /login/"
