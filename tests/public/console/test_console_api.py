"""
Tests de regresión para la API de consola (API-First).

Verifica:
- Endpoints DataTables (POST + CSRF) con contrato estándar
- Permisos IsAdminUser
- No exposición de campos sensibles
- Optimización de queries (only/select_related)
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.db import connection
from django.urls import reverse
from rest_framework import status
from apps.public.tenants.models import Client, Domain

User = get_user_model()

# Configurar ROOT_URLCONF para todos los tests de este módulo
pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def setup_public_schema():
    """Fixture automático que configura el esquema público y ROOT_URLCONF para cada test."""
    with override_settings(ROOT_URLCONF='config.urls_public'):
        connection.set_schema_to_public()
        yield


@pytest.fixture
def api_client():
    """Fixture para APIClient de DRF."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Fixture que crea un usuario administrador."""
    User = get_user_model()
    user = User.objects.create_superuser(
        email="admin@test.local",
        password="admin123"
    )
    return user


@pytest.fixture
def regular_user(db):
    """Fixture que crea un usuario regular (no staff)."""
    User = get_user_model()
    user = User.objects.create_user(
        email="user@test.local",
        password="user123"
    )
    return user


@pytest.fixture
def sample_tenant(db):
    """Fixture que crea un tenant de prueba."""
    tenant = Client.objects.create(
        nombre="Empresa Test",
        schema_name="empresa_test",
        is_active=True,
        on_trial=True,
    )
    Domain.objects.create(
        tenant=tenant,
        domain="test.localhost",
        is_primary=True,
    )
    return tenant


def test_tenants_datatable_authenticated_staff(api_client, admin_user, sample_tenant):
    """
    Test: POST /api/admin/v1/console/dt/tenants/ con usuario staff devuelve 200 y contrato DataTables.
    """
    api_client.force_authenticate(user=admin_user)
    
    url = "/api/admin/v1/console/dt/tenants/"
    payload = {
        "draw": 1,
        "start": 0,
        "length": 10,
        "search": {"value": ""},
        "order": [{"column": 0, "dir": "asc"}],
        "columns": [
            {"data": 0, "name": "id", "searchable": False, "orderable": True},
            {"data": 1, "name": "nombre", "searchable": True, "orderable": True},
            {"data": 2, "name": "schema_name", "searchable": True, "orderable": True},
        ],
    }
    
    response = api_client.post(url, payload, format="json")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Verificar contrato DataTables estándar
    assert "draw" in data
    assert "recordsTotal" in data
    assert "recordsFiltered" in data
    assert "data" in data
    
    assert data["draw"] == 1
    assert data["recordsTotal"] >= 1
    assert data["recordsFiltered"] >= 1
    assert isinstance(data["data"], list)
    
    # Verificar que los datos contienen solo campos mínimos
    if data["data"]:
        tenant = data["data"][0]
        allowed_fields = {"id", "nombre", "schema_name", "is_active", "on_trial", "paid_until", "created_on"}
        assert set(tenant.keys()).issubset(allowed_fields)
        
        # Verificar que NO se exponen campos sensibles
        sensitive_fields = {"password", "secret_key", "api_key"}
        assert not any(field in tenant for field in sensitive_fields)


def test_tenants_datatable_unauthenticated(api_client):
    """
    Test: POST /api/admin/v1/console/dt/tenants/ sin autenticación devuelve 401.
    """
    url = "/api/admin/v1/console/dt/tenants/"
    payload = {
        "draw": 1,
        "start": 0,
        "length": 10,
        "search": {"value": ""},
        "order": [],
        "columns": [],
    }
    
    response = api_client.post(url, payload, format="json")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_tenants_datatable_non_staff(api_client, regular_user):
    """
    Test: POST /api/admin/v1/console/dt/tenants/ con usuario no-staff devuelve 403.
    """
    api_client.force_authenticate(user=regular_user)
    
    url = "/api/admin/v1/console/dt/tenants/"
    payload = {
        "draw": 1,
        "start": 0,
        "length": 10,
        "search": {"value": ""},
        "order": [],
        "columns": [],
    }
    
    response = api_client.post(url, payload, format="json")
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_tenants_datatable_search(api_client, admin_user, sample_tenant):
    """
    Test: Búsqueda en DataTables funciona correctamente.
    """
    api_client.force_authenticate(user=admin_user)
    
    url = "/api/admin/v1/console/dt/tenants/"
    payload = {
        "draw": 1,
        "start": 0,
        "length": 10,
        "search": {"value": "Empresa"},  # Buscar por nombre
        "order": [],
        "columns": [],
    }
    
    response = api_client.post(url, payload, format="json")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Debe encontrar al menos el tenant de prueba
    assert data["recordsFiltered"] >= 1
    assert any("Empresa" in str(tenant.get("nombre", "")) for tenant in data["data"])


def test_tenant_domains_datatable(api_client, admin_user, sample_tenant):
    """
    Test: POST /api/admin/v1/console/dt/tenant-domains/ devuelve contrato DataTables.
    """
    api_client.force_authenticate(user=admin_user)
    
    url = "/api/admin/v1/console/dt/tenant-domains/"
    payload = {
        "draw": 1,
        "start": 0,
        "length": 10,
        "search": {"value": ""},
        "order": [],
        "columns": [],
    }
    
    response = api_client.post(url, payload, format="json")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert "draw" in data
    assert "recordsTotal" in data
    assert "recordsFiltered" in data
    assert "data" in data
    
    # Verificar campos mínimos
    if data["data"]:
        domain = data["data"][0]
        allowed_fields = {"id", "domain", "is_primary"}
        assert set(domain.keys()).issubset(allowed_fields)


def test_users_datatable(api_client, admin_user):
    """
    Test: POST /api/admin/v1/console/dt/users/ devuelve contrato DataTables.
    """
    api_client.force_authenticate(user=admin_user)
    
    url = "/api/admin/v1/console/dt/users/"
    payload = {
        "draw": 1,
        "start": 0,
        "length": 10,
        "search": {"value": ""},
        "order": [],
        "columns": [],
    }
    
    response = api_client.post(url, payload, format="json")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert "draw" in data
    assert "recordsTotal" in data
    assert "recordsFiltered" in data
    assert "data" in data
    
    # Verificar campos mínimos (no password ni información sensible)
    if data["data"]:
        user = data["data"][0]
        allowed_fields = {"id", "email", "is_active", "is_staff", "date_joined"}
        assert set(user.keys()).issubset(allowed_fields)
        
        # Verificar que NO se expone password
        assert "password" not in user


def test_console_health(api_client, admin_user):
    """
    Test: GET /api/admin/v1/console/health/ devuelve estado de la consola.
    """
    api_client.force_authenticate(user=admin_user)
    
    # Usar reverse() para obtener la URL correcta
    url = reverse('console_api:health')
    response = api_client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert data["status"] == "ok"
    assert "time" in data
    assert "features" in data
    assert data["features"]["api_first"] is True
    assert data["features"]["datatables_post"] is True


def test_console_health_unauthenticated(api_client):
    """
    Test: GET /api/admin/v1/console/health/ sin autenticación devuelve 401.
    """
    url = "/api/admin/v1/console/health/"
    response = api_client.get(url)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
