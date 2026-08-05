"""
Pytest fixtures for Empleados tests.
"""
import pytest
from django.core.management import call_command
from django.db import connection
from django_tenants.utils import schema_context, get_public_schema_name

from apps.public.tenants.models import Client, Domain
from apps.tenant.empresa.models import Empresa


@pytest.fixture
def tenant(db):
    """
    Simple fixture that returns an existing test tenant.
    """
    tenant_obj = (
        Client.objects.exclude(schema_name='public')
        .exclude(schema_name__contains='_')
        .only('id', 'schema_name', 'nombre')
        .first()
    )
    if tenant_obj:
        schema = tenant_obj.schema_name
    else:
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

    Domain.objects.get_or_create(
        tenant=tenant_obj,
        domain=f'{tenant_obj.schema_name}.sintel.net.co',
        defaults={'is_primary': True},
    )

    with connection.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS {tenant_obj.schema_name}')

    with schema_context(tenant_obj.schema_name):
        tables = set(connection.introspection.table_names())

    if 'empresa_empresa' not in tables:
        call_command('migrate_schemas', '--tenant', '-s', tenant_obj.schema_name, 'empresa', '--noinput', verbosity=0)

    with schema_context(tenant_obj.schema_name):
        tables = set(connection.introspection.table_names())

    if 'empleados_empleado' not in tables:
        call_command('migrate_schemas', '--tenant', '-s', tenant_obj.schema_name, 'tenant_empleados', '--noinput', verbosity=0)

    with schema_context(tenant_obj.schema_name):
        tables = set(connection.introspection.table_names())

    if 'perfil_tenantprofile' not in tables:
        call_command('migrate_schemas', '--tenant', '-s', tenant_obj.schema_name, 'perfil', '--noinput', verbosity=0)

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
def admin_user(db, tenant):
    """Fixture que crea un usuario administrador con membresia y perfil en el tenant."""
    from django.contrib.auth import get_user_model
    from apps.public.tenants.models import TenantMembership
    from apps.tenant.perfil.models import TenantProfile
    
    User = get_user_model()
    user = User.objects.filter(email="admin@test.local").first()
    if not user:
        user = User.objects.create_superuser(
            username="admin_test",
            email="admin@test.local",
            password="admin123"
        )
    
    TenantMembership.objects.get_or_create(
        client=tenant,
        user=user,
        defaults={'is_active': True, 'rol': 'ADMIN'}
    )
    
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        TenantProfile.objects.get_or_create(
            user=user,
            empresa=empresa,
            defaults={'rol': 'ADMIN'}
        )
        
    return user


@pytest.fixture
def tenant_factory():
    """
    Fixture factory para crear tenants de prueba.
    """
    def _factory(**kwargs):
        schema_name = kwargs.pop('schema_name', None)
        if not schema_name:
            raise ValueError("schema_name es requerido")
        
        with schema_context(get_public_schema_name()):
            tenant = Client.objects.filter(schema_name=schema_name).first()
            if tenant:
                for key, value in kwargs.items():
                    if hasattr(tenant, key):
                        setattr(tenant, key, value)
                tenant.save()
            else:
                tenant = Client(schema_name=schema_name, **kwargs)
                tenant.save()  # django-tenants creará el schema automáticamente
            
            # Crear dominio para el nuevo tenant
            Domain.objects.get_or_create(
                tenant=tenant,
                domain=f'{schema_name}.sintel.net.co',
                defaults={'is_primary': True},
            )
            
        return tenant
    return _factory


# Fixtures canonicas tenant1/tenant2 (AGENTS.md §24.5), mismo patron usado en
# apps/tenant/gastos/tests/conftest.py y el resto de apps migradas en Fase 5-BIS.

@pytest.fixture
def tenant1(db):
    schema = 'tenant1'
    tenant_obj = Client.objects.filter(schema_name=schema).first()
    if not tenant_obj:
        with schema_context('public'):
            tenant_obj = Client.objects.create(schema_name=schema, nombre='Tenant 1')
            Domain.objects.create(tenant=tenant_obj, domain=f'{schema}.sintel.net.co', is_primary=True)

    with connection.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS {schema}')

    call_command('migrate_schemas', '--tenant', '-s', schema, '--noinput', verbosity=0)

    with schema_context(schema):
        if not Empresa.objects.exists():
            Empresa.objects.create(nit="111", razon_social="Empresa 1 SAS", direccion="Calle 1")

    return tenant_obj


@pytest.fixture
def tenant2(db):
    schema = 'tenant2'
    tenant_obj = Client.objects.filter(schema_name=schema).first()
    if not tenant_obj:
        with schema_context('public'):
            tenant_obj = Client.objects.create(schema_name=schema, nombre='Tenant 2')
            Domain.objects.create(tenant=tenant_obj, domain=f'{schema}.sintel.net.co', is_primary=True)

    with connection.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS {schema}')

    call_command('migrate_schemas', '--tenant', '-s', schema, '--noinput', verbosity=0)

    with schema_context(schema):
        if not Empresa.objects.exists():
            Empresa.objects.create(nit="222", razon_social="Empresa 2 SAS", direccion="Calle 2")

    return tenant_obj
