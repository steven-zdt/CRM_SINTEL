"""
Pytest fixtures for Cotizaciones tests.
Provides fixtures for multi-tenant tests and entity factories.
"""
import pytest
from django.core.management import call_command
from django.db import connection
from django_tenants.utils import schema_context

from apps.public.tenants.models import Client, Domain
from apps.tenant.empresa.models import Empresa
from apps.tenant.clientes.models import Cliente
from apps.tenant.perfil.models import TenantProfile
from django.contrib.auth import get_user_model
from apps.public.tenants.models import TenantMembership


def _ensure_tenant(schema_name, nombre):
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

    # Migrate tenant apps required for cotizaciones tests
    # 'facturas' agregado para el test de bloqueo de DELETE por Factura
    # vinculada (Factura.cotizacion_uuid) -- auditoria REL Cotizaciones
    # FASE 5, 2026-08-26.
    # 'tenant_ventas' agregado para los tests de convertir_a_venta()
    # (COTIZACIONES-01, 2026-09-08). 'tenant_inventario' (ItemVenta.producto/
    # servicio son FK reales a ese catalogo) y 'tenant_proyectos'
    # (convertir_a_proyecto) agregados en COTIZACIONES-02, mismo dia.
    # 'tenant_gastos' agregado 2026-09-18: GASTOS_PROYECTOS_01 acoplo
    # calcular_indicadores_financieros() (llamado desde
    # orchestrate_create_proyecto(), en el camino de convertir_a_proyecto())
    # a tenant_gastos_documentosoporte via import perezoso -- sin esta
    # migracion, convertir_a_proyecto() fallaba con "relation ... does not
    # exist" en cualquier tenant de test que no tuviera ya esa tabla.
    required_apps = [
        'empresa', 'perfil', 'tenant_clientes', 'tenant_cotizaciones', 'facturas',
        'tenant_ventas', 'tenant_inventario', 'tenant_proyectos', 'tenant_gastos',
    ]
    for app in required_apps:
        call_command('migrate_schemas', '--tenant', '-s', tenant_obj.schema_name, app, '--noinput', verbosity=0)

    return tenant_obj


@pytest.fixture
def tenant(db):
    """
    Fixture that returns an existing test tenant and sets up database schema.
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
    (COTIZACIONES-01: Cotizacion->Venta, 2026-09-08)."""
    return _ensure_tenant('testtenantb_cot', 'Test Tenant B Cotizaciones')


@pytest.fixture
def factory_empresa(tenant):
    """
    Factory fixture to create or retrieve the singleton Empresa.
    """
    def _create_empresa():
        with schema_context(tenant.schema_name):
            empresa = Empresa.objects.first()
            if not empresa:
                empresa = Empresa.objects.create(
                    razon_social='EMPRESA TEST S.A.S.',
                    nit='901234567',
                    direccion='Direccion de prueba',
                    telefono='3000000000',
                )
            
            # Create a user to avoid `usuario_set.first()` returning None in tests
            User = get_user_model()
            user = User.objects.filter(email="admin@test.local").first()
            if not user:
                user = User.objects.create_superuser(
                    username="admin_test",
                    email="admin@test.local",
                    password="admin123"
                )
            
            # Ensure TenantMembership and TenantProfile exist
            TenantMembership.objects.get_or_create(
                client=tenant,
                user=user,
                defaults={'is_active': True, 'rol': 'ADMIN'}
            )
            TenantProfile.objects.get_or_create(
                user=user,
                empresa=empresa,
                defaults={'rol': 'ADMIN'}
            )
            
            return empresa
    return _create_empresa


@pytest.fixture
def factory_cliente(tenant):
    """
    Factory fixture to create a Cliente.
    """
    def _create_cliente(empresa):
        with schema_context(tenant.schema_name):
            cliente = Cliente.objects.filter(empresa=empresa).first()
            if not cliente:
                cliente = Cliente.objects.create(
                    empresa=empresa,
                    tipo_persona='JURIDICA',
                    tipo_documento='NIT',
                    numero_documento='800123456',
                    razon_social='CLIENTE TEST S.A.S.',
                    direccion='Calle de prueba',
                    telefono='3111111111',
                    email='cliente@test.com',
                    regimen_tributario='ORDINARIO',
                )
            return cliente
    return _create_cliente
