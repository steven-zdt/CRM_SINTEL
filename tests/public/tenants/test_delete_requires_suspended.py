"""
Tests para verificar que solo se pueden eliminar tenants suspendidos.

Verifica que:
- No se puede eliminar un tenant activo (is_active=True)
- Se debe desactivar primero (is_active=False) antes de eliminar
"""
import pytest
from django.db import connection
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.public.tenants.models import Client

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


@pytest.fixture
def active_tenant(db):
    """Tenant activo para tests."""
    connection.set_schema_to_public()
    return Client.objects.create(
        nombre="Test Tenant Activo",
        schema_name="test_active",
        is_active=True,
        on_trial=True
    )


@pytest.fixture
def suspended_tenant(db):
    """Tenant suspendido para tests."""
    connection.set_schema_to_public()
    return Client.objects.create(
        nombre="Test Tenant Suspendido",
        schema_name="test_suspended",
        is_active=False,
        on_trial=True
    )


def test_cannot_delete_active_tenant(api_client, staff_user, active_tenant):
    """Test: No se puede eliminar un tenant activo desde la API."""
    connection.set_schema_to_public()
    
    api_client.force_authenticate(user=staff_user)
    
    # Intentar eliminar un tenant activo debe retornar 400
    response = api_client.delete(f"/api/public/v1/tenants/{active_tenant.id}/")
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST, \
        f"Se esperaba 400, pero se recibió {response.status_code}"
    
    data = response.json()
    assert "is_active" in str(data.get("error", "")).lower() or "suspendido" in str(data.get("error", "")).lower(), \
        f"El mensaje de error debe mencionar is_active o suspendido. Error: {data}"


def test_service_forbids_active_delete(active_tenant):
    """Test: El servicio hard_delete_tenant rechaza eliminar un tenant activo."""
    connection.set_schema_to_public()
    from apps.public.tenants.services.deletion_service import hard_delete_tenant
    
    # Intentar eliminar un tenant activo debe lanzar ValidationError
    with pytest.raises(ValidationError) as exc_info:
        hard_delete_tenant(client_id=active_tenant.id, actor_user_id=None)
    
    error_msg = str(exc_info.value)
    assert "is_active" in error_msg.lower() or "suspendido" in error_msg.lower(), \
        f"El mensaje de error debe mencionar is_active o suspendido. Mensaje: {error_msg}"


def test_can_delete_suspended_tenant(api_client, staff_user, suspended_tenant):
    """Test: Se puede eliminar un tenant suspendido desde la API."""
    connection.set_schema_to_public()
    
    api_client.force_authenticate(user=staff_user)
    
    # Eliminar un tenant suspendido debe retornar 204
    response = api_client.delete(f"/api/public/v1/tenants/{suspended_tenant.id}/")
    
    # Puede ser 204 (No Content) o 200 con mensaje
    assert response.status_code in (status.HTTP_204_NO_CONTENT, status.HTTP_200_OK), \
        f"Se esperaba 204 o 200, pero se recibió {response.status_code}"
    
    # Verificar que el tenant fue eliminado
    assert not Client.objects.filter(id=suspended_tenant.id).exists(), \
        "El tenant suspendido debería haber sido eliminado"
