"""
Smoke tests para Core API endpoints de perfil (mi-perfil/ y mi-perfil/configuracion/).

[WARNING] MULTI-TENANT: Estos tests verifican que los endpoints Core API están correctamente registrados
en el TENANT_URLCONF y responden correctamente desde el dominio del tenant.

Referencia: SINTEL v2.30 - Core API como orquestador único de la UI privada.
"""
import json

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.utils import timezone
from django_tenants.utils import schema_context

from apps.public.tenants.models import Client as TenantClient
from apps.public.tenants.models import Domain
from apps.tenant.perfil.models import TenantProfile

User = get_user_model()


@pytest.mark.django_db
def test_core_mi_perfil_get_returns_200(client):
    """
    Verifica que GET /api/v1/core/mi-perfil/ retorna 200 OK.
    
    [WARNING] MULTI-TENANT: Usa HTTP_HOST para entrar al TENANT_URLCONF correcto.
    """
    try:
        import cryptography  # noqa: F401
        import playwright  # noqa: F401
    except Exception:
        pytest.skip("Skipping heavy smoke test: missing playwright/cryptography")

    # Crear tenant de prueba
    schema_name = "tenant_test_core_mi_perfil_get"
    tenant, created = TenantClient.objects.get_or_create(
        schema_name=schema_name,
        defaults={
            "name": "Test Core Mi Perfil Get Tenant",
            "paid_until": timezone.now().replace(year=2099),
            "on_trial": False,
        }
    )
    
    # Crear dominio para el tenant
    domain_name = "test-core-perfil.sintel.net.co"
    Domain.objects.get_or_create(
        domain=domain_name,
        tenant=tenant,
        defaults={"is_primary": True}
    )
    
    # Crear usuario y perfil en el esquema del tenant
    with schema_context(schema_name):
        try:
            user = User.objects.create_user(
                username="testuser",
                email="test@example.com",
                password="testpass123",
                first_name="Test",
                last_name="User"
            )
            TenantProfile.objects.create(
                user=user,
                cargo="Contador",
                departamento="Finanzas",
                telefono_corporativo="3001234567",
                configuracion={"tema": "oscuro"}
            )
        except Exception as e:
            pytest.skip(f"No se pudo crear usuario/perfil de prueba (migraciones?): {e}")
    
    # Cliente HTTP con HTTP_HOST del tenant
    client.defaults["HTTP_HOST"] = domain_name
    client.force_login(user)
    
    # Hacer petición al endpoint Core API
    url = "/api/v1/core/mi-perfil/"
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
    
    # Verificar estructura básica
    data = resp.json()
    assert isinstance(data, dict), "Response should be a JSON object"
    assert "user_id" in data, "Response should contain 'user_id' (from User global)"
    assert "user_email" in data, "Response should contain 'user_email' (from User global)"
    assert "cargo" in data, "Response should contain 'cargo'"
    assert data["cargo"] == "Contador", "Should return the created cargo"
    assert data["user_email"] == "test@example.com", "Should return the user email"


