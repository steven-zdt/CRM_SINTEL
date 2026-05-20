"""
Pytest fixtures for Proveedores tests.
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
        domain=f'{tenant_obj.schema_name}.sintel.com',
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

    if 'proveedores_proveedor' not in tables:
        call_command('migrate_schemas', '--tenant', '-s', tenant_obj.schema_name, 'tenant_proveedores', '--noinput', verbosity=0)

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
