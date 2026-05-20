"""
Pytest fixtures for ContactoCliente tests.

Provides fixtures for multi-tenant tests.
"""
import pytest
from django.core.management import call_command
from django.db import connection
from django_tenants.utils import schema_context

from apps.public.tenants.models import Client, Domain
from apps.tenant.empresa.models import Empresa


@pytest.fixture
def tenant(db):
    """
    Simple fixture that returns an existing test tenant.
    
    For multi-tenant tests, this works with pytest.mark.django_db
    which automatically creates the test database and schemas.
    """
    # Prefer a non-public tenant schema if available.
    tenant_obj = (
        Client.objects.exclude(schema_name='public')
        .exclude(schema_name__contains='_')
        .only('id', 'schema_name', 'nombre')
        .first()
    )
    if tenant_obj:
        schema = tenant_obj.schema_name
    else:
        # Use RFC-valid schema name for HTTP_HOST based tests.
        schema = 'testtenant'
        tenant_obj = Client.objects.filter(schema_name=schema).only('id', 'schema_name', 'nombre').first()
        if not tenant_obj:
            with schema_context('public'):
                tenant_obj = Client(
                    schema_name=schema,
                    nombre='Test Tenant'
                )
                tenant_obj.auto_create_schema = False
                tenant_obj.save(force_insert=True)

    # Ensure domain exists for host-based tests.
    Domain.objects.get_or_create(
        tenant=tenant_obj,
        domain=f'{tenant_obj.schema_name}.sintel.com',
        defaults={'is_primary': True},
    )

    # Ensure schema exists and required app tables are present.
    with connection.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS {tenant_obj.schema_name}')

    with schema_context(tenant_obj.schema_name):
        tables = set(connection.introspection.table_names())

    if 'empresa_empresa' not in tables:
        # Migrate only required apps for this test module to avoid unrelated migration failures.
        call_command('migrate_schemas', '--tenant', '-s', tenant_obj.schema_name, 'empresa', '--noinput', verbosity=0)

    with schema_context(tenant_obj.schema_name):
        tables = set(connection.introspection.table_names())

    if 'clientes_cliente' not in tables:
        call_command('migrate_schemas', '--tenant', '-s', tenant_obj.schema_name, 'tenant_clientes', '--noinput', verbosity=0)

    with schema_context(tenant_obj.schema_name):
        tables = set(connection.introspection.table_names())

    if 'perfil_tenantprofile' not in tables:
        call_command('migrate_schemas', '--tenant', '-s', tenant_obj.schema_name, 'perfil', '--noinput', verbosity=0)

    # Ensure singleton Empresa exists with valid current model fields.
    with schema_context(tenant_obj.schema_name):
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            Empresa.objects.create(
                razon_social='EMPRESA TEST S.A.S.',
                nit='901234567',
                direccion='Direccion de prueba',
                telefono='3000000000',
            )

    return tenant_obj


@pytest.fixture
def tenant_with_empresa(tenant):
    """
    Creates a test tenant with default Empresa.
    
    Returns:
        Dict with:
        - tenant: Client instance
        - empresa: Empresa instance in the tenant schema
    
    Usage:
        def test_something(tenant_with_empresa):
            tenant = tenant_with_empresa['tenant']
            empresa = tenant_with_empresa['empresa']
            with schema_context(tenant.schema_name):
                # Use empresa directly
    """
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        if not empresa:
            empresa = Empresa.objects.create(
                nombre="Empresa Test",
                razon_social="EMPRESA TEST S.A.S.",
                nit="901234567"
            )
    
    return {
        'tenant': tenant,
        'empresa': empresa
    }


@pytest.fixture
def admin_user(db, tenant):
    """Fixture que crea un usuario administrador con membresia y perfil en el tenant."""
    from django.contrib.auth import get_user_model
    from apps.public.tenants.models import TenantMembership
    from apps.tenant.perfil.models import TenantProfile
    
    User = get_user_model()
    # Check if user already exists
    user = User.objects.filter(email="admin@test.local").first()
    if not user:
        user = User.objects.create_superuser(
            username="admin_test",
            email="admin@test.local",
            password="admin123"
        )
    
    # Ensure TenantMembership exists
    TenantMembership.objects.get_or_create(
        client=tenant,
        user=user,
        defaults={'is_active': True, 'rol': 'ADMIN'}
    )
    
    # Ensure TenantProfile exists
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        TenantProfile.objects.get_or_create(
            user=user,
            empresa=empresa,
            defaults={'rol': 'ADMIN'}
        )
        
    return user
