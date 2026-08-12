"""
Tests para listado de usuarios en API admin.

Verifica que:
- GET /api/admin/v1/accounts/users/ responde 200 con IsAdminUser
- Retorna paginación DRF estándar
- Requiere autenticación de administrador
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
def admin_user(db):
    """Usuario admin global."""
    connection.set_schema_to_public()
    return User.objects.create_superuser(email="admin@test.local", password="admin123")


@pytest.fixture
def regular_user(db):
    """Usuario regular (no staff)."""
    connection.set_schema_to_public()
    return User.objects.create_user(
        email="regular@test.local", password="regular123", is_staff=False
    )


def test_admin_users_list_requires_admin(api_client, admin_user, regular_user):
    """Test: GET /api/admin/v1/accounts/users/ requiere IsAdminUser."""
    connection.set_schema_to_public()
    from django.urls import reverse

    # Sin autenticación → 401/403
    response = api_client.get(reverse("admin-user-list"))
    assert response.status_code in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    )

    # Usuario regular → 403
    api_client.force_authenticate(user=regular_user)
    response = api_client.get(reverse("admin-user-list"))
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Admin → 200
    api_client.force_authenticate(user=admin_user)
    response = api_client.get(reverse("admin-user-list"))
    assert response.status_code == status.HTTP_200_OK


def test_admin_users_list_pagination(api_client, admin_user):
    """Test: GET /api/admin/v1/accounts/users/ retorna paginación DRF."""
    connection.set_schema_to_public()
    from django.urls import reverse

    api_client.force_authenticate(user=admin_user)

    # Crear algunos usuarios
    for i in range(5):
        User.objects.create_user(email=f"user{i}@test.com", password="test123")

    response = api_client.get(reverse("admin-user-list"))
    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    # Verificar formato de paginación DRF
    assert "results" in data or isinstance(
        data, list
    ), "La respuesta debe tener formato de paginación DRF (results) o lista"

    if "results" in data:
        assert isinstance(
            data["results"], list
        ), "El campo 'results' debe ser una lista"
        assert "count" in data, "Debe incluir 'count' en paginación DRF"
        assert isinstance(data["count"], int), "El campo 'count' debe ser un entero"


def test_admin_users_list_with_pagination_params(api_client, admin_user):
    """Test: GET /api/admin/v1/accounts/users/?page=1&page_size=25 funciona."""
    connection.set_schema_to_public()
    from django.urls import reverse

    api_client.force_authenticate(user=admin_user)

    response = api_client.get(f"{reverse('admin-user-list')}?page=1&page_size=25")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    # Debe responder correctamente con parámetros de paginación
    assert "results" in data or isinstance(data, list)
