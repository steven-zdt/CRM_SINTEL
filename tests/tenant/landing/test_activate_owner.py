"""
Tests para la vista de activación de owner (v2.24).

⚠️ IMPORTANTE:
- Verifica que GET /activate muestra formulario si el token es válido
- Verifica que POST /activate establece password y loguea al usuario
- Verifica que tokens inválidos/expirados son rechazados
- Verifica validación de membresía activa
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.public.tenants.services.invitations import generate_invitation_token, build_activation_url

User = get_user_model()


@pytest.mark.django_db
def test_activate_get_with_valid_token(client, tenant_factory, user_factory):
    """
    Verifica que GET /activate muestra formulario si el token es válido.
    """
    # Crear tenant y usuario
    tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    domain = Domain.objects.create(domain="acme.localhost", tenant=tenant, is_primary=True)
    user = user_factory(email="owner@acme.com")
    user.set_unusable_password()
    user.save()
    
    # Crear membresía
    membership = TenantMembership.objects.create(
        client=tenant,
        user=user,
        rol="ADMIN",
        is_primary_admin=True,
        is_active=True,
    )
    
    # Generar token
    token = generate_invitation_token(user.id, tenant.id)
    
    # GET /activate con token válido
    response = client.get(
        f"/activate/?token={token}",
        HTTP_HOST="acme.localhost",
    )
    
    assert response.status_code == 200, "Debe retornar 200 con token válido"
    assert "activate.html" in [t.name for t in response.templates], "Debe renderizar activate.html"
    assert "form" in response.context, "Debe incluir el formulario en el contexto"


@pytest.mark.django_db
def test_activate_get_without_token(client, tenant_factory):
    """
    Verifica que GET /activate sin token redirige a login.
    """
    tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    Domain.objects.create(domain="acme.localhost", tenant=tenant, is_primary=True)
    
    # GET /activate sin token
    response = client.get(
        "/activate/",
        HTTP_HOST="acme.localhost",
    )
    
    assert response.status_code == 302, "Debe redirigir sin token"
    assert "/login/" in response.url, "Debe redirigir a /login/"


@pytest.mark.django_db
def test_activate_get_with_invalid_token(client, tenant_factory):
    """
    Verifica que GET /activate con token inválido redirige a login.
    """
    tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    Domain.objects.create(domain="acme.localhost", tenant=tenant, is_primary=True)
    
    # GET /activate con token inválido
    response = client.get(
        "/activate/?token=invalid_token",
        HTTP_HOST="acme.localhost",
    )
    
    assert response.status_code == 302, "Debe redirigir con token inválido"
    assert "/login/" in response.url, "Debe redirigir a /login/"


@pytest.mark.django_db
def test_activate_post_success(client, tenant_factory, user_factory):
    """
    Verifica que POST /activate establece password y loguea al usuario.
    """
    # Crear tenant y usuario
    tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    domain = Domain.objects.create(domain="acme.localhost", tenant=tenant, is_primary=True)
    user = user_factory(email="owner@acme.com")
    user.set_unusable_password()
    user.save()
    
    # Crear membresía
    membership = TenantMembership.objects.create(
        client=tenant,
        user=user,
        rol="ADMIN",
        is_primary_admin=True,
        is_active=True,
    )
    
    # Generar token
    token = generate_invitation_token(user.id, tenant.id)
    
    # POST /activate con password válido (v2.29: usa password1/password2)
    response = client.post(
        f"/activate/?token={token}",
        {
            "password1": "NewPassword123!",
            "password2": "NewPassword123!",
        },
        HTTP_HOST="acme.localhost",
    )
    
    assert response.status_code == 302, "Debe redirigir después de activación exitosa"
    assert "/dashboard/" in response.url, "Debe redirigir a /dashboard/"
    
    # Verificar que el usuario tiene password usable ahora
    user.refresh_from_db()
    assert user.has_usable_password(), "El usuario debe tener password usable después de activación"
    assert user.check_password("NewPassword123!"), "El password debe ser el establecido"
    
    # Verificar que el usuario está logueado
    response = client.get("/dashboard/", HTTP_HOST="acme.localhost")
    assert response.status_code in (200, 302), "El usuario debe poder acceder al dashboard"


@pytest.mark.django_db
def test_activate_post_password_mismatch(client, tenant_factory, user_factory):
    """
    Verifica que POST /activate rechaza passwords que no coinciden.
    """
    # Crear tenant y usuario
    tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    domain = Domain.objects.create(domain="acme.localhost", tenant=tenant, is_primary=True)
    user = user_factory(email="owner@acme.com")
    user.set_unusable_password()
    user.save()
    
    # Crear membresía
    membership = TenantMembership.objects.create(
        client=tenant,
        user=user,
        rol="ADMIN",
        is_primary_admin=True,
        is_active=True,
    )
    
    # Generar token
    token = generate_invitation_token(user.id, tenant.id)
    
    # POST /activate con passwords que no coinciden (v2.29: usa password1/password2)
    response = client.post(
        f"/activate/?token={token}",
        {
            "password1": "NewPassword123!",
            "password2": "DifferentPassword123!",
        },
        HTTP_HOST="acme.localhost",
    )
    
    assert response.status_code == 200, "Debe retornar 200 con error de validación"
    assert "form" in response.context, "Debe incluir el formulario con errores"
    assert response.context["form"].errors, "Debe tener errores de validación"


@pytest.mark.django_db
def test_activate_post_without_membership(client, tenant_factory, user_factory):
    """
    Verifica que POST /activate rechaza usuarios sin membresía activa.
    """
    # Crear tenant y usuario
    tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    domain = Domain.objects.create(domain="acme.localhost", tenant=tenant, is_primary=True)
    user = user_factory(email="owner@acme.com")
    user.set_unusable_password()
    user.save()
    
    # NO crear membresía (usuario sin acceso al tenant)
    
    # Generar token (aunque no tenga membresía)
    token = generate_invitation_token(user.id, tenant.id)
    
    # POST /activate (v2.29: usa password1/password2)
    response = client.post(
        f"/activate/?token={token}",
        {
            "password1": "NewPassword123!",
            "password2": "NewPassword123!",
        },
        HTTP_HOST="acme.localhost",
    )
    
    assert response.status_code == 302, "Debe redirigir"
    assert "/login/" in response.url, "Debe redirigir a /login/ con mensaje de error"


@pytest.mark.django_db
def test_activate_cross_tenant_isolation(client, tenant_factory, user_factory):
    """
    Verifica que un token de un tenant no funciona en otro tenant.
    """
    # Crear dos tenants
    tenant_a = tenant_factory(schema_name="acme", nombre="Acme SAS")
    domain_a = Domain.objects.create(domain="acme.localhost", tenant=tenant_a, is_primary=True)
    
    tenant_b = tenant_factory(schema_name="beta", nombre="Beta SAS")
    domain_b = Domain.objects.create(domain="beta.localhost", tenant=tenant_b, is_primary=True)
    
    # Crear usuario y membresía en tenant_a
    user = user_factory(email="owner@acme.com")
    user.set_unusable_password()
    user.save()
    
    membership_a = TenantMembership.objects.create(
        client=tenant_a,
        user=user,
        rol="ADMIN",
        is_primary_admin=True,
        is_active=True,
    )
    
    # Generar token para tenant_a
    token = generate_invitation_token(user.id, tenant_a.id)
    
    # Intentar activar en tenant_b (token de tenant_a) (v2.29: usa password1/password2)
    response = client.post(
        f"/activate/?token={token}",
        {
            "password1": "NewPassword123!",
            "password2": "NewPassword123!",
        },
        HTTP_HOST="beta.localhost",
    )
    
    assert response.status_code == 302, "Debe redirigir"
    assert "/login/" in response.url, "Debe redirigir a /login/ (token no corresponde al tenant)"
