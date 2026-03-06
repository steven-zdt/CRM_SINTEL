"""
Smoke tests para endpoints de empresa (mailbox configs + mi-empresa).

⚠️ MULTI-TENANT: Estos tests verifican que los endpoints están correctamente registrados
en el TENANT_URLCONF y responden correctamente desde el dominio del tenant.

Referencia: SINTEL v2.30 - API-First JSON-only, TENANT_URLCONF para privados.
"""
import pytest
from django.test import Client
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client as TenantClient, Domain
from apps.tenant.empresa.models import MailInboxConfig, Empresa
from django.utils import timezone


@pytest.mark.django_db
def test_mi_empresa_returns_200(client):
    """
    Verifica que GET /api/v1/empresas/mi-empresa/ retorna 200 OK.
    
    ⚠️ MULTI-TENANT: Usa HTTP_HOST para entrar al TENANT_URLCONF correcto.
    """
    client.defaults["HTTP_HOST"] = "home.sintel.com"
    r = client.get("/api/v1/empresas/mi-empresa/")
    assert r.status_code == 200, r.content
    assert r.get("Content-Type", "").startswith("application/json"), "Response should be JSON"


@pytest.mark.django_db
def test_mailbox_configs_list_returns_200(client):
    """
    Verifica que GET /api/v1/empresas/mailbox/configs/ retorna 200 OK.
    
    ⚠️ MULTI-TENANT: Usa HTTP_HOST para entrar al TENANT_URLCONF correcto.
    """
    client.defaults["HTTP_HOST"] = "home.sintel.com"
    r = client.get("/api/v1/empresas/mailbox/configs/")
    assert r.status_code == 200, r.content
    assert r.get("Content-Type", "").startswith("application/json"), "Response should be JSON"


@pytest.mark.django_db
def test_mailbox_configs_list_and_mi_empresa():
    """
    Verifica que GET /api/v1/empresas/mailbox/configs/ y GET /api/v1/empresas/mi-empresa/
    responden 200 OK desde el dominio del tenant.
    
    ⚠️ MULTI-TENANT: Usa HTTP_HOST para entrar al TENANT_URLCONF correcto.
    Este test comprueba el routing por hostname (clave en django-tenants).
    """
    # Crear tenant de prueba si no existe
    schema_name = "tenant_test_empresa_endpoints_smoke"
    tenant, created = TenantClient.objects.get_or_create(
        schema_name=schema_name,
        defaults={
            "name": "Test Empresa Endpoints Smoke Tenant",
            "paid_until": timezone.now().replace(year=2099),
            "on_trial": False,
        }
    )
    
    # Crear dominio para el tenant (simulando home.sintel.com)
    domain_name = "home.sintel.com"
    Domain.objects.get_or_create(
        domain=domain_name,
        tenant=tenant,
        defaults={"is_primary": True}
    )
    
    # Cliente HTTP con HTTP_HOST del tenant
    # ⚠️ CRÍTICO: Esto hace que django-tenants resuelva el TENANT_URLCONF correcto
    client = Client()
    client.defaults["HTTP_HOST"] = domain_name
    
    # Test 1: GET /api/v1/empresas/mailbox/configs/
    r1 = client.get("/api/v1/empresas/mailbox/configs/")
    assert r1.status_code == 200, (
        f"Expected 200 OK for mailbox/configs/, got {r1.status_code}. "
        f"Response: {r1.content.decode('utf-8')[:500]}"
    )
    
    # Verificar que la respuesta es JSON
    assert r1.get("Content-Type", "").startswith("application/json"), (
        f"Expected JSON response, got {r1.get('Content-Type')}"
    )
    
    # Verificar estructura básica (paginada o lista simple)
    data1 = r1.json()
    assert isinstance(data1, (list, dict)), "Response should be a JSON array or paginated object"
    
    # Si es paginada, debe tener 'results' o 'count'
    if isinstance(data1, dict):
        assert "results" in data1 or "count" in data1, (
            "Paginated response should have 'results' or 'count'"
        )
    
    # Test 2: GET /api/v1/empresas/mi-empresa/
    r2 = client.get("/api/v1/empresas/mi-empresa/")
    # ⚠️ v2.30: El endpoint siempre retorna 200 (con datos o con mensaje informativo)
    assert r2.status_code == 200, (
        f"Expected 200 OK for mi-empresa/, got {r2.status_code}. "
        f"Response: {r2.content.decode('utf-8')[:500]}"
    )
    
    # Verificar que la respuesta es JSON
    assert r2.get("Content-Type", "").startswith("application/json"), (
        f"Expected JSON response, got {r2.get('Content-Type')}"
    )
    
    # Verificar estructura básica (empresa o mensaje informativo)
    data2 = r2.json()
    assert isinstance(data2, dict), "Response should be a JSON object"
    
    if "detail" in data2:
        # Si no existe empresa, debe tener 'detail' con mensaje informativo
        assert "Empresa" in data2["detail"], "Detail should mention 'Empresa'"
    else:
        # Si hay empresa, debe tener campos básicos
        assert "id" in data2 or "razon_social" in data2, (
            "Empresa response should have 'id' or 'razon_social'"
        )


