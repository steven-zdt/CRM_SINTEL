"""
Tests para API de password reset (API-First v2.30).

Endpoints:
- POST /api/v1/landing/auth/password-reset/request/
- GET  /api/v1/landing/auth/password-reset/validate/
- POST /api/v1/landing/auth/password-reset/confirm/
"""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework import status
from rest_framework.test import APIClient

from apps.public.tenants.models import Client, Domain, TenantMembership

User = get_user_model()


@pytest.fixture
def tenant_with_user(tenant_factory, user_factory):
    """Crea un tenant con un usuario activo con contraseña usable."""
    with schema_context(get_public_schema_name()):
        tenant = tenant_factory(schema_name="testtenant", nombre="Test Tenant")
        domain = Domain.objects.create(
            tenant=tenant, domain="testtenant.localhost", is_primary=True
        )
        user = user_factory(email="user@testtenant.com")
        user.set_password("oldpassword123")
        user.save()
        TenantMembership.objects.create(
            client=tenant, user=user, rol="ADMIN", is_active=True
        )
    return tenant, user, domain


@pytest.fixture
def api_client():
    """Cliente API sin autenticación."""
    return APIClient()


@pytest.mark.django_db
@patch("apps.public.tenants.services.password_reset.send_password_reset_email")
def test_password_reset_request_200_success(
    mock_send_email, api_client, tenant_with_user
):
    """POST /password-reset/request/ retorna 200 y envía email cuando el usuario existe."""
    tenant, user, domain = tenant_with_user

    url = "/api/v1/landing/auth/password-reset/request/"
    response = api_client.post(
        url, {"email": user.email}, HTTP_HOST=domain.domain, format="json"
    )

    assert response.status_code == status.HTTP_200_OK
    assert "recibirás un correo" in response.data["detail"].lower()
    mock_send_email.assert_called_once()

    # Verificar que la URL de reset se construyó correctamente
    call_args = mock_send_email.call_args
    assert call_args[0][0] == user  # user
    assert call_args[0][1] == tenant  # tenant
    assert (
        "/api/v1/landing/auth/password-reset/confirm/" in call_args[0][2]
    )  # reset_url


@pytest.mark.django_db
def test_password_reset_request_200_idempotent(api_client, tenant_with_user):
    """POST /password-reset/request/ retorna 200 incluso si el email no existe (idempotente)."""
    tenant, user, domain = tenant_with_user

    url = "/api/v1/landing/auth/password-reset/request/"
    response = api_client.post(
        url,
        {"email": "nonexistent@testtenant.com"},
        HTTP_HOST=domain.domain,
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "recibirás un correo" in response.data["detail"].lower()


@pytest.mark.django_db
def test_password_reset_request_400_no_password_usable(api_client, tenant_with_user):
    """POST /password-reset/request/ retorna 400 si el usuario no tiene contraseña usable."""
    tenant, user, domain = tenant_with_user

    # Marcar contraseña como unusable
    user.set_unusable_password()
    user.save()

    url = "/api/v1/landing/auth/password-reset/request/"
    response = api_client.post(
        url, {"email": user.email}, HTTP_HOST=domain.domain, format="json"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "activado" in response.data["detail"].lower()


@pytest.mark.django_db
def test_password_reset_validate_200_valid_token(api_client, tenant_with_user):
    """GET /password-reset/validate/ retorna 200 cuando el token es válido."""
    tenant, user, domain = tenant_with_user

    # Generar token Django estándar
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    url = f"/api/v1/landing/auth/password-reset/validate/?uidb64={uidb64}&token={token}"
    response = api_client.get(url, HTTP_HOST=domain.domain)

    assert response.status_code == status.HTTP_200_OK
    assert "válido" in response.data["detail"].lower()
    assert response.data["user"]["email"] == user.email


@pytest.mark.django_db
def test_password_reset_validate_400_invalid_token(api_client, tenant_with_user):
    """GET /password-reset/validate/ retorna 400 cuando el token es inválido."""
    tenant, user, domain = tenant_with_user

    # Generar token inválido
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = "invalid-token"

    url = f"/api/v1/landing/auth/password-reset/validate/?uidb64={uidb64}&token={token}"
    response = api_client.get(url, HTTP_HOST=domain.domain)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        "inválido" in response.data["detail"].lower()
        or "expirado" in response.data["detail"].lower()
    )


@pytest.mark.django_db
def test_password_reset_confirm_200_success(api_client, tenant_with_user):
    """POST /password-reset/confirm/ establece nueva contraseña y retorna redirect_url."""
    tenant, user, domain = tenant_with_user

    # Generar token Django estándar
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    url = f"/api/v1/landing/auth/password-reset/confirm/?uidb64={uidb64}&token={token}"
    response = api_client.post(
        url,
        {
            "password1": "newpassword123",
            "password2": "newpassword123",
        },
        HTTP_HOST=domain.domain,
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "restablecida" in response.data["detail"].lower()
    assert "redirect_url" in response.data
    assert "/login/" in response.data["redirect_url"]
    assert "login_api_url" in response.data

    # Verificar que la contraseña se cambió
    user.refresh_from_db()
    assert user.check_password("newpassword123")
    assert not user.check_password("oldpassword123")


@pytest.mark.django_db
def test_password_reset_confirm_400_passwords_mismatch(api_client, tenant_with_user):
    """POST /password-reset/confirm/ retorna 400 cuando las contraseñas no coinciden."""
    tenant, user, domain = tenant_with_user

    # Generar token Django estándar
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    url = f"/api/v1/landing/auth/password-reset/confirm/?uidb64={uidb64}&token={token}"
    response = api_client.post(
        url,
        {
            "password1": "newpassword123",
            "password2": "differentpassword123",
        },
        HTTP_HOST=domain.domain,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "no coinciden" in str(response.data).lower()


@pytest.mark.django_db
def test_password_reset_confirm_400_invalid_token(api_client, tenant_with_user):
    """POST /password-reset/confirm/ retorna 400 cuando el token es inválido."""
    tenant, user, domain = tenant_with_user

    # Generar token inválido
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = "invalid-token"

    url = f"/api/v1/landing/auth/password-reset/confirm/?uidb64={uidb64}&token={token}"
    response = api_client.post(
        url,
        {
            "password1": "newpassword123",
            "password2": "newpassword123",
        },
        HTTP_HOST=domain.domain,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        "inválido" in str(response.data).lower()
        or "expirado" in str(response.data).lower()
    )


@pytest.mark.django_db
def test_password_reset_confirm_no_auto_login(api_client, tenant_with_user):
    """POST /password-reset/confirm/ NO hace auto-login (seguridad)."""
    tenant, user, domain = tenant_with_user

    # Generar token Django estándar
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    url = f"/api/v1/landing/auth/password-reset/confirm/?uidb64={uidb64}&token={token}"
    response = api_client.post(
        url,
        {
            "password1": "newpassword123",
            "password2": "newpassword123",
        },
        HTTP_HOST=domain.domain,
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    # Verificar que NO hay sesión iniciada
    # (el cliente no debería tener user autenticado)
    assert not hasattr(api_client, "session") or not api_client.session.get(
        "_auth_user_id"
    )
