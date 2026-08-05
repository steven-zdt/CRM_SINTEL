"""
Tests completos para hard delete de tenants.

Verifica:
- No permite borrar public
- Requiere is_active=False
- 204 en caso exitoso y el schema no existe luego
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.utils import schema_exists
from rest_framework import status

from apps.public.tenants.models import Client, Domain, TenantMembership

User = get_user_model()


@pytest.fixture
def staff_user(db):
    """Usuario staff para tests."""
    connection.set_schema_to_public()
    return User.objects.create_user(
        email="staff@test.local",
        password="testpass123",
        is_staff=True,
        is_superuser=False,
    )


@pytest.fixture
def suspended_tenant(db, staff_user):
    """Tenant suspendido para tests de eliminación."""
    connection.set_schema_to_public()

    tenant = Client.objects.create(
        nombre="Test Tenant Para Eliminar",
        schema_name="test_delete_me",
        is_active=False,  # [WARNING] CRÍTICO: Debe estar suspendido
        on_trial=True,
    )

    Domain.objects.create(
        tenant=tenant, domain="test-delete-me.localhost", is_primary=True
    )

    TenantMembership.objects.create(
        client=tenant,
        user=staff_user,
        rol="ADMIN",
        is_primary_admin=True,
        is_active=True,
    )

    return tenant


@pytest.mark.django_db
def test_hard_delete_forbids_public_tenant(api_client, staff_user):
    """
    Test: Hard delete no permite borrar el tenant público.

    Objetivo: Verificar que se rechaza la eliminación del tenant público (schema='public').
    """
    connection.set_schema_to_public()
    api_client.force_authenticate(user=staff_user)

    # Obtener o crear el tenant público
    public_tenant, _ = Client.objects.get_or_create(
        schema_name="public", defaults={"nombre": "Tenant Público", "is_active": True}
    )

    # Intentar eliminar el tenant público
    response = api_client.delete(f"/api/public/v1/tenants/{public_tenant.id}/")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    assert "público" in str(data).lower() or "public" in str(data).lower()


@pytest.mark.django_db
def test_hard_delete_requires_suspended_tenant(api_client, staff_user):
    """
    Test: Hard delete requiere que el tenant esté suspendido (is_active=False).

    Objetivo: Verificar que se rechaza la eliminación de tenants activos.
    """
    connection.set_schema_to_public()
    api_client.force_authenticate(user=staff_user)

    # Crear tenant activo
    active_tenant = Client.objects.create(
        nombre="Tenant Activo",
        schema_name="active_tenant",
        is_active=True,  # [WARNING] Activo (no puede eliminarse)
        on_trial=True,
    )

    Domain.objects.create(
        tenant=active_tenant, domain="active.localhost", is_primary=True
    )

    # Intentar eliminar tenant activo
    response = api_client.delete(f"/api/public/v1/tenants/{active_tenant.id}/")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "is_active" in str(data).lower() or "suspendido" in str(data).lower()


@pytest.mark.django_db
def test_hard_delete_success_and_schema_dropped(
    api_client, staff_user, suspended_tenant
):
    """
    Test: Hard delete exitoso elimina el schema y retorna 204.

    Objetivo: Verificar que:
    - Se retorna 204 No Content
    - El schema PostgreSQL no existe después de la eliminación
    - El Client, Domain y TenantMembership se eliminan del esquema public
    """
    connection.set_schema_to_public()
    api_client.force_authenticate(user=staff_user)

    schema_name = suspended_tenant.schema_name
    tenant_id = suspended_tenant.id

    # Verificar que el schema existe antes de eliminar
    assert schema_exists(
        schema_name
    ), f"El schema '{schema_name}' debe existir antes de eliminarlo"

    # Verificar que el Client existe
    assert Client.objects.filter(id=tenant_id).exists()

    # Ejecutar hard delete
    response = api_client.delete(f"/api/public/v1/tenants/{tenant_id}/")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verificar que el Client fue eliminado
    assert not Client.objects.filter(
        id=tenant_id
    ).exists(), "El Client debe eliminarse del esquema public"

    # Verificar que el Domain fue eliminado (CASCADE)
    assert not Domain.objects.filter(
        tenant_id=tenant_id
    ).exists(), "El Domain debe eliminarse (CASCADE)"

    # Verificar que el TenantMembership fue eliminado (CASCADE)
    assert not TenantMembership.objects.filter(
        client_id=tenant_id
    ).exists(), "El TenantMembership debe eliminarse (CASCADE)"

    # Verificar que el schema PostgreSQL fue eliminado
    assert not schema_exists(
        schema_name
    ), f"El schema '{schema_name}' debe eliminarse (drop schema)"


@pytest.mark.django_db
def test_hard_delete_requires_staff_permission(api_client, django_user_model):
    """
    Test: Hard delete requiere permisos de staff (IsAdminUser).

    Objetivo: Verificar que usuarios no-staff reciben 403 al intentar eliminar tenants.
    """
    connection.set_schema_to_public()

    # Crear usuario no-staff
    regular_user = django_user_model.objects.create_user(
        email="regular@test.local",
        password="testpass123",
        is_staff=False,
        is_superuser=False,
    )

    # Crear tenant suspendido
    tenant = Client.objects.create(
        nombre="Test Tenant", schema_name="test_tenant", is_active=False, on_trial=True
    )

    api_client.force_authenticate(user=regular_user)

    response = api_client.delete(f"/api/public/v1/tenants/{tenant.id}/")

    assert response.status_code == status.HTTP_403_FORBIDDEN