@pytest.mark.django_db
def test_core_mi_perfil_patch_json_returns_200(client):
    """
    Verifica que PATCH /api/v1/core/mi-perfil/ con JSON actualiza campos básicos.
    
    [WARNING] MULTI-TENANT: Usa HTTP_HOST para entrar al TENANT_URLCONF correcto.
    """
    # Crear tenant de prueba
    schema_name = "tenant_test_core_mi_perfil_patch_json"
    tenant, created = TenantClient.objects.get_or_create(
        schema_name=schema_name,
        defaults={
            "name": "Test Core Mi Perfil Patch JSON Tenant",
            "paid_until": timezone.now().replace(year=2099),
            "on_trial": False,
        }
    )
    
    # Crear dominio para el tenant
    domain_name = "test-core-perfil-patch.sintel.net.co"
    Domain.objects.get_or_create(
        domain=domain_name,
        tenant=tenant,
        defaults={"is_primary": True}
    )
    
    # Crear usuario y perfil en el esquema del tenant
    with schema_context(schema_name):
        try:
            user = User.objects.create_user(
                username="testuser2",
                email="test2@example.com",
                password="testpass123",
            )
            TenantProfile.objects.create(
                user=user,
                cargo="Auxiliar",
                departamento="RRHH",
            )
        except Exception as e:
            pytest.skip(f"No se pudo crear usuario/perfil de prueba (migraciones?): {e}")
    
    # Cliente HTTP con HTTP_HOST del tenant
    client.defaults["HTTP_HOST"] = domain_name
    client.force_login(user)
    
    # Hacer petición PATCH al endpoint Core API
    url = "/api/v1/core/mi-perfil/"
    payload = {
        "cargo": "Contador Senior",
        "departamento": "Finanzas",
        "telefono_corporativo": "3009876543",
        "configuracion": {"tema": "claro", "densidad": "compacta"}
    }
    resp = client.patch(url, data=json.dumps(payload), content_type="application/json")
    
    # Verificar respuesta
    assert resp.status_code == 200, (
        f"Expected 200 OK, got {resp.status_code}. "
        f"Response: {resp.content.decode('utf-8')[:500]}"
    )
    
    # Verificar que los cambios se reflejaron
    data = resp.json()
    assert data["cargo"] == "Contador Senior", "Cargo should be updated"
    assert data["departamento"] == "Finanzas", "Departamento should be updated"
    assert data["telefono_corporativo"] == "3009876543", "Telefono should be updated"
    assert data["configuracion"]["tema"] == "claro", "Configuracion should be updated"
    
    # Verificar persistencia en BD
    with schema_context(schema_name):
        perfil = TenantProfile.objects.get(user=user)
        assert perfil.cargo == "Contador Senior", "Cargo should be persisted"
        assert perfil.departamento == "Finanzas", "Departamento should be persisted"
        assert perfil.telefono_corporativo == "3009876543", "Telefono should be persisted"


@pytest.mark.django_db
def test_core_mi_perfil_patch_multipart_returns_200(client):
    """
    Verifica que PATCH /api/v1/core/mi-perfil/ con multipart actualiza avatar y campos básicos.
    
    [WARNING] MULTI-TENANT: Usa HTTP_HOST para entrar al TENANT_URLCONF correcto.
    """
    # Crear tenant de prueba
    schema_name = "tenant_test_core_mi_perfil_multipart"
    tenant, created = TenantClient.objects.get_or_create(
        schema_name=schema_name,
        defaults={
            "name": "Test Core Mi Perfil Multipart Tenant",
            "paid_until": timezone.now().replace(year=2099),
            "on_trial": False,
        }
    )
    
    # Crear dominio para el tenant
    domain_name = "test-core-perfil-multipart.sintel.net.co"
    Domain.objects.get_or_create(
        domain=domain_name,
        tenant=tenant,
        defaults={"is_primary": True}
    )
    
    # Crear usuario y perfil en el esquema del tenant
    with schema_context(schema_name):
        try:
            user = User.objects.create_user(
                username="testuser3",
                email="test3@example.com",
                password="testpass123",
            )
            TenantProfile.objects.create(
                user=user,
                cargo="Auxiliar",
            )
        except Exception as e:
            pytest.skip(f"No se pudo crear usuario/perfil de prueba (migraciones?): {e}")
    
    # Cliente HTTP con HTTP_HOST del tenant
    client.defaults["HTTP_HOST"] = domain_name
    client.force_login(user)
    
    # Crear archivo de imagen simulado
    avatar_file = SimpleUploadedFile(
        "test_avatar.jpg",
        b"fake image content",
        content_type="image/jpeg"
    )
    
    # Hacer petición PATCH al endpoint Core API con multipart
    url = "/api/v1/core/mi-perfil/"
    payload = {
        "avatar": avatar_file,
        "cargo": "Contador",
        "departamento": "Finanzas",
        "telefono_corporativo": "3001112233",
        "configuracion": json.dumps({"tema": "oscuro"})
    }
    resp = client.patch(url, data=payload, format="multipart")
    
    # Verificar respuesta
    assert resp.status_code == 200, (
        f"Expected 200 OK, got {resp.status_code}. "
        f"Response: {resp.content.decode('utf-8')[:500]}"
    )
    
    # Verificar que los cambios se reflejaron
    data = resp.json()
    assert data["cargo"] == "Contador", "Cargo should be updated"
    assert data["departamento"] == "Finanzas", "Departamento should be updated"
    assert "avatar" in data, "Avatar should be present"
    assert data["avatar"] is not None, "Avatar should not be None"
    
    # Verificar persistencia en BD
    with schema_context(schema_name):
        perfil = TenantProfile.objects.get(user=user)
        assert perfil.cargo == "Contador", "Cargo should be persisted"
        assert perfil.avatar is not None, "Avatar should be persisted"


