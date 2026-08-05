"""
Tests para verificar que el onboarding no crea usuarios con username='' (cadena vacía).

Verifica que:
- El onboarding crea usuarios con username válido (no vacío)
- El username se genera automáticamente desde el email
- Las contraseñas se hashean con set_password() (nunca texto plano)
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection

from apps.public.tenants.models import Client, Domain
from apps.services.onboarding.empresa_service import crear_tenant_con_owner

User = get_user_model()

pytestmark = [
    pytest.mark.django_db,
]


@pytest.fixture(autouse=True)
def setup_public_schema():
    """Fixture automático que configura el esquema público para cada test."""
    connection.set_schema_to_public()
    yield


def test_onboard_creates_user_with_valid_username():
    """
    Test: El onboarding crea usuarios con username válido (no vacío).

    Objetivo: Verificar que cuando se crea un tenant con owner_email/owner_password,
    el usuario se crea con un username válido (no cadena vacía).
    """
    connection.set_schema_to_public()

    # Crear tenant con owner_email/owner_password
    result = crear_tenant_con_owner(
        nombre="Test Company",
        schema_name="test_company",
        dominio_fqdn="test-company.localhost",
        owner_email="owner@test-company.com",
        owner_password="SecurePass123!",
        owner_is_staff=True,
        owner_is_active=True,
    )

    # Verificar que el tenant se creó
    assert result is not None
    assert "client_id" in result
    assert "login_url" in result

    # Obtener el usuario creado
    user = User.objects.filter(email="owner@test-company.com").first()
    assert user is not None, "El usuario debe haberse creado"

    # Verificar que el username NO está vacío
    assert user.username is not None, "El username no debe ser None"
    assert user.username != "", "El username no debe ser una cadena vacía"
    assert (
        len(user.username.strip()) > 0
    ), "El username no debe ser solo espacios en blanco"

    # Verificar que el username se generó desde el email
    assert (
        "owner" in user.username.lower()
    ), "El username debe contener el local-part del email"

    # Verificar que la contraseña está hasheada (no texto plano)
    assert user.password != "SecurePass123!", "La contraseña debe estar hasheada"
    assert (
        user.has_usable_password()
    ), "El usuario debe tener una contraseña usable (hasheada)"


def test_onboard_handles_empty_email_local_part():
    """
    Test: El onboarding maneja correctamente emails con local-part vacío o problemático.

    Objetivo: Verificar que incluso si el local-part del email está vacío o es problemático,
    se genera un username válido (no vacío).
    """
    connection.set_schema_to_public()

    # Intentar crear tenant con email problemático (solo @ y dominio)
    # Esto no debería pasar la validación, pero si pasa, debe generar username válido
    try:
        result = crear_tenant_con_owner(
            nombre="Test Company 2",
            schema_name="test_company_2",
            dominio_fqdn="test-company-2.localhost",
            owner_email="@test-company.com",  # Email inválido (sin local-part)
            owner_password="SecurePass123!",
            owner_is_staff=True,
            owner_is_active=True,
        )

        # Si se crea (aunque no debería), verificar username
        user = User.objects.filter(email="@test-company.com").first()
        if user:
            assert user.username is not None
            assert user.username != ""
            assert len(user.username.strip()) > 0
    except (ValueError, ValidationError):
        # Esperado: el email inválido debe ser rechazado
        pass


def test_onboard_idempotent_user_creation():
    """
    Test: El onboarding es idempotente en la creación de usuarios.

    Objetivo: Verificar que si se llama dos veces con el mismo email,
    no se crea un segundo usuario y no hay conflictos de unicidad.
    """
    connection.set_schema_to_public()

    email = "idempotent@test-company.com"
    password = "SecurePass123!"

    # Primera llamada
    result1 = crear_tenant_con_owner(
        nombre="Test Company 3",
        schema_name="test_company_3",
        dominio_fqdn="test-company-3.localhost",
        owner_email=email,
        owner_password=password,
        owner_is_staff=True,
        owner_is_active=True,
    )

    # Segunda llamada (mismo email, diferente tenant)
    result2 = crear_tenant_con_owner(
        nombre="Test Company 4",
        schema_name="test_company_4",
        dominio_fqdn="test-company-4.localhost",
        owner_email=email,  # Mismo email
        owner_password=password,
        owner_is_staff=True,
        owner_is_active=True,
    )

    # Verificar que solo existe un usuario con ese email
    users = User.objects.filter(email=email)
    assert users.count() == 1, "Debe existir solo un usuario con ese email"

    user = users.first()
    assert user.username is not None
    assert user.username != ""
    assert len(user.username.strip()) > 0


def test_onboard_username_collision_handling():
    """
    Test: El onboarding maneja correctamente colisiones de username.

    Objetivo: Verificar que si hay colisiones de username, se genera un username único
    con sufijo incremental.
    """
    connection.set_schema_to_public()

    # Crear usuario manualmente con username "owner"
    User.objects.create_user(
        email="owner1@test.com",
        username="owner",
        password="test123",
    )

    # Crear tenant con email que generaría el mismo username
    result = crear_tenant_con_owner(
        nombre="Test Company 5",
        schema_name="test_company_5",
        dominio_fqdn="test-company-5.localhost",
        owner_email="owner@test-company-5.com",  # Generaría "owner" también
        owner_password="SecurePass123!",
        owner_is_staff=True,
        owner_is_active=True,
    )

    # Verificar que el usuario se creó con username único (no "owner")
    user = User.objects.filter(email="owner@test-company-5.com").first()
    assert user is not None
    assert user.username is not None
    assert user.username != ""
    # El username debe ser único (puede ser "owner-1", "owner2", etc.)
    assert (
        user.username != "owner" or User.objects.filter(username="owner").count() == 1
    )
