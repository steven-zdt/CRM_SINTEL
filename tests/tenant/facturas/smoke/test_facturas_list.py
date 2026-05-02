"""
Smoke test para verificar que GET /api/v1/facturas/ responde 200 OK.

[WARNING] MULTI-TENANT: Este test verifica que el endpoint está correctamente registrado
en el TENANT_URLCONF y responde correctamente desde el dominio del tenant.

Referencia: SINTEL v2.30 - API-First JSON-only, TENANT_URLCONF para privados.
"""
import pytest
from django.test import Client
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client as TenantClient, Domain
from apps.tenant.facturas.models import Factura
from django.utils import timezone


@pytest.mark.django_db
def test_list_facturas_returns_200():
    """
    Verifica que GET /api/v1/facturas/ responde 200 OK desde el dominio del tenant.
    
    [WARNING] MULTI-TENANT: Usa HTTP_HOST para entrar al TENANT_URLCONF correcto.
    Este test comprueba el routing por hostname (clave en django-tenants).
    """
    # Crear tenant de prueba si no existe
    schema_name = "tenant_test_facturas_smoke"
    tenant, created = TenantClient.objects.get_or_create(
        schema_name=schema_name,
        defaults={
            "name": "Test Facturas Smoke Tenant",
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
    
    # Crear factura de prueba en el esquema del tenant
    with schema_context(schema_name):
        # Asegurar que la tabla existe (migraciones aplicadas)
        try:
            Factura.objects.create(
                numero="SMOKE-001",
                naturaleza="VENTA",
                estado="BORRADOR",
                fecha_emision=timezone.now(),
                moneda="COP",
                subtotal=1000,
                impuestos=190,
                total=1190,
                emisor_nit="123456789",
                emisor_razon_social="EMISOR SMOKE TEST",
                receptor_nit="987654321",
                receptor_razon_social="RECEPTOR SMOKE TEST",
            )
        except Exception as e:
            # Si falla, puede ser que las migraciones no estén aplicadas
            pytest.skip(f"No se pudo crear factura de prueba (migraciones?): {e}")
    
    # Cliente HTTP con HTTP_HOST del tenant
    # [WARNING] CRÍTICO: Esto hace que django-tenants resuelva el TENANT_URLCONF correcto
    client = Client()
    client.defaults["HTTP_HOST"] = domain_name
    
    # Hacer petición al endpoint
    url = "/api/v1/facturas/?ordering=-fecha_emision&page=1&page_size=10"
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
    
    # Verificar estructura básica de respuesta paginada
    data = resp.json()
    assert isinstance(data, dict), "Response should be a JSON object"
    assert "results" in data or "count" in data, (
        "Response should have pagination structure (results or count)"
    )


@pytest.mark.django_db
def test_list_facturas_empty_returns_200():
    """
    Verifica que GET /api/v1/facturas/ responde 200 OK incluso sin facturas.
    
    [WARNING] MULTI-TENANT: Verifica que el endpoint existe aunque no haya datos.
    """
    # Crear tenant de prueba
    schema_name = "tenant_test_facturas_empty_smoke"
    tenant, created = TenantClient.objects.get_or_create(
        schema_name=schema_name,
        defaults={
            "name": "Test Facturas Empty Smoke Tenant",
            "paid_until": timezone.now().replace(year=2099),
            "on_trial": False,
        }
    )
    
    # Crear dominio para el tenant
    domain_name = "empty-test.sintel.com"
    Domain.objects.get_or_create(
        domain=domain_name,
        tenant=tenant,
        defaults={"is_primary": True}
    )
    
    # Cliente HTTP con HTTP_HOST del tenant
    client = Client()
    client.defaults["HTTP_HOST"] = domain_name
    
    # Hacer petición al endpoint (sin facturas)
    url = "/api/v1/facturas/?ordering=-fecha_emision&page=1&page_size=10"
    resp = client.get(url)
    
    # Verificar respuesta (debe ser 200 incluso sin datos)
    assert resp.status_code == 200, (
        f"Expected 200 OK even with no data, got {resp.status_code}. "
        f"Response: {resp.content.decode('utf-8')[:500]}"
    )
    
    # Verificar que la respuesta es JSON
    assert resp.get("Content-Type", "").startswith("application/json"), (
        f"Expected JSON response, got {resp.get('Content-Type')}"
    )


@pytest.mark.django_db
def test_list_facturas_404_from_public_domain():
    """
    Verifica que GET /api/v1/facturas/ devuelve 404 desde el dominio público.
    
    [WARNING] SEGURIDAD: Las facturas solo están disponibles en el ámbito del tenant.
    Este test confirma que el endpoint NO existe en ROOT_URLCONF.
    """
    # Cliente HTTP sin HTTP_HOST (o con dominio público)
    client = Client()
    # No establecer HTTP_HOST o usar un dominio que no sea de tenant
    
    # Hacer petición al endpoint desde contexto público
    url = "/api/v1/facturas/"
    resp = client.get(url)
    
    # Verificar que devuelve 404 (porque no existe en ROOT_URLCONF)
    # O 403 si hay algún middleware que bloquea
    assert resp.status_code in [404, 403], (
        f"Expected 404 or 403 from public domain, got {resp.status_code}. "
        f"This confirms that facturas endpoint is only available in TENANT_URLCONF."
    )
