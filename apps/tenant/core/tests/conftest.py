"""
Pytest fixtures for apps/tenant/core/ tests.
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

    if 'perfil_tenantprofile' not in tables:
        call_command('migrate_schemas', '--tenant', '-s', tenant_obj.schema_name, 'perfil', '--noinput', verbosity=0)

    with schema_context(tenant_obj.schema_name):
        tables = set(connection.introspection.table_names())

    # Requerido por test_workspace_401_handler_smoke.py -- ejercita
    # /api/v1/gastos/, /api/v1/clientes/, /api/v1/proveedores/.
    if 'tenant_gastos_gasto' not in tables:
        call_command('migrate_schemas', '--tenant', '-s', tenant_obj.schema_name, 'tenant_gastos', '--noinput', verbosity=0)

    with schema_context(tenant_obj.schema_name):
        tables = set(connection.introspection.table_names())

    if 'clientes_cliente' not in tables:
        call_command('migrate_schemas', '--tenant', '-s', tenant_obj.schema_name, 'tenant_clientes', '--noinput', verbosity=0)

    with schema_context(tenant_obj.schema_name):
        tables = set(connection.introspection.table_names())

    if 'proveedores_proveedor' not in tables:
        call_command('migrate_schemas', '--tenant', '-s', tenant_obj.schema_name, 'tenant_proveedores', '--noinput', verbosity=0)

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


def _crear_tenant_completo(schema, nit):
    """
    N8N-SINTEL-02 (FASE 3): mismo patron canonico de
    apps/tenant/bancos/tests/conftest.py (AGENTS.md §24.5), pero con
    migracion COMPLETA (sin filtrar por app) -- a diferencia del fixture
    `tenant` de arriba, que solo migra empresa/perfil/gastos/clientes/
    proveedores, aqui se necesita `facturas` real para probar aislamiento
    cross-tenant del endpoint upload-document.
    """
    tenant_obj = Client.objects.filter(schema_name=schema).first()
    if not tenant_obj:
        with schema_context('public'):
            tenant_obj = Client.objects.create(schema_name=schema, nombre=schema)
            Domain.objects.create(tenant=tenant_obj, domain=f'{schema}.sintel.net.co', is_primary=True)

    with connection.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS {schema}')

    call_command('migrate_schemas', '--tenant', '-s', schema, '--noinput', verbosity=0)

    with schema_context(schema):
        if not Empresa.objects.exists():
            Empresa.objects.create(nit=nit, razon_social=f'Empresa {schema} SAS', direccion='Calle 1')

    return tenant_obj


@pytest.fixture
def n8n_tenant_a(db):
    # NIT 901999888: mismo receptor (CompanyID) del XML_VALIDO fijo en
    # test_n8n_upload_document_security.py -- FacturaBusinessService.
    # guardar_desde_dto() exige que la Empresa actual coincida con el
    # emisor o el receptor del documento (regla real, no relajada aqui).
    return _crear_tenant_completo('n8ntesta', '901999888')


@pytest.fixture
def n8n_tenant_b(db):
    return _crear_tenant_completo('n8ntestb', '900222222')
