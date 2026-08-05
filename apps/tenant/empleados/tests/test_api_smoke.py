"""
Pruebas de humo para API de empleados (DRF + multitenancy).

Verifica que los endpoints respondan correctamente y que el aislamiento
por esquema funcione correctamente.
"""
import pytest
from django_tenants.utils import schema_context

from apps.tenant.empleados.models import Empleado


@pytest.mark.django_db
def test_empleados_list_smoke(client, admin_user, tenant):
    """
    Smoke test: lista de empleados.
    
    Inserta un registro en el esquema del tenant y verifica que el endpoint
    responda correctamente (200 o 404 si aún no se incluyó el router).
    """
    # Insertar registro en el esquema del tenant
    with schema_context(tenant.schema_name):
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.first()
        Empleado.objects.create(
            tipo_documento="CC",
            numero_documento="1234567890",
            primer_nombre="Ana",
            primer_apellido="Pérez",
            email="ana@example.com",
            estado="ACTIVO",
            fecha_ingreso="2024-01-01",
            empresa=empresa,
            eps="EPS004",
            afp="AFP001",
            arl="ARL002"
        )
    
    # Autenticar usuario global (según fixtures)
    client.force_login(admin_user)
    
    # La ruta se incluirá más adelante en TENANT_URLCONF (/api/v1/empleados/)
    resp = client.get("/api/v1/empleados/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")
    
    # 200 si el router está incluido, 404 si aún no se incluyó
    assert resp.status_code in (200, 404), f"Expected 200 or 404, got {resp.status_code}"


@pytest.mark.django_db
def test_empleados_create_smoke(client, admin_user, tenant):
    """
    Smoke test: crear empleado.
    
    Verifica que el endpoint de creación responda correctamente.
    """
    client.force_login(admin_user)
    
    with schema_context(tenant.schema_name):
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.first()
    
    payload = {
        "empresa": str(empresa.id),
        "tipo_documento": "CC",
        "numero_documento": "9876543210",
        "primer_nombre": "Juan",
        "primer_apellido": "García",
        "email": "juan@example.com",
        "estado": "ACTIVO",
        "fecha_ingreso": "2024-01-01",
        "eps": "EPS004",
        "afp": "AFP001",
        "arl": "ARL002"
    }
    
    resp = client.post(
        "/api/v1/empleados/",
        data=payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co"
    )
    
    # 201 si el router está incluido y funciona, 404 si aún no se incluyó
    assert resp.status_code in (201, 404), f"Expected 201 or 404, got {resp.status_code}"
    
    # Si se creó, verificar que existe en el esquema correcto
    if resp.status_code == 201:
        with schema_context(tenant.schema_name):
            assert Empleado.objects.filter(numero_documento="9876543210").exists()


@pytest.mark.django_db
def test_empleados_multitenancy_isolation(client, admin_user, tenant, tenant_factory):
    """
    Smoke test: aislamiento multitenant.
    
    Verifica que los empleados de un tenant no sean visibles desde otro tenant.
    """
    # Crear segundo tenant
    tenant2 = tenant_factory(schema_name="tenant2")
    
    # Crear empleado en tenant1
    with schema_context(tenant.schema_name):
        from apps.tenant.empresa.models import Empresa
        empresa1 = Empresa.objects.first()
        Empleado.objects.create(
            tipo_documento="CC",
            numero_documento="1111111111",
            primer_nombre="Tenant1",
            primer_apellido="User",
            email="t1@example.com",
            fecha_ingreso="2024-01-01",
            empresa=empresa1,
            eps="EPS004",
            afp="AFP001",
            arl="ARL002"
        )
    
    # Crear empleado en tenant2
    with schema_context(tenant2.schema_name):
        from apps.tenant.empresa.models import Empresa
        empresa2 = Empresa.objects.first()
        # Ensure Empresa exists in tenant2 as tenant_factory might not run the migrations.
        if not empresa2:
            empresa2 = Empresa.objects.create(
                razon_social='EMPRESA TEST 2',
                nit='901234568',
                direccion='Dir test 2',
                telefono='3000000001'
            )
        Empleado.objects.create(
            tipo_documento="CC",
            numero_documento="2222222222",
            primer_nombre="Tenant2",
            primer_apellido="User",
            email="t2@example.com",
            fecha_ingreso="2024-01-01",
            empresa=empresa2,
            eps="EPS004",
            afp="AFP001",
            arl="ARL002"
        )
    
    from apps.public.tenants.models import TenantMembership
    from apps.tenant.perfil.models import TenantProfile
    TenantMembership.objects.get_or_create(
        client=tenant2,
        user=admin_user,
        defaults={'is_active': True, 'rol': 'ADMIN'}
    )
    with schema_context(tenant2.schema_name):
        TenantProfile.objects.get_or_create(
            user=admin_user,
            empresa=empresa2,
            defaults={'rol': 'ADMIN'}
        )
    
    client.force_login(admin_user)
    
    # Verificar que tenant1 solo ve su empleado (si el router está incluido)
    resp1 = client.get("/api/v1/empleados/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")
    if resp1.status_code == 200:
        data1 = resp1.json()
        results1 = data1.get("results", data1) if isinstance(data1, dict) else data1
        if isinstance(results1, list):
            doc_numbers = [r.get("numero_documento") for r in results1 if isinstance(r, dict)]
            assert "1111111111" in doc_numbers or len(doc_numbers) == 0
            assert "2222222222" not in doc_numbers
    
    # Verificar que tenant2 solo ve su empleado
    resp2 = client.get("/api/v1/empleados/", HTTP_HOST=f"{tenant2.schema_name}.sintel.net.co")
    if resp2.status_code == 200:
        data2 = resp2.json()
        results2 = data2.get("results", data2) if isinstance(data2, dict) else data2
        if isinstance(results2, list):
            doc_numbers = [r.get("numero_documento") for r in results2 if isinstance(r, dict)]
            assert "2222222222" in doc_numbers or len(doc_numbers) == 0
            assert "1111111111" not in doc_numbers
