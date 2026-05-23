import pytest
from django.core.management import call_command
from django.db import connection
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client, Domain
from apps.tenant.empresa.models import Empresa

@pytest.fixture
def tenant1(db):
    schema = 'tenant1'
    tenant_obj = Client.objects.filter(schema_name=schema).first()
    if not tenant_obj:
        with schema_context('public'):
            tenant_obj = Client.objects.create(schema_name=schema, nombre='Tenant 1')
            Domain.objects.create(tenant=tenant_obj, domain=f'{schema}.sintel.com', is_primary=True)

    # Ensure schema and tables
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
            Domain.objects.create(tenant=tenant_obj, domain=f'{schema}.sintel.com', is_primary=True)

    # Ensure schema and tables
    with connection.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS {schema}')

    call_command('migrate_schemas', '--tenant', '-s', schema, '--noinput', verbosity=0)

    with schema_context(schema):
        if not Empresa.objects.exists():
            Empresa.objects.create(nit="222", razon_social="Empresa 2 SAS", direccion="Calle 2")

    return tenant_obj
