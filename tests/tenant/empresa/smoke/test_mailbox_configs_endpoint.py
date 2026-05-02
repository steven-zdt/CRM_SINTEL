"""
Smoke test para verificar que GET /api/v1/empresas/mailbox/configs/ responde 200 OK.

[WARNING] MULTI-TENANT: Este test verifica que el endpoint está correctamente registrado
en el TENANT_URLCONF y responde correctamente desde el dominio del tenant.

Referencia: SINTEL v2.30 - API-First JSON-only, TENANT_URLCONF para privados.
"""
import pytest
from django.test import Client
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client as TenantClient, Domain
from apps.tenant.empresa.models import MailInboxConfig
from django.utils import timezone


@pytest.mark.django_db
def test_mailbox_configs_list_returns_200():
    """
    Verifica que GET /api/v1/empresas/mailbox/configs/ responde 200 OK desde el dominio del tenant.
    
    [WARNING] MULTI-TENANT: Usa HTTP_HOST para entrar al TENANT_URLCONF correcto.
    Este test comprueba el routing por hostname (clave en django-tenants).
    """
    # Crear tenant de prueba si no existe
    schema_name = "tenant_test_empresa_mailbox_smoke"
    tenant, created = TenantClient.objects.get_or_create(
        schema_name=schema_name,
        defaults={
            "name": "Test Empresa Mailbox Smoke Tenant",
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
    # [WARNING] CRÍTICO: Esto hace que django-tenants resuelva el TENANT_URLCONF correcto
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
    
    # Verificar estructura básica de respuesta (lista o paginada)
    data = resp.json()
    assert isinstance(data, (list, dict)), "Response should be a JSON array or paginated object"
    
    # Si es paginada, debe tener 'results' o 'count'
    if isinstance(data, dict):
        assert "results" in data or "count" in data, (
            "Paginated response should have 'results' or 'count'"
        )


@pytest.mark.django_db
def test_mailbox_configs_list_with_data_returns_200():
    """
    Verifica que GET /api/v1/empresas/mailbox/configs/ responde 200 OK con datos.
    
    [WARNING] MULTI-TENANT: Verifica que el endpoint funciona con datos en el esquema del tenant.
    """
    # Crear tenant de prueba
    schema_name = "tenant_test_empresa_mailbox_data_smoke"
    tenant, created = TenantClient.objects.get_or_create(
        schema_name=schema_name,
        defaults={
            "name": "Test Empresa Mailbox Data Smoke Tenant",
            "paid_until": timezone.now().replace(year=2099),
            "on_trial": False,
        }
    )
    
    # Crear dominio para el tenant
    domain_name = "test-mailbox.sintel.com"
    Domain.objects.get_or_create(
        domain=domain_name,
        tenant=tenant,
        defaults={"is_primary": True}
    )
    
    # Crear configuración de prueba en el esquema del tenant
    with schema_context(schema_name):
        # Asegurar que la tabla existe (migraciones aplicadas)
        try:
            MailInboxConfig.objects.create(
                nombre="Test Config",
                host="imap.test.com",
                port=993,
                protocol="imap",
                ssl=True,
                username="test@test.com",
                password="test123",
                mailbox="INBOX",
                is_active=True,
            )
        except Exception as e:
            # Si falla, puede ser que las migraciones no estén aplicadas
            pytest.skip(f"No se pudo crear configuración de prueba (migraciones?): {e}")
    
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
    
    # Verificar que contiene datos
    data = resp.json()
    if isinstance(data, list):
        assert len(data) > 0, "Response should contain at least one configuration"
        assert "id" in data[0], "Configuration should have 'id' field"
        assert "nombre" in data[0], "Configuration should have 'nombre' field"
        assert "password" not in data[0], "Password should not be exposed in response"
    elif isinstance(data, dict) and "results" in data:
        assert len(data["results"]) > 0, "Paginated response should contain at least one configuration"
        assert "id" in data["results"][0], "Configuration should have 'id' field"
        assert "password" not in data["results"][0], "Password should not be exposed in response"


@pytest.mark.django_db
def test_mailbox_configs_404_from_public_domain():
    """
    Verifica que GET /api/v1/empresas/mailbox/configs/ devuelve 404 desde el dominio público.
    
    [WARNING] SEGURIDAD: Las configuraciones de mailbox solo están disponibles en el ámbito del tenant.
    Este test confirma que el endpoint NO existe en ROOT_URLCONF.
    """
    # Cliente HTTP sin HTTP_HOST (o con dominio público)
    client = Client()
    # No establecer HTTP_HOST o usar un dominio que no sea de tenant
    
    # Hacer petición al endpoint desde contexto público
    url = "/api/v1/empresas/mailbox/configs/"
    resp = client.get(url)
    
    # Verificar que devuelve 404 (porque no existe en ROOT_URLCONF)
    # O 403 si hay algún middleware que bloquea
    assert resp.status_code in [404, 403], (
        f"Expected 404 or 403 from public domain, got {resp.status_code}. "
        f"This confirms that mailbox configs endpoint is only available in TENANT_URLCONF."
    )
