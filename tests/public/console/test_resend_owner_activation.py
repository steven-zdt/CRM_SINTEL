"""
Tests para el endpoint de reenvío de token de activación del owner desde la consola.

[WARNING] v2.30: Endpoint API-First para reenviar tokens de activación.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django_tenants.utils import schema_context, get_public_schema_name
from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.public.console.models import ConsoleActionLog

User = get_user_model()


@pytest.mark.django_db
def test_resend_activation_200_when_unusable_password(client, admin_user):
    """
    POST /api/admin/v1/console/tenants/{tenant_id}/owner/resend-activation/
    con usuario SIN password usable debe retornar 200 y enviar email.
    """
    with schema_context(get_public_schema_name()):
        # Crear tenant y owner sin password usable
        tenant = Client.objects.create(
            schema_name="test_tenant",
            nombre="Test Tenant",
            is_active=True
        )
        domain = Domain.objects.create(
            domain="test.localhost",
            tenant=tenant,
            is_primary=True
        )
        owner = User.objects.create(
            email="owner@test.com",
            is_active=True
        )
        owner.set_unusable_password()
        owner.save()
        
        TenantMembership.objects.create(
            client=tenant,
            user=owner,
            rol="ADMIN",
            is_primary_admin=True,
            is_active=True
        )
    
    # Autenticar como admin
    client.force_login(admin_user)
    
    # Mock del envío de email
    with patch('apps.public.console.api.views.ResendOwnerActivationAPIView._send_email') as mock_send:
        mock_send.return_value = True
        
        # POST al endpoint
        response = client.post(
            f"/api/admin/v1/console/tenants/{tenant.id}/owner/resend-activation/",
            {"ttl_minutes": 120},
            content_type="application/json"
        )
    
    # Debe retornar 200
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.data}"
    data = response.json()
    assert "activation_url" in data
    assert data["owner_email"] == "owner@test.com"
    assert data["tenant_domain"] == "test.localhost"
    assert "/api/v1/landing/auth/activate/?token=" in data["activation_url"]
    
    # Verificar que se intentó enviar el email
    mock_send.assert_called_once()
    
    # Verificar auditoría
    with schema_context(get_public_schema_name()):
        log = ConsoleActionLog.objects.filter(
            action="RESEND_OWNER_ACTIVATION",
            tenant=tenant,
            target_user=owner
        ).first()
        assert log is not None
        assert log.actor == admin_user


@pytest.mark.django_db
def test_resend_activation_409_when_has_usable_password(client, admin_user):
    """
    POST /api/admin/v1/console/tenants/{tenant_id}/owner/resend-activation/
    con usuario CON password usable debe retornar 409.
    """
    with schema_context(get_public_schema_name()):
        tenant = Client.objects.create(
            schema_name="test_tenant",
            nombre="Test Tenant",
            is_active=True
        )
        domain = Domain.objects.create(
            domain="test.localhost",
            tenant=tenant,
            is_primary=True
        )
        owner = User.objects.create(
            email="owner@test.com",
            is_active=True
        )
        owner.set_password("ExistingPassword123!")
        owner.save()
        
        TenantMembership.objects.create(
            client=tenant,
            user=owner,
            rol="ADMIN",
            is_primary_admin=True,
            is_active=True
        )
    
    client.force_login(admin_user)
    
    response = client.post(
        f"/api/admin/v1/console/tenants/{tenant.id}/owner/resend-activation/",
        {"ttl_minutes": 120},
        content_type="application/json"
    )
    
    # Debe retornar 409
    assert response.status_code == 409
    data = response.json()
    assert "ya fue activada" in data["detail"].lower()
    assert data["owner_email"] == "owner@test.com"


@pytest.mark.django_db
def test_resend_activation_429_rate_limit(client, admin_user):
    """
    POST /api/admin/v1/console/tenants/{tenant_id}/owner/resend-activation/
    con rate limit excedido debe retornar 429.
    """
    with schema_context(get_public_schema_name()):
        tenant = Client.objects.create(
            schema_name="test_tenant",
            nombre="Test Tenant",
            is_active=True
        )
        domain = Domain.objects.create(
            domain="test.localhost",
            tenant=tenant,
            is_primary=True
        )
        owner = User.objects.create(
            email="owner@test.com",
            is_active=True
        )
        owner.set_unusable_password()
        owner.save()
        
        TenantMembership.objects.create(
            client=tenant,
            user=owner,
            rol="ADMIN",
            is_primary_admin=True,
            is_active=True
        )
        
        # Crear log reciente (dentro del rate limit)
        ConsoleActionLog.objects.create(
            action="RESEND_OWNER_ACTIVATION",
            actor=admin_user,
            tenant=tenant,
            target_user=owner,
            created_at=timezone.now() - timedelta(minutes=2)  # Hace 2 minutos
        )
    
    client.force_login(admin_user)
    
    response = client.post(
        f"/api/admin/v1/console/tenants/{tenant.id}/owner/resend-activation/",
        {"ttl_minutes": 120},
        content_type="application/json"
    )
    
    # Debe retornar 429
    assert response.status_code == 429
    data = response.json()
    assert "demasiadas solicitudes" in data["detail"].lower()


@pytest.mark.django_db
def test_resend_activation_404_tenant_not_found(client, admin_user):
    """
    POST /api/admin/v1/console/tenants/{tenant_id}/owner/resend-activation/
    con tenant inexistente debe retornar 404.
    """
    client.force_login(admin_user)
    
    response = client.post(
        "/api/admin/v1/console/tenants/99999/owner/resend-activation/",
        {"ttl_minutes": 120},
        content_type="application/json"
    )
    
    assert response.status_code == 404
    data = response.json()
    assert "no encontrado" in data["detail"].lower()


@pytest.mark.django_db
def test_resend_activation_404_owner_not_found(client, admin_user):
    """
    POST /api/admin/v1/console/tenants/{tenant_id}/owner/resend-activation/
    con tenant sin owner debe retornar 404.
    """
    with schema_context(get_public_schema_name()):
        tenant = Client.objects.create(
            schema_name="test_tenant",
            nombre="Test Tenant",
            is_active=True
        )
        domain = Domain.objects.create(
            domain="test.localhost",
            tenant=tenant,
            is_primary=True
        )
        # No crear owner
    
    client.force_login(admin_user)
    
    response = client.post(
        f"/api/admin/v1/console/tenants/{tenant.id}/owner/resend-activation/",
        {"ttl_minutes": 120},
        content_type="application/json"
    )
    
    assert response.status_code == 404
    data = response.json()
    assert "owner" in data["detail"].lower() and "no encontrado" in data["detail"].lower()


@pytest.mark.django_db
def test_resend_activation_200_dry_run(client, admin_user):
    """
    POST /api/admin/v1/console/tenants/{tenant_id}/owner/resend-activation/?dry_run=true
    debe retornar 200 con activation_url sin enviar email.
    """
    with schema_context(get_public_schema_name()):
        tenant = Client.objects.create(
            schema_name="test_tenant",
            nombre="Test Tenant",
            is_active=True
        )
        domain = Domain.objects.create(
            domain="test.localhost",
            tenant=tenant,
            is_primary=True
        )
        owner = User.objects.create(
            email="owner@test.com",
            is_active=True
        )
        owner.set_unusable_password()
        owner.save()
        
        TenantMembership.objects.create(
            client=tenant,
            user=owner,
            rol="ADMIN",
            is_primary_admin=True,
            is_active=True
        )
    
    client.force_login(admin_user)
    
    # Mock del envío de email (no debe llamarse)
    with patch('apps.public.console.api.views.ResendOwnerActivationAPIView._send_email') as mock_send:
        response = client.post(
            f"/api/admin/v1/console/tenants/{tenant.id}/owner/resend-activation/?dry_run=true",
            {"ttl_minutes": 120},
            content_type="application/json"
        )
        
        # No debe llamarse el envío de email
        mock_send.assert_not_called()
    
    assert response.status_code == 200
    data = response.json()
    assert "activation_url" in data
    assert "/api/v1/landing/auth/activate/?token=" in data["activation_url"]
    assert "DRY RUN" in data["detail"].upper()


@pytest.mark.django_db
def test_resend_activation_url_api_first(client, admin_user):
    """
    Verificar que la URL de activación siempre apunta a la API-first.
    """
    with schema_context(get_public_schema_name()):
        tenant = Client.objects.create(
            schema_name="test_tenant",
            nombre="Test Tenant",
            is_active=True
        )
        domain = Domain.objects.create(
            domain="test.localhost",
            tenant=tenant,
            is_primary=True
        )
        owner = User.objects.create(
            email="owner@test.com",
            is_active=True
        )
        owner.set_unusable_password()
        owner.save()
        
        TenantMembership.objects.create(
            client=tenant,
            user=owner,
            rol="ADMIN",
            is_primary_admin=True,
            is_active=True
        )
    
    client.force_login(admin_user)
    
    with patch('apps.public.console.api.views.ResendOwnerActivationAPIView._send_email'):
        response = client.post(
            f"/api/admin/v1/console/tenants/{tenant.id}/owner/resend-activation/",
            {"ttl_minutes": 120},
            content_type="application/json"
        )
    
    assert response.status_code == 200
    data = response.json()
    activation_url = data["activation_url"]
    
    # Verificar que la URL es API-first
    assert activation_url.startswith("http://") or activation_url.startswith("https://")
    assert "/api/v1/landing/auth/activate/?token=" in activation_url
    assert "test.localhost" in activation_url
    # Verificar que NO apunta a rutas HTML legacy
    assert "/activate?token=" not in activation_url
    assert "/activate/?token=" not in activation_url
