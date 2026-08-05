"""
Tests para creación de usuarios (CRUD robusto).

Verifica que:
- Se puede crear un usuario con email + password + password2
- El password no se expone en la respuesta
- El username se genera automáticamente si el modelo lo tiene
- Las contraseñas deben coincidir
- No se pueden crear usuarios duplicados
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.urls("config.urls_public"),
]


@pytest.fixture
def api_client():
    """Cliente API para tests."""
    return APIClient()


@pytest.fixture
def staff_user(db):
    """Usuario staff global."""
    connection.set_schema_to_public()
    return User.objects.create_user(
        email="staff@test.local", password="staff123", is_staff=True, is_active=True
    )


def test_create_user_minimal_ok(api_client, staff_user):
    """Test: Crear usuario exitosamente con email + password + password2."""
    connection.set_schema_to_public()

    api_client.force_authenticate(user=staff_user)

    response = api_client.post(
        "/api/admin/v1/accounts/users/",
        {
            "email": "owner@example.com",
            "password": "Secr3tPass!",
            "password2": "Secr3tPass!",
        },
        format="json",
    )

    assert (
        response.status_code == status.HTTP_201_CREATED
    ), f"Se esperaba 201, pero se recibió {response.status_code}. Respuesta: {response.data}"

    data = response.json()

    # Verificar que password NO está en la respuesta
    assert "password" not in data, "El password no debe estar en la respuesta"
    assert "password2" not in data, "El password2 no debe estar en la respuesta"

    # Verificar datos del usuario
    assert data["email"] == "owner@example.com"

    # Verificar que el usuario existe en la BD
    user = User.objects.get(email="owner@example.com")
    assert user is not None

    # Verificar que el username se haya generado si existe ese campo
    if hasattr(User, "username"):
        assert user.username, "El username no debe estar vacío"
        assert len(user.username) > 0, "El username debe tener contenido"

    # Verificar que el password está hasheado (no es texto plano)
    assert user.password != "Secr3tPass!", "El password debe estar hasheado"
    assert user.password.startswith("pbkdf2_") or user.password.startswith(
        "argon2"
    ), "El password debe estar hasheado con un algoritmo seguro"


def test_create_user_password_mismatch(api_client, staff_user):
    """Test: Crear usuario con contraseñas que no coinciden debe fallar."""
    connection.set_schema_to_public()

    api_client.force_authenticate(user=staff_user)

    response = api_client.post(
        "/api/admin/v1/accounts/users/",
        {
            "email": "mismatch@example.com",
            "password": "Secr3tPass!",
            "password2": "OtherPass!",
        },
        format="json",
    )

    assert (
        response.status_code == status.HTTP_400_BAD_REQUEST
    ), f"Se esperaba 400, pero se recibió {response.status_code}"

    data = response.json()
    assert (
        "password2" in str(data) or "coinciden" in str(data).lower()
    ), f"El error debe mencionar que las contraseñas no coinciden. Respuesta: {data}"


def test_create_user_duplicate_email(api_client, staff_user):
    """Test: Crear usuario con email duplicado debe fallar."""
    connection.set_schema_to_public()

    # Crear usuario existente
    if hasattr(User, "username"):
        User.objects.create_user(
            email="dup@example.com", username="dupuser", password="test123"
        )
    else:
        User.objects.create_user(email="dup@example.com", password="test123")

    api_client.force_authenticate(user=staff_user)

    response = api_client.post(
        "/api/admin/v1/accounts/users/",
        {
            "email": "dup@example.com",
            "password": "Secr3tPass!",
            "password2": "Secr3tPass!",
        },
        format="json",
    )

    assert (
        response.status_code == status.HTTP_400_BAD_REQUEST
    ), f"Se esperaba 400, pero se recibió {response.status_code}"

    data = response.json()
    assert (
        "email" in str(data).lower()
        or "existente" in str(data).lower()
        or "duplicado" in str(data).lower()
    ), f"El error debe mencionar que el email ya existe. Respuesta: {data}"


def test_create_user_without_password2(api_client, staff_user):
    """Test: Crear usuario sin password2 debe fallar."""
    connection.set_schema_to_public()

    api_client.force_authenticate(user=staff_user)

    response = api_client.post(
        "/api/admin/v1/accounts/users/",
        {
            "email": "nopassword2@example.com",
            "password": "Secr3tPass!",
            # password2 faltante
        },
        format="json",
    )

    assert (
        response.status_code == status.HTTP_400_BAD_REQUEST
    ), f"Se esperaba 400, pero se recibió {response.status_code}"


def test_create_user_password_too_short(api_client, staff_user):
    """Test: Crear usuario con password muy corto debe fallar."""
    connection.set_schema_to_public()

    api_client.force_authenticate(user=staff_user)

    response = api_client.post(
        "/api/admin/v1/accounts/users/",
        {
            "email": "shortpass@example.com",
            "password": "Short1!",
            "password2": "Short1!",
        },
        format="json",
    )

    # Debe fallar porque el password tiene menos de 8 caracteres
    assert (
        response.status_code == status.HTTP_400_BAD_REQUEST
    ), f"Se esperaba 400, pero se recibió {response.status_code}"
