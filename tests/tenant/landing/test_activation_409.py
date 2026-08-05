"""
Tests de seguridad: Activación duplicada (409 Conflict).

Valida que la activación retorne 409 si el usuario ya tiene contraseña usable.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django_tenants.utils import schema_context

from apps.public.tenants.models import Client as TenantClient
from apps.public.tenants.models import Domain, TenantMembership
from apps.public.tenants.services.invitations import generate_invitation_token

User = get_user_model()


@pytest.fixture
def create_tenant_with_owner(db):
    """
    Fixture que crea un tenant con owner para tests de activación.
    """

    def _create_tenant_with_owner(schema_name="test_tenant", domain="test.localhost"):
        with schema_context("public"):
            tenant = TenantClient.objects.create(
                schema_name=schema_name,
                nombre=f"Test Tenant - {schema_name}",
                is_active=True,
            )
            domain_obj = Domain.objects.create(
                tenant=tenant, domain=domain, is_primary=True
            )
            owner = User.objects.create_user(
                email=f"owner@{schema_name}.com", password=None  # Sin password inicial
            )
            owner.set_unusable_password()  # [WARNING] Sin password usable
            owner.save()

            TenantMembership.objects.create(client=tenant, user=owner, is_active=True)

            return tenant, owner, domain_obj

    return _create_tenant_with_owner


@pytest.mark.django_db
def test_activation_returns_409_if_already_usable(create_tenant_with_owner):
    """
    La activación debe retornar 409 si el usuario ya tiene contraseña usable.
    """
    tenant, owner, domain = create_tenant_with_owner()

    # Simular usuario ya activado
    owner.set_password("Secret123!")
    owner.save(update_fields=["password"])

    # Generar token de activación
    token = generate_invitation_token(owner.id, tenant.id)

    # Intentar activar con token
    c = Client(HTTP_HOST=domain.domain)
    resp = c.get(f"/api/v1/landing/auth/activate/?token={token}")

    # Debe retornar 409 CONFLICT
    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}"
    data = resp.json()
    assert "activada" in data["detail"].lower() or "activa" in data["detail"].lower()
