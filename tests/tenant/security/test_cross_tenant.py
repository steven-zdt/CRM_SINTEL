"""
Tests de seguridad: Cross-Tenant Access.

Valida que usuarios con membresía en un tenant no puedan acceder a otro tenant.
"""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context

from apps.public.tenants.models import Client as TenantClient, Domain, TenantMembership

User = get_user_model()


@pytest.mark.django_db
def test_user_cannot_access_other_tenant_domain():
    """
    Usuario con membresía en A no accede a B (403/302 a login).
    """
    # Crear tenant A
    with schema_context('public'):
        tenant_a = TenantClient.objects.create(
            schema_name='tenant_a',
            nombre='Tenant A',
            is_active=True
        )
        domain_a = Domain.objects.create(
            tenant=tenant_a,
            domain='tenant-a.localhost',
            is_primary=True
        )
        
        # Crear tenant B
        tenant_b = TenantClient.objects.create(
            schema_name='tenant_b',
            nombre='Tenant B',
            is_active=True
        )
        domain_b = Domain.objects.create(
            tenant=tenant_b,
            domain='tenant-b.localhost',
            is_primary=True
        )
        
        # Crear usuario A con membresía solo en tenant A
        user_a = User.objects.create_user(
            email='user_a@test.com',
            password='testpass123'
        )
        TenantMembership.objects.create(
            client=tenant_a,
            user=user_a,
            is_active=True
        )
    
    # Intentar acceder a tenant B con credenciales de tenant A
    c = Client(HTTP_HOST=domain_b.domain)
    c.force_login(user_a)
    resp = c.get("/dashboard/")
    # Debe ser 302 (redirect a login) o 403 (forbidden)
    assert resp.status_code in (302, 403)


@pytest.mark.django_db
def test_user_can_access_own_tenant():
    """
    Usuario con membresía en tenant A puede acceder a tenant A.
    """
    # Crear tenant A
    with schema_context('public'):
        tenant_a = TenantClient.objects.create(
            schema_name='tenant_a',
            nombre='Tenant A',
            is_active=True
        )
        domain_a = Domain.objects.create(
            tenant=tenant_a,
            domain='tenant-a.localhost',
            is_primary=True
        )
        
        # Crear usuario A con membresía en tenant A
        user_a = User.objects.create_user(
            email='user_a@test.com',
            password='testpass123'
        )
        TenantMembership.objects.create(
            client=tenant_a,
            user=user_a,
            is_active=True
        )
    
    # Intentar acceder a tenant A con credenciales válidas
    c = Client(HTTP_HOST=domain_a.domain)
    c.force_login(user_a)
    resp = c.get("/dashboard/")
    # No debe ser 403 si tiene membresía activa
    assert resp.status_code != 403
