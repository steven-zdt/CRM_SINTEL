"""
Tests para el flujo de activación API-First (v2.30).

[WARNING] v2.30: Cambios en el comportamiento de activación:
- Endpoint API: GET/POST /api/v1/landing/auth/activate/?token=...
- GET retorna 409 CONFLICT si el usuario ya tiene contraseña usable
- POST retorna 409 CONFLICT si el usuario ya tiene contraseña usable
- Una sola activación: si has_usable_password()==True → 409
- Redirect absoluto al dashboard después de activación exitosa
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.public.tenants.services.invitations import generate_invitation_token, verify_invitation_token

User = get_user_model()


@pytest.mark.django_db
def test_activate_get_200_when_no_usable_password(client, tenant_factory, user_factory):
    """
    GET /api/v1/landing/auth/activate/?token=... con token válido y usuario SIN password usable
    debe retornar 200 con información del usuario y tenant.
    """
    # Crear tenant y usuario SIN password usable
    tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    domain = Domain.objects.create(domain="acme.localhost", tenant=tenant, is_primary=True)
    user = user_factory(email="owner@acme.com")
    user.set_unusable_password()  # [WARNING] Sin password usable
    user.save()
    
    # Crear membresía
    TenantMembership.objects.create(
        client=tenant,
        user=user,
        rol="ADMIN",
        is_primary_admin=True,
        is_active=True,
    )
    
    # Generar token
    token = generate_invitation_token(user.id, tenant.id)
    
    # GET /api/v1/landing/auth/activate/?token=...
    response = client.get(
        f"/api/v1/landing/auth/activate/?token={token}",
        HTTP_HOST="acme.localhost",
    )
    
    # Debe retornar 200 con información
    assert response.status_code == 200, "Debe retornar 200 con token válido y sin password usable"
    data = response.json()
    assert data["token_valid"] is True
    assert data["user"]["email"] == "owner@acme.com"
    assert data["user"]["has_usable_password"] is False
    assert data["tenant"]["nombre"] == "Acme SAS"


@pytest.mark.django_db
def test_activate_get_409_when_has_usable_password(client, tenant_factory, user_factory):
    """
    GET /api/v1/landing/auth/activate/?token=... con token válido y usuario CON password usable
    debe retornar 409 CONFLICT indicando que la cuenta ya fue activada.
    """
    # Crear tenant y usuario CON password usable
    tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    domain = Domain.objects.create(domain="acme.localhost", tenant=tenant, is_primary=True)
    user = user_factory(email="owner@acme.com")
    user.set_password("ExistingPassword123!")  # [WARNING] Password usable
    user.save()
    
    # Crear membresía
    TenantMembership.objects.create(
        client=tenant,
        user=user,
        rol="ADMIN",
        is_primary_admin=True,
        is_active=True,
    )
    
    # Generar token
    token = generate_invitation_token(user.id, tenant.id)
    
    # GET /api/v1/landing/auth/activate/?token=...
    response = client.get(
        f"/api/v1/landing/auth/activate/?token={token}",
        HTTP_HOST="acme.localhost",
    )
    
    # [WARNING] v2.30: Debe retornar 409 CONFLICT
    assert response.status_code == 409, "Debe retornar 409 si ya tiene password usable"
    data = response.json()
    assert "ya fue activada" in data["detail"].lower() or "cuenta ya activada" in data["detail"].lower()
    assert data["redirect_url"] == "/login/", f"Expected redirect_url='/login/', got '{data.get('redirect_url')}'"
    assert "login_api_url" in data  # v2.30: URL de la API de login para referencia


@pytest.mark.django_db
def test_activate_get_400_invalid_token(client, tenant_factory):
    """
    GET /api/v1/landing/auth/activate/?token=... con token inválido
    debe retornar 400 BAD REQUEST.
    """
    tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    domain = Domain.objects.create(domain="acme.localhost", tenant=tenant, is_primary=True)
    
    # GET con token inválido
    response = client.get(
        "/api/v1/landing/auth/activate/?token=invalid_token_12345",
        HTTP_HOST="acme.localhost",
    )
    
    # Debe retornar 400
    assert response.status_code == 400, "Debe retornar 400 con token inválido"
    data = response.json()
    assert "inválido" in data["detail"].lower() or "expirado" in data["detail"].lower()


@pytest.mark.django_db
def test_activate_post_200_success(client, tenant_factory, user_factory):
    """
    POST /api/v1/landing/auth/activate/?token=... con datos válidos
    debe establecer password, loguear usuario y retornar redirect_url ABSOLUTA.
    """
    # Crear tenant y usuario SIN password usable
    tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    domain = Domain.objects.create(domain="acme.localhost", tenant=tenant, is_primary=True)
    user = user_factory(email="owner@acme.com")
    user.set_unusable_password()
    user.save()
    
    # Crear membresía
    TenantMembership.objects.create(
        client=tenant,
        user=user,
        rol="ADMIN",
        is_primary_admin=True,
        is_active=True,
    )
    
    # Generar token
    token = generate_invitation_token(user.id, tenant.id)
    
    # POST /api/v1/landing/auth/activate/?token=...
    response = client.post(
        f"/api/v1/landing/auth/activate/?token={token}",
        {
            "password1": "NewPassword123!",
            "password2": "NewPassword123!",
        },
        HTTP_HOST="acme.localhost",
        content_type="application/json",
    )
    
    # Debe retornar 200 con redirect_url absoluta
    assert response.status_code == 200, "Debe retornar 200 después de activación exitosa"
    data = response.json()
    assert "redirect_url" in data
    assert data["redirect_url"].startswith("http://") or data["redirect_url"].startswith("https://")
    assert "/dashboard/" in data["redirect_url"]
    assert "acme.localhost" in data["redirect_url"]
    
    # Verificar que la contraseña fue establecida
    user.refresh_from_db()
    assert user.has_usable_password(), "El usuario debe tener password usable"
    assert user.check_password("NewPassword123!"), "El password debe ser el establecido"
    
    # Verificar que el usuario está logueado
    assert "_auth_user_id" in client.session, "El usuario debe estar logueado"


@pytest.mark.django_db
def test_activate_post_409_when_has_usable_password(client, tenant_factory, user_factory):
    """
    POST /api/v1/landing/auth/activate/?token=... con usuario que ya tiene password usable
    debe retornar 409 CONFLICT.
    """
    # Crear tenant y usuario CON password usable
    tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    domain = Domain.objects.create(domain="acme.localhost", tenant=tenant, is_primary=True)
    user = user_factory(email="owner@acme.com")
    user.set_password("ExistingPassword123!")  # [WARNING] Password usable
    user.save()
    
    # Crear membresía
    TenantMembership.objects.create(
        client=tenant,
        user=user,
        rol="ADMIN",
        is_primary_admin=True,
        is_active=True,
    )
    
    # Generar token
    token = generate_invitation_token(user.id, tenant.id)
    
    # POST /api/v1/landing/auth/activate/?token=...
    response = client.post(
        f"/api/v1/landing/auth/activate/?token={token}",
        {
            "password1": "NewPassword123!",
            "password2": "NewPassword123!",
        },
        HTTP_HOST="acme.localhost",
        content_type="application/json",
    )
    
    # [WARNING] v2.30: Debe retornar 409 CONFLICT
    assert response.status_code == 409, "Debe retornar 409 si ya tiene password usable"
    data = response.json()
    assert "ya fue activada" in data["detail"].lower() or "cuenta ya activada" in data["detail"].lower()
    assert data["redirect_url"] == "/login/", f"Expected redirect_url='/login/', got '{data.get('redirect_url')}'"
    assert "login_api_url" in data  # v2.30: URL de la API de login para referencia
    
    # Verificar que la contraseña NO fue cambiada
    user.refresh_from_db()
    assert user.check_password("ExistingPassword123!"), "El password original debe mantenerse"


@pytest.mark.django_db
def test_activate_post_400_invalid_token(client, tenant_factory):
    """
    POST /api/v1/landing/auth/activate/?token=... con token inválido
    debe retornar 400 BAD REQUEST.
    """
    tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    domain = Domain.objects.create(domain="acme.localhost", tenant=tenant, is_primary=True)
    
    # POST con token inválido
    response = client.post(
        "/api/v1/landing/auth/activate/?token=invalid_token_12345",
        {
            "password1": "NewPassword123!",
            "password2": "NewPassword123!",
        },
        HTTP_HOST="acme.localhost",
        content_type="application/json",
    )
    
    # Debe retornar 400
    assert response.status_code == 400, "Debe retornar 400 con token inválido"
    data = response.json()
    assert "inválido" in data["detail"].lower() or "expirado" in data["detail"].lower()


@pytest.mark.django_db
def test_activate_post_400_passwords_mismatch(client, tenant_factory, user_factory):
    """
    POST /api/v1/landing/auth/activate/?token=... con password1 != password2
    debe retornar 400 BAD REQUEST.
    """
    # Crear tenant y usuario SIN password usable
    tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    domain = Domain.objects.create(domain="acme.localhost", tenant=tenant, is_primary=True)
    user = user_factory(email="owner@acme.com")
    user.set_unusable_password()
    user.save()
    
    # Crear membresía
    TenantMembership.objects.create(
        client=tenant,
        user=user,
        rol="ADMIN",
        is_primary_admin=True,
        is_active=True,
    )
    
    # Generar token
    token = generate_invitation_token(user.id, tenant.id)
    
    # POST con passwords que no coinciden
    response = client.post(
        f"/api/v1/landing/auth/activate/?token={token}",
        {
            "password1": "Password123!",
            "password2": "DifferentPassword123!",
        },
        HTTP_HOST="acme.localhost",
        content_type="application/json",
    )
    
    # Debe retornar 400
    assert response.status_code == 400, "Debe retornar 400 si passwords no coinciden"
    data = response.json()
    assert "password2" in data or "no coinciden" in str(data).lower()


@pytest.mark.django_db
def test_activate_post_400_password_too_short(client, tenant_factory, user_factory):
    """
    POST /api/v1/landing/auth/activate/?token=... con password menor a 8 caracteres
    debe retornar 400 BAD REQUEST.
    """
    # Crear tenant y usuario SIN password usable
    tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    domain = Domain.objects.create(domain="acme.localhost", tenant=tenant, is_primary=True)
    user = user_factory(email="owner@acme.com")
    user.set_unusable_password()
    user.save()
    
    # Crear membresía
    TenantMembership.objects.create(
        client=tenant,
        user=user,
        rol="ADMIN",
        is_primary_admin=True,
        is_active=True,
    )
    
    # Generar token
    token = generate_invitation_token(user.id, tenant.id)
    
    # POST con password muy corto
    response = client.post(
        f"/api/v1/landing/auth/activate/?token={token}",
        {
            "password1": "Short1!",
            "password2": "Short1!",
        },
        HTTP_HOST="acme.localhost",
        content_type="application/json",
    )
    
    # Debe retornar 400
    assert response.status_code == 400, "Debe retornar 400 si password es muy corto"
    data = response.json()
    assert "password" in data or "mínimo" in str(data).lower() or "8" in str(data)


@pytest.mark.django_db
def test_activate_redirect_url_absolute(client, tenant_factory, user_factory):
    """
    [WARNING] v2.27: POST /api/v1/landing/auth/activate/?token=... debe retornar redirect_url ABSOLUTA.
    """
    # Crear tenant y usuario SIN password usable
    tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    domain = Domain.objects.create(domain="acme.localhost", tenant=tenant, is_primary=True)
    user = user_factory(email="owner@acme.com")
    user.set_unusable_password()
    user.save()
    
    # Crear membresía
    TenantMembership.objects.create(
        client=tenant,
        user=user,
        rol="ADMIN",
        is_primary_admin=True,
        is_active=True,
    )
    
    # Generar token
    token = generate_invitation_token(user.id, tenant.id)
    
    # POST /api/v1/landing/auth/activate/?token=...
    response = client.post(
        f"/api/v1/landing/auth/activate/?token={token}",
        {
            "password1": "NewPassword123!",
            "password2": "NewPassword123!",
        },
        HTTP_HOST="acme.localhost",
        content_type="application/json",
    )
    
    # Verificar redirect absoluto
    assert response.status_code == 200, "Debe retornar 200"
    data = response.json()
    redirect_url = data["redirect_url"]
    
    assert redirect_url.startswith("http://") or redirect_url.startswith("https://"), \
        "Debe ser URL absoluta (v2.27)"
    assert "/dashboard/" in redirect_url, "Debe redirigir al dashboard"
    assert "acme.localhost" in redirect_url, "Debe incluir el dominio del tenant"
    
    # Nota: No seguimos el redirect porque requiere configuración adicional de URLs
    # La validación de la URL absoluta es suficiente para verificar v2.27
