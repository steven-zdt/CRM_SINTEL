import pytest
from apps.public.tenants.models import Client, Domain, TenantMembership

@pytest.fixture
def tenant(db):
    """Fixture to provide a standard test tenant."""
    tenant_obj = Client.objects.filter(schema_name='testtenant').first()
    if not tenant_obj:
        tenant_obj = Client.objects.create(schema_name='testtenant', nombre='Test Tenant')
        Domain.objects.create(tenant=tenant_obj, domain='testtenant.sintel.com', is_primary=True)
    return tenant_obj

@pytest.fixture
def create_tenant(db):
    """Factory fixture to create tenants."""
    def _create(schema_name, nombre):
        tenant = Client.objects.filter(schema_name=schema_name).first()
        if not tenant:
            tenant = Client.objects.create(schema_name=schema_name, nombre=nombre)
            Domain.objects.create(tenant=tenant, domain=f"{schema_name}.sintel.com", is_primary=True)
        return tenant
    return _create

@pytest.fixture
def create_user(db, django_user_model):
    """Factory fixture to create users with tenant membership."""
    def _create(username, tenant):
        user = django_user_model.objects.create(username=username, email=f"{username}@example.com")
        TenantMembership.objects.create(client=tenant, user=user, is_active=True, rol="ADMIN")
        return user
    return _create
