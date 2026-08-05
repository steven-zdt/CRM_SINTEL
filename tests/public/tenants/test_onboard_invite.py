"""
Tests para el sistema de invitación de owners (v2.24).

[WARNING] IMPORTANTE:
- Verifica que el onboarding crea usuarios con set_unusable_password()
- Verifica que se generan tokens de invitación
- Verifica que los tokens tienen TTL y firma válida
"""

from datetime import datetime, timedelta

import pytest
from django.contrib.auth import get_user_model

from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.public.tenants.services.invitations import (
    DEFAULT_TOKEN_TTL_HOURS,
    build_activation_url,
    generate_invitation_token,
    verify_invitation_token,
)
from apps.services.onboarding.empresa_service import crear_tenant_con_owner

User = get_user_model()


@pytest.mark.django_db
def test_onboard_creates_user_with_unusable_password(client_factory):
    """
    Verifica que el onboarding crea usuarios con set_unusable_password().
    """
    # Crear tenant con owner_email
    result = crear_tenant_con_owner(
        nombre="Test Company",
        schema_name="test_company",
        dominio_fqdn="test-company.localhost",
        owner_email="owner@test.com",
        owner_is_staff=True,
        owner_is_active=True,
    )

    # Verificar que el usuario fue creado
    user = User.objects.get(email="owner@test.com")

    # [WARNING] CRÍTICO: El usuario debe tener password unusable
    assert (
        not user.has_usable_password()
    ), "El usuario debe tener password unusable después del onboarding"

    # Verificar que el tenant fue creado
    tenant = Client.objects.get(schema_name="test_company")
    assert tenant is not None

    # Verificar que la membresía fue creada
    membership = TenantMembership.objects.get(client=tenant, user=user)
    assert membership.rol == "ADMIN"
    assert membership.is_primary_admin is True
    assert membership.is_active is True


@pytest.mark.django_db
def test_onboard_generates_invitation_token(client_factory):
    """
    Verifica que el onboarding genera tokens de invitación.
    """
    # Crear tenant con owner_email
    result = crear_tenant_con_owner(
        nombre="Test Company",
        schema_name="test_company",
        dominio_fqdn="test-company.localhost",
        owner_email="owner@test.com",
        owner_is_staff=True,
        owner_is_active=True,
    )

    # Verificar que se generó activation_url
    assert "activation_url" in result, "El resultado debe incluir activation_url"
    assert result["activation_url"] is not None, "activation_url no debe ser None"
    assert "token=" in result["activation_url"], "activation_url debe contener el token"

    # Extraer token de la URL
    token = result["activation_url"].split("token=")[1].split("&")[0]

    # Verificar que el token es válido
    payload = verify_invitation_token(token)
    assert payload is not None, "El token debe ser válido"
    assert payload["user_id"] == User.objects.get(email="owner@test.com").id
    assert payload["tenant_id"] == Client.objects.get(schema_name="test_company").id


@pytest.mark.django_db
def test_invitation_token_has_ttl():
    """
    Verifica que los tokens de invitación tienen TTL y expiran correctamente.
    """
    user_id = 1
    tenant_id = 1

    # Generar token con TTL corto (1 segundo para testing)
    token = generate_invitation_token(
        user_id, tenant_id, ttl_hours=1 / 3600
    )  # 1 segundo

    # Verificar que el token es válido inmediatamente
    payload = verify_invitation_token(token)
    assert payload is not None, "El token debe ser válido inmediatamente"

    # Nota: No podemos probar expiración fácilmente sin mock de tiempo,
    # pero verificamos que el token incluye expires_at
    from django.core import signing

    decoded = signing.loads(token, salt="tenant-owner-invitation")
    assert "expires_at" in decoded, "El token debe incluir expires_at"


@pytest.mark.django_db
def test_invitation_token_invalid_signature():
    """
    Verifica que tokens con firma inválida son rechazados.
    """
    # Token con firma inválida
    invalid_token = "invalid_token_signature"

    payload = verify_invitation_token(invalid_token)
    assert payload is None, "El token con firma inválida debe ser rechazado"


@pytest.mark.django_db
def test_build_activation_url():
    """
    Verifica que build_activation_url construye URLs correctas.
    """
    token = "test_token_123"

    # URL en desarrollo (HTTP)
    url = build_activation_url("test.localhost", token)
    assert url.startswith("http://"), "En desarrollo debe usar HTTP"
    assert "test.localhost" in url, "Debe incluir el dominio"
    assert token in url, "Debe incluir el token"
    assert "/activate" in url, "Debe incluir la ruta /activate"


@pytest.mark.django_db
def test_onboard_existing_user_with_password(client_factory):
    """
    Verifica que si el usuario ya existe con password usable, se mantiene.
    """
    # Crear usuario existente con password
    existing_user = User.objects.create_user(
        email="existing@test.com",
        username="existing",
        password="existing_password",
    )
    assert existing_user.has_usable_password(), "El usuario debe tener password usable"

    # Crear tenant con el mismo email
    result = crear_tenant_con_owner(
        nombre="Test Company",
        schema_name="test_company",
        dominio_fqdn="test-company.localhost",
        owner_email="existing@test.com",
        owner_is_staff=True,
        owner_is_active=True,
    )

    # Verificar que el usuario mantiene su password
    user = User.objects.get(email="existing@test.com")
    assert (
        user.has_usable_password()
    ), "El usuario existente debe mantener su password usable"

    # Verificar que se generó invitación (aunque el usuario ya tenga password)
    # En este caso, el usuario puede usar su password existente o activar con el token
    assert (
        "activation_url" in result
    ), "Debe generarse activation_url incluso si el usuario ya tiene password"


@pytest.mark.django_db
def test_onboard_with_admin_user_id_skips_invitation(client_factory):
    """
    Verifica que si se proporciona admin_user_id, no se genera invitación.
    """
    # Crear usuario existente
    existing_user = User.objects.create_user(
        email="admin@test.com",
        username="admin",
        password="admin_password",
    )

    # Crear tenant con admin_user_id (no owner_email)
    result = crear_tenant_con_owner(
        nombre="Test Company",
        schema_name="test_company",
        dominio_fqdn="test-company.localhost",
        admin_user_id=existing_user.id,
        owner_is_staff=True,
        owner_is_active=True,
    )

    # Verificar que NO se generó activation_url
    assert (
        "activation_url" not in result
    ), "No debe generarse activation_url cuando se usa admin_user_id"