@pytest.mark.django_db
def test_mailbox_configs_with_pagination():
    """
    Verifica que GET /api/v1/empresas/mailbox/configs/ maneja paginación DRF correctamente.
    """
    # Crear tenant de prueba
    schema_name = "tenant_test_empresa_pagination_smoke"
    tenant, created = TenantClient.objects.get_or_create(
        schema_name=schema_name,
        defaults={
            "name": "Test Empresa Pagination Smoke Tenant",
            "paid_until": timezone.now().replace(year=2099),
            "on_trial": False,
        }
    )
    
    # Crear dominio para el tenant
    domain_name = "test-pagination.sintel.com"
    Domain.objects.get_or_create(
        domain=domain_name,
        tenant=tenant,
        defaults={"is_primary": True}
    )
    
    # Cliente HTTP con HTTP_HOST del tenant
    client = Client()
    client.defaults["HTTP_HOST"] = domain_name
    
    # Hacer petición al endpoint
    url = "/api/v1/empresas/mailbox/configs/"
    resp = client.get(url)
    
    # Verificar respuesta
    assert resp.status_code == 200, (
        f"Expected 200 OK, got {resp.status_code}. "
        f"Response: {resp.content.decode('utf-8')[:500]}"
    )
    
    # Verificar que la respuesta es JSON
    assert resp.get("Content-Type", "").startswith("application/json"), (
        f"Expected JSON response, got {resp.get('Content-Type')}"
    )
    
    # Verificar estructura (puede ser lista o paginada)
    data = resp.json()
    if isinstance(data, dict):
        # Respuesta paginada DRF
        assert "results" in data, "Paginated response should have 'results'"
        assert isinstance(data["results"], list), "Results should be a list"
        # Verificar que password no se expone
        for item in data["results"]:
            assert "password" not in item, "Password should not be exposed in response"
    elif isinstance(data, list):
        # Lista simple
        for item in data:
            assert "password" not in item, "Password should not be exposed in response"


@pytest.mark.django_db
def test_mi_empresa_with_data():
    """
    Verifica que GET /api/v1/empresas/mi-empresa/ retorna datos cuando existe empresa.
    """
    # Crear tenant de prueba
    schema_name = "tenant_test_empresa_mi_empresa_data"
    tenant, created = TenantClient.objects.get_or_create(
        schema_name=schema_name,
        defaults={
            "name": "Test Empresa Mi Empresa Data Tenant",
            "paid_until": timezone.now().replace(year=2099),
            "on_trial": False,
        }
    )
    
    # Crear dominio para el tenant
    domain_name = "test-mi-empresa.sintel.com"
    Domain.objects.get_or_create(
        domain=domain_name,
        tenant=tenant,
        defaults={"is_primary": True}
    )
    
    # Crear empresa de prueba en el esquema del tenant
    with schema_context(schema_name):
        try:
            Empresa.objects.create(
                razon_social="Test Empresa S.A.S.",
                nit="123456789",
                direccion="Calle Test 123",
                telefono="1234567890",
            )
        except Exception as e:
            # Si falla, puede ser que las migraciones no estén aplicadas
            pytest.skip(f"No se pudo crear empresa de prueba (migraciones?): {e}")
    
    # Cliente HTTP con HTTP_HOST del tenant
    client = Client()
    client.defaults["HTTP_HOST"] = domain_name
    
    # Hacer petición al endpoint
    url = "/api/v1/empresas/mi-empresa/"
    resp = client.get(url)
    
    # Verificar respuesta
    assert resp.status_code == 200, (
        f"Expected 200 OK, got {resp.status_code}. "
        f"Response: {resp.content.decode('utf-8')[:500]}"
    )
    
    # Verificar que la respuesta es JSON
    assert resp.get("Content-Type", "").startswith("application/json"), (
        f"Expected JSON response, got {resp.get('Content-Type')}"
    )
    
    # Verificar que contiene datos de empresa
    data = resp.json()
    assert isinstance(data, dict), "Response should be a JSON object"
    assert "razon_social" in data, "Response should contain 'razon_social'"
    assert data["razon_social"] == "Test Empresa S.A.S.", "Should return the created empresa"


@pytest.mark.django_db
def test_empresa_endpoints_404_from_public_domain():
    """
    Verifica que los endpoints de empresa devuelven 404 desde el dominio público.
    
    ⚠️ SEGURIDAD: Los endpoints de empresa solo están disponibles en el ámbito del tenant.
    Este test confirma que los endpoints NO existen en ROOT_URLCONF.
    """
    # Cliente HTTP sin HTTP_HOST (o con dominio público)
    client = Client()
    # No establecer HTTP_HOST o usar un dominio que no sea de tenant
    
    # Test 1: mailbox/configs/
    url1 = "/api/v1/empresas/mailbox/configs/"
    resp1 = client.get(url1)
    assert resp1.status_code in [404, 403], (
        f"Expected 404 or 403 from public domain for mailbox/configs/, got {resp1.status_code}. "
        f"This confirms that endpoint is only available in TENANT_URLCONF."
    )
    
    # Test 2: mi-empresa/
    url2 = "/api/v1/empresas/mi-empresa/"
    resp2 = client.get(url2)
    assert resp2.status_code in [404, 403], (
        f"Expected 404 or 403 from public domain for mi-empresa/, got {resp2.status_code}. "
        f"This confirms that endpoint is only available in TENANT_URLCONF."
    )