@pytest.mark.django_db
def test_core_mi_perfil_configuracion_patch_returns_200(client):
    """
    Verifica que PATCH /api/v1/core/mi-perfil/configuracion/ mezcla configuración.
    
    [WARNING] MULTI-TENANT: Usa HTTP_HOST para entrar al TENANT_URLCONF correcto.
    """
    # Crear tenant de prueba
    schema_name = "tenant_test_core_mi_perfil_configuracion"
    tenant, created = TenantClient.objects.get_or_create(
        schema_name=schema_name,
        defaults={
            "name": "Test Core Mi Perfil Configuracion Tenant",
            "paid_until": timezone.now().replace(year=2099),
            "on_trial": False,
        }
    )
    
    # Crear dominio para el tenant
    domain_name = "test-core-perfil-config.sintel.net.co"
    Domain.objects.get_or_create(
        domain=domain_name,
        tenant=tenant,
        defaults={"is_primary": True}
    )
    
    # Crear usuario y perfil en el esquema del tenant
    with schema_context(schema_name):
        try:
            user = User.objects.create_user(
                username="testuser4",
                email="test4@example.com",
                password="testpass123",
            )
            TenantProfile.objects.create(
                user=user,
                cargo="Auxiliar",
                configuracion={"tema": "oscuro", "densidad": "normal"}
            )
        except Exception as e:
            pytest.skip(f"No se pudo crear usuario/perfil de prueba (migraciones?): {e}")
    
    # Cliente HTTP con HTTP_HOST del tenant
    client.defaults["HTTP_HOST"] = domain_name
    client.force_login(user)
    
    # Hacer petición PATCH al endpoint de configuración (merge=True por defecto)
    url = "/api/v1/core/mi-perfil/configuracion/"
    payload = {
        "densidad": "compacta",
        "nuevo_campo": "valor"
    }
    resp = client.patch(url, data=json.dumps(payload), content_type="application/json")
    
    # Verificar respuesta
    assert resp.status_code == 200, (
        f"Expected 200 OK, got {resp.status_code}. "
        f"Response: {resp.content.decode('utf-8')[:500]}"
    )
    
    # Verificar que la configuración se mezcló correctamente
    data = resp.json()
    assert data["configuracion"]["tema"] == "oscuro", "Tema should be preserved (merge)"
    assert data["configuracion"]["densidad"] == "compacta", "Densidad should be updated"
    assert data["configuracion"]["nuevo_campo"] == "valor", "Nuevo campo should be added"
    
    # Verificar persistencia en BD
    with schema_context(schema_name):
        perfil = TenantProfile.objects.get(user=user)
        assert perfil.configuracion["tema"] == "oscuro", "Tema should be persisted"
        assert perfil.configuracion["densidad"] == "compacta", "Densidad should be persisted"
        assert perfil.configuracion["nuevo_campo"] == "valor", "Nuevo campo should be persisted"


@pytest.mark.django_db
def test_core_perfil_endpoints_401_if_not_authenticated(client):
    """
    Verifica que los endpoints Core API de perfil devuelven 401 si no está autenticado.
    
    [WARNING] SEGURIDAD: Los endpoints Core API requieren autenticación.
    """
    # Cliente HTTP sin autenticación
    # No establecer HTTP_HOST (o usar un dominio que no sea de tenant)
    
    # Test 1: mi-perfil/ GET
    url1 = "/api/v1/core/mi-perfil/"
    resp1 = client.get(url1)
    assert resp1.status_code in [401, 403], (
        f"Expected 401 or 403 from unauthenticated request for mi-perfil/, got {resp1.status_code}."
    )
    
    # Test 2: mi-perfil/ PATCH
    url2 = "/api/v1/core/mi-perfil/"
    resp2 = client.patch(url2, data=json.dumps({}), content_type="application/json")
    assert resp2.status_code in [401, 403], (
        f"Expected 401 or 403 from unauthenticated request for mi-perfil/ PATCH, got {resp2.status_code}."
    )
    
    # Test 3: mi-perfil/configuracion/ PATCH
    url3 = "/api/v1/core/mi-perfil/configuracion/"
    resp3 = client.patch(url3, data=json.dumps({}), content_type="application/json")
    assert resp3.status_code in [401, 403], (
        f"Expected 401 or 403 from unauthenticated request for mi-perfil/configuracion/, got {resp3.status_code}."
    )
