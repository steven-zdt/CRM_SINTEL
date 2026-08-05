"""
Test: Verifica que los endpoints de proveedores acepten SessionAuthentication
y NO devuelvan 401 cuando el usuario está autenticado con sesión.

Valida que:
1. Los endpoints respondan 200 cuando el usuario está autenticado con sesión
2. Los endpoints NO devuelvan 401 si SessionAuthentication está configurado
3. El handler del workspace NO redirija a login para este módulo no crítico
"""
import pytest
from django.core.management import call_command
from django.db import connection
from django_tenants.utils import schema_context

from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.tenant.empresa.models import Empresa


@pytest.fixture
def tenant(db):
    tenant_obj = (
        Client.objects.exclude(schema_name='public')
        .exclude(schema_name__contains='_')
        .only('id', 'schema_name', 'nombre')
        .first()
    )

    if not tenant_obj:
        with schema_context('public'):
            tenant_obj = Client.objects.filter(schema_name='testtenant').only('id', 'schema_name', 'nombre').first()
            if not tenant_obj:
                tenant_obj = Client(schema_name='testtenant', nombre='Test Tenant')
                tenant_obj.auto_create_schema = False
                tenant_obj.save(force_insert=True)

    Domain.objects.get_or_create(
        tenant=tenant_obj,
        domain=f'{tenant_obj.schema_name}.sintel.net.co',
        defaults={'is_primary': True},
    )

    with connection.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA IF NOT EXISTS {tenant_obj.schema_name}')

    with schema_context(tenant_obj.schema_name):
        tables = set(connection.introspection.table_names())

    if 'empresa_empresa' not in tables:
        call_command('migrate_schemas', '--tenant', '-s', tenant_obj.schema_name, 'empresa', '--noinput', verbosity=0)

    if 'tenant_proveedores_proveedor' not in tables:
        call_command('migrate_schemas', '--tenant', '-s', tenant_obj.schema_name, 'tenant_proveedores', '--noinput', verbosity=0)

    with schema_context(tenant_obj.schema_name):
        if not Empresa.objects.only('id').first():
            Empresa.objects.create(
                razon_social='EMPRESA TEST PROVEEDORES S.A.S.',
                nit='901234567',
                direccion='Direccion de prueba',
                telefono='3000000000',
            )

    return tenant_obj


@pytest.mark.django_db
def test_proveedores_list_session_ok(client, django_user_model, tenant):
    """
    Verifica que tras login, el endpoint de proveedores NO devuelva 401.
    
    Si el ViewSet acepta SessionAuthentication, NO debe devolver 401 tras login.
    """
    # Crear usuario
    user = django_user_model.objects.create(username="testuser", email="test@example.com")
    
    # Crear membresía activa en el tenant
    TenantMembership.objects.create(
        client=tenant,
        user=user,
        is_active=True,
        rol="ADMIN"
    )
    
    # django.contrib.sessions esta en TENANT_APPS (sesiones aisladas por
    # schema, ver config/settings.py) -- force_login() debe ejecutarse
    # dentro del schema del tenant para que la sesion se guarde en la
    # tabla django_session correcta (la que consultara SessionMiddleware
    # una vez el request cambie a este schema). Fuera de schema_context()
    # la sesion se guarda en 'public' y el request subsiguiente recibe
    # AnonymousUser -> puede enmascarar un 401 real como 404.
    with schema_context(tenant.schema_name):
        client.force_login(user)

    # Si el ViewSet acepta SessionAuthentication, NO debe devolver 401
    r = client.get("/api/v1/proveedores/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    # Nunca debe ser 401 si la sesión está activa y SessionAuthentication está configurado
    assert r.status_code == 200, (
        f"El endpoint de proveedores no respondió 200 tras login por sesión. "
        f"Verifica que ProveedorViewSet tenga authentication_classes = [SessionAuthentication]. "
        f"Status recibido: {r.status_code}"
    )


# WARNING: v2.40: CompraProveedorViewSet eliminado - este test ya no aplica
# @pytest.mark.django_db
# def test_compras_proveedor_list_session_ok(client, django_user_model, tenant):
#     """
#     WARNING: DEPRECATED: CompraProveedorViewSet fue eliminado en v2.40.
#     Este test ya no aplica.
#     """
#     pass
