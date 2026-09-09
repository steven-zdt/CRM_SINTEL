"""
Pytest fixtures for Proveedores tests.
"""
import pytest
from django.core.management import call_command
from django.db import connection
from django_tenants.utils import schema_context

from apps.public.tenants.models import Client, Domain
from apps.tenant.empresa.models import Empresa


def _ensure_tenant(schema_name, nombre):
    """Crea (o reutiliza) un tenant de prueba con las tablas minimas para
    los tests de proveedores. Extraido para poder provisionar 2 tenants
    independientes (aislamiento cross-tenant) sin duplicar la logica."""
    tenant_obj = Client.objects.filter(schema_name=schema_name).only('id', 'schema_name', 'nombre').first()
    if not tenant_obj:
        with schema_context('public'):
            tenant_obj = Client(schema_name=schema_name, nombre=nombre)
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

    if 'proveedores_proveedor' not in tables:
        call_command('migrate_schemas', '--tenant', '-s', tenant_obj.schema_name, 'tenant_proveedores', '--noinput', verbosity=0)

    with schema_context(tenant_obj.schema_name):
        tables = set(connection.introspection.table_names())

    if 'perfil_tenantprofile' not in tables:
        call_command('migrate_schemas', '--tenant', '-s', tenant_obj.schema_name, 'perfil', '--noinput', verbosity=0)

    with schema_context(tenant_obj.schema_name):
        tables = set(connection.introspection.table_names())

    if 'facturas_factura' not in tables:
        # Requerido por ProveedorSelector.get_cuentas_pagar_resumen() (lee
        # Factura.naturaleza=COMPRA como fuente de verdad de cartera).
        call_command('migrate_schemas', '--tenant', '-s', tenant_obj.schema_name, 'facturas', '--noinput', verbosity=0)

    with schema_context(tenant_obj.schema_name):
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            Empresa.objects.create(
                razon_social=f'EMPRESA {nombre.upper()} S.A.S.',
                nit='901234567' if schema_name.endswith('b') else '901234566',
                direccion='Direccion de prueba',
                telefono='3000000000',
            )

    return tenant_obj


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
        return _ensure_tenant(tenant_obj.schema_name, tenant_obj.nombre or 'Test Tenant')
    return _ensure_tenant('testtenant', 'Test Tenant')


@pytest.fixture
def tenant_b(db):
    """Segundo tenant independiente, para tests de aislamiento cross-tenant
    (PROVEEDORES-01: CuentasPagar no tenia cobertura de aislamiento)."""
    return _ensure_tenant('testtenantb', 'Test Tenant B')
