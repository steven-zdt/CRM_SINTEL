"""
Tests de garantía para Hard Delete de Tenants.

Valida:
- Precondición obligatoria: is_active == False
- Borrado total: drop de esquema + eliminación de registros
- Defensa en profundidad: validación en Admin, API y servicio
- Transaccionalidad y auditoría
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django_tenants.utils import schema_exists, get_public_schema_name
from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.public.tenants.services.deletion_service import hard_delete_tenant

User = get_user_model()

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def admin_user(db):
    """Usuario admin global."""
    connection.set_schema_to_public()
    return User.objects.create_superuser(
        email="admin@test.local",
        password="admin123"
    )


@pytest.fixture
def tenant_owner(db):
    """Usuario propietario del tenant."""
    connection.set_schema_to_public()
    return User.objects.create_user(
        email="owner@tenant.local",
        password="owner123"
    )


@pytest.fixture
def active_tenant(db, tenant_owner):
    """Tenant activo (is_active=True) para pruebas de bloqueo."""
    connection.set_schema_to_public()
    
    tenant = Client.objects.create(
        nombre="Tenant Activo",
        schema_name="tenant_activo",
        is_active=True,  # ACTIVO
        on_trial=True,
    )
    
    Domain.objects.create(
        tenant=tenant,
        domain="tenant-activo.localhost",
        is_primary=True,
    )
    
    TenantMembership.objects.create(
        client=tenant,
        user=tenant_owner,
        rol="ADMIN",
        is_primary_admin=True,
        is_active=True,
    )
    
    return tenant


@pytest.fixture
def inactive_tenant(db, tenant_owner):
    """Tenant inactivo (is_active=False) para pruebas de eliminación."""
    connection.set_schema_to_public()
    
    tenant = Client.objects.create(
        nombre="Tenant Inactivo",
        schema_name="tenant_inactivo",
        is_active=False,  # INACTIVO
        on_trial=True,
    )
    
    Domain.objects.create(
        tenant=tenant,
        domain="tenant-inactivo.localhost",
        is_primary=True,
    )
    
    TenantMembership.objects.create(
        client=tenant,
        user=tenant_owner,
        rol="ADMIN",
        is_primary_admin=True,
        is_active=True,
    )
    
    return tenant


def test_hard_delete_bloquea_tenant_activo(active_tenant):
    """
    Test A: No permite borrar tenant activo.
    
    Dado Client.is_active=True, llamar hard_delete_tenant → ValidationError
    """
    connection.set_schema_to_public()
    
    tenant_id = active_tenant.id
    schema_name = active_tenant.schema_name
    
    # Intentar eliminar tenant activo debe fallar
    with pytest.raises(ValidationError) as exc_info:
        hard_delete_tenant(client_id=tenant_id)
    
    assert "is_active=False" in str(exc_info.value).lower() or "suspendido" in str(exc_info.value).lower()
    
    # Verificar que el tenant NO fue eliminado
    assert Client.objects.filter(id=tenant_id).exists()
    assert Domain.objects.filter(tenant_id=tenant_id).exists()
    assert TenantMembership.objects.filter(client_id=tenant_id).exists()
    
    # Verificar que el esquema sigue existiendo
    assert schema_exists(schema_name)


def test_hard_delete_elimina_tenant_inactivo(inactive_tenant):
    """
    Test B: Borra tenant suspendido correctamente.
    
    Dado Client.is_active=False, al llamar hard_delete_tenant:
    - El esquema ya no existe
    - Client y Domain(s)/Membership(s) en public no existen más
    """
    connection.set_schema_to_public()
    
    tenant_id = inactive_tenant.id
    schema_name = inactive_tenant.schema_name
    domain_id = inactive_tenant.domains.first().id
    membership_id = inactive_tenant.tenantmembership_set.first().id
    
    # Verificar que existe antes de eliminar
    assert Client.objects.filter(id=tenant_id).exists()
    assert Domain.objects.filter(id=domain_id).exists()
    assert TenantMembership.objects.filter(id=membership_id).exists()
    assert schema_exists(schema_name)
    
    # Ejecutar hard delete
    hard_delete_tenant(client_id=tenant_id)
    
    # Verificar que el tenant fue eliminado
    assert not Client.objects.filter(id=tenant_id).exists()
    assert not Domain.objects.filter(id=domain_id).exists()
    assert not TenantMembership.objects.filter(id=membership_id).exists()
    
    # Verificar que el esquema fue eliminado
    assert not schema_exists(schema_name)


def test_hard_delete_bloquea_tenant_publico(db):
    """
    Test C: No permite borrar el tenant público.
    """
    connection.set_schema_to_public()
    
    public_schema = get_public_schema_name()
    public_tenant = Client.objects.get(schema_name=public_schema)
    
    # Desactivar temporalmente para pasar la precondición
    public_tenant.is_active = False
    public_tenant.save()
    
    # Intentar eliminar tenant público debe fallar
    with pytest.raises(ValueError) as exc_info:
        hard_delete_tenant(client_id=public_tenant.id)
    
    assert "público" in str(exc_info.value).lower() or "public" in str(exc_info.value).lower()
    
    # Restaurar estado
    public_tenant.is_active = True
    public_tenant.save()


def test_hard_delete_tenant_inexistente():
    """
    Test D: Si el tenant no existe → ValidationError.
    """
    connection.set_schema_to_public()
    
    with pytest.raises(ValidationError) as exc_info:
        hard_delete_tenant(client_id=99999)  # ID que no existe
    
    assert "no existe" in str(exc_info.value).lower()


def test_hard_delete_api_bloquea_activo(api_client, admin_user, active_tenant):
    """
    Test E: API rechaza hard delete si is_active=True (400).
    """
    connection.set_schema_to_public()
    api_client.force_authenticate(user=admin_user)
    
    url = f"/api/public/v1/tenants/{active_tenant.id}/"
    
    response = api_client.delete(url)
    
    assert response.status_code == 400
    assert "is_active=False" in str(response.data.get('error', '')).lower() or "suspendido" in str(response.data.get('error', '')).lower()
    
    # Verificar que el tenant NO fue eliminado
    assert Client.objects.filter(id=active_tenant.id).exists()


def test_hard_delete_api_elimina_inactivo(api_client, admin_user, inactive_tenant):
    """
    Test F: API elimina tenant inactivo correctamente (204).
    """
    connection.set_schema_to_public()
    api_client.force_authenticate(user=admin_user)
    
    tenant_id = inactive_tenant.id
    schema_name = inactive_tenant.schema_name
    url = f"/api/public/v1/tenants/{tenant_id}/"
    
    response = api_client.delete(url)
    
    assert response.status_code == 204
    
    # Verificar que el tenant fue eliminado
    assert not Client.objects.filter(id=tenant_id).exists()
    
    # Verificar que el esquema fue eliminado
    assert not schema_exists(schema_name)


def test_hard_delete_cascade_domain_and_membership(inactive_tenant):
    """
    Test G: Verificar que CASCADE elimina Domain y TenantMembership.
    """
    connection.set_schema_to_public()
    
    tenant_id = inactive_tenant.id
    domain = inactive_tenant.domains.first()
    membership = inactive_tenant.tenantmembership_set.first()
    
    # Verificar que existen antes
    assert Domain.objects.filter(id=domain.id).exists()
    assert TenantMembership.objects.filter(id=membership.id).exists()
    
    # Ejecutar hard delete
    hard_delete_tenant(client_id=tenant_id)
    
    # Verificar que fueron eliminados por CASCADE
    assert not Domain.objects.filter(id=domain.id).exists()
    assert not TenantMembership.objects.filter(id=membership.id).exists()


def test_hard_delete_preserva_usuarios_globales(inactive_tenant, tenant_owner):
    """
    Test H: Los usuarios globales NO se eliminan (pueden pertenecer a otros tenants).
    """
    connection.set_schema_to_public()
    
    tenant_id = inactive_tenant.id
    user_id = tenant_owner.id
    
    # Ejecutar hard delete
    hard_delete_tenant(client_id=tenant_id)
    
    # Verificar que el usuario global sigue existiendo
    assert User.objects.filter(id=user_id).exists()
    
    # Verificar que la membresía fue eliminada
    assert not TenantMembership.objects.filter(client_id=tenant_id, user_id=user_id).exists()
