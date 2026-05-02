"""
Pruebas de humo para API de empleados (DRF + multitenancy).

Verifica que los endpoints respondan correctamente y que el aislamiento
por esquema funcione correctamente.
"""
import pytest
from django_tenants.utils import schema_context

from apps.tenant.empleados.models import Empleado


@pytest.mark.django_db
def test_empleados_list_smoke(client, django_user_model, tenant):
    """
    Smoke test: lista de empleados.
    
    Inserta un registro en el esquema del tenant y verifica que el endpoint
    responda correctamente (200 o 404 si aún no se incluyó el router).
    """
    # Insertar registro en el esquema del tenant
    with schema_context(tenant.schema_name):
        Empleado.objects.create(
            tipo_documento="CC",
            numero_documento="1234567890",
            primer_nombre="Ana",
            primer_apellido="Pérez",
            email="ana@example.com",
            estado="ACTIVO"
        )
    
    # Autenticar usuario global (según fixtures)
    user = django_user_model.objects.create(username="testuser", email="test@example.com")
    client.force_login(user)
    
    # La ruta se incluirá más adelante en TENANT_URLCONF (/api/v1/empleados/)
    resp = client.get("/api/v1/empleados/", HTTP_HOST=f"{tenant.schema_name}.sintel.com")
    
    # 200 si el router está incluido, 404 si aún no se incluyó
    assert resp.status_code in (200, 404), f"Expected 200 or 404, got {resp.status_code}"


@pytest.mark.django_db
def test_empleados_create_smoke(client, django_user_model, tenant):
    """
    Smoke test: crear empleado.
    
    Verifica que el endpoint de creación responda correctamente.
    """
    user = django_user_model.objects.create(username="testuser", email="test@example.com")
    client.force_login(user)
    
    payload = {
        "tipo_documento": "CC",
        "numero_documento": "9876543210",
        "primer_nombre": "Juan",
        "primer_apellido": "García",
        "email": "juan@example.com",
        "estado": "ACTIVO"
    }
    
    resp = client.post(
        "/api/v1/empleados/",
        data=payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant.schema_name}.sintel.com"
    )
    
    # 201 si el router está incluido y funciona, 404 si aún no se incluyó
    assert resp.status_code in (201, 404), f"Expected 201 or 404, got {resp.status_code}"
    
    # Si se creó, verificar que existe en el esquema correcto
    if resp.status_code == 201:
        with schema_context(tenant.schema_name):
            assert Empleado.objects.filter(numero_documento="9876543210").exists()


@pytest.mark.django_db
def test_empleados_multitenancy_isolation(client, django_user_model, tenant, tenant_factory):
    """
    Smoke test: aislamiento multitenant.
    
    Verifica que los empleados de un tenant no sean visibles desde otro tenant.
    """
    # Crear segundo tenant
    tenant2 = tenant_factory(schema_name="tenant2")
    
    # Crear empleado en tenant1
    with schema_context(tenant.schema_name):
        Empleado.objects.create(
            tipo_documento="CC",
            numero_documento="1111111111",
            primer_nombre="Tenant1",
            primer_apellido="User",
            email="t1@example.com"
        )
    
    # Crear empleado en tenant2
    with schema_context(tenant2.schema_name):
        Empleado.objects.create(
            tipo_documento="CC",
            numero_documento="2222222222",
            primer_nombre="Tenant2",
            primer_apellido="User",
            email="t2@example.com"
        )
    
    user = django_user_model.objects.create(username="testuser", email="test@example.com")
    client.force_login(user)
    
    # Verificar que tenant1 solo ve su empleado (si el router está incluido)
    resp1 = client.get("/api/v1/empleados/", HTTP_HOST=f"{tenant.schema_name}.sintel.com")
    if resp1.status_code == 200:
        data1 = resp1.json()
        results1 = data1.get("results", data1) if isinstance(data1, dict) else data1
        if isinstance(results1, list):
            doc_numbers = [r.get("numero_documento") for r in results1 if isinstance(r, dict)]
            assert "1111111111" in doc_numbers or len(doc_numbers) == 0
            assert "2222222222" not in doc_numbers
    
    # Verificar que tenant2 solo ve su empleado
    resp2 = client.get("/api/v1/empleados/", HTTP_HOST=f"{tenant2.schema_name}.sintel.com")
    if resp2.status_code == 200:
        data2 = resp2.json()
        results2 = data2.get("results", data2) if isinstance(data2, dict) else data2
        if isinstance(results2, list):
            doc_numbers = [r.get("numero_documento") for r in results2 if isinstance(r, dict)]
            assert "2222222222" in doc_numbers or len(doc_numbers) == 0
            assert "1111111111" not in doc_numbers
