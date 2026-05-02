"""
Tests para DataTables de usuarios en la consola.

Verifica que:
- POST /api/admin/v1/console/dt/users/ responde 200
- Retorna el contrato DataTables estándar
- Requiere IsAdminUser
"""
import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.urls('config.urls_public'),
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
        email="staff@test.local",
        password="staff123",
        is_staff=True,
        is_active=True
    )


def test_console_dt_users_ok(api_client, staff_user):
    """Test: POST /api/admin/v1/console/dt/users/ responde 200 con contrato DataTables."""
    connection.set_schema_to_public()
    
    # Sin autenticación → 401/403
    response = api_client.post(
        "/api/admin/v1/console/dt/users/",
        {"draw": 1, "start": 0, "length": 10},
        format="json"
    )
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    
    # Con autenticación staff → 200
    api_client.force_authenticate(user=staff_user)
    response = api_client.post(
        "/api/admin/v1/console/dt/users/",
        {
            "draw": 1,
            "start": 0,
            "length": 10,
            "search": {"value": ""},
            "order": [{"column": 0, "dir": "asc"}],
            "columns": []
        },
        format="json"
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Verificar contrato DataTables estándar
    assert set(data.keys()) == {"draw", "recordsTotal", "recordsFiltered", "data"}, \
        f"La respuesta debe tener el contrato DataTables. Keys: {data.keys()}"
    
    assert isinstance(data["data"], list), "El campo 'data' debe ser una lista"
    assert isinstance(data["recordsTotal"], int), "El campo 'recordsTotal' debe ser un entero"
    assert isinstance(data["recordsFiltered"], int), "El campo 'recordsFiltered' debe ser un entero"
    assert data["draw"] == 1, "El campo 'draw' debe coincidir con el request"
