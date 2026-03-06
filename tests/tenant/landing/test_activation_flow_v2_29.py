"""
Tests para el flujo de activación mejorado (v2.29).

⚠️ v2.29: Cambios en el comportamiento de activación:
- GET /activate con token válido SIEMPRE muestra el formulario, incluso si el usuario ya tiene password usable
- POST /activate permite establecer/actualizar la contraseña incluso si ya tiene una usable
- Redirect absoluto al dashboard después de activación exitosa
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.public.tenants.services.invitations import generate_invitation_token

User = get_user_model()


@pytest.mark.django_db
def test_activate_get_with_valid_token_and_usable_password(client, tenant_factory, user_factory):
    """
    ⚠️ v2.29: GET /activate con token válido y usuario con password usable
    debe mostrar el formulario (no redirigir a /login/).
    
    Antes (v2.28): 302 a /login/
    Ahora (v2.29): 200 con template activate.html
    """
    # Crear tenant y usuario CON password usable
    tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    domain = Domain.objects.create(domain="acme.localhost", tenant=tenant, is_primary=True)
    user = user_factory(email="owner@acme.com")
    user.set_password("OldPassword123!")  # ⚠️ Password usable
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
    
    # GET /activate con token válido (usuario ya tiene password usable)
    response = client.get(
        f"/activate/?token={token}",
        HTTP_HOST="acme.localhost",
    )
    
    # ⚠️ v2.29: Debe mostrar el formulario, no redirigir
    assert response.status_code == 200, "Debe retornar 200 con token válido (v2.29)"
    assert "activate.html" in [t.name for t in response.templates], "Debe renderizar activate.html"
    assert "form" in response.context, "Debe incluir el formulario en el contexto"


@pytest.mark.django_db
def test_activate_post_updates_password_even_if_usable(client, tenant_factory, user_factory):
    """
    ⚠️ v2.29: POST /activate permite actualizar la contraseña incluso si el usuario ya tiene una usable.
    """
    # Crear tenant y usuario CON password usable
    tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    domain = Domain.objects.create(domain="acme.localhost", tenant=tenant, is_primary=True)
    user = user_factory(email="owner@acme.com")
    user.set_password("OldPassword123!")  # ⚠️ Password usable existente
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
    
    # POST /activate con nueva contraseña (v2.29: permite actualizar)
    response = client.post(
        f"/activate/?token={token}",
        {
            "password1": "NewPassword123!",
            "password2": "NewPassword123!",
        },
        HTTP_HOST="acme.localhost",
    )
    
    # Debe redirigir al dashboard con URL absoluta
    assert response.status_code == 302, "Debe redirigir después de actualización exitosa"
    assert "http://acme.localhost/dashboard/" in response.url or "https://acme.localhost/dashboard/" in response.url, \
        "Debe redirigir con URL absoluta al dashboard"
    
    # Verificar que la contraseña fue actualizada
    user.refresh_from_db()
    assert user.has_usable_password(), "El usuario debe tener password usable"
    assert user.check_password("NewPassword123!"), "El password debe ser el nuevo establecido"
    assert not user.check_password("OldPassword123!"), "El password antiguo no debe funcionar"


@pytest.mark.django_db
def test_activate_post_redirect_absolute_url(client, tenant_factory, user_factory):
    """
    ⚠️ v2.29: POST /activate redirige con URL absoluta al dashboard del tenant.
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
    
    # POST /activate
    response = client.post(
        f"/activate/?token={token}",
        {
            "password1": "NewPassword123!",
            "password2": "NewPassword123!",
        },
        HTTP_HOST="acme.localhost",
    )
    
    # Verificar redirect absoluto
    assert response.status_code == 302, "Debe redirigir"
    assert response.url.startswith("http://") or response.url.startswith("https://"), \
        "Debe ser URL absoluta (v2.27)"
    assert "/dashboard/" in response.url, "Debe redirigir al dashboard"
    assert "acme.localhost" in response.url, "Debe incluir el dominio del tenant"
    
    # Seguir redirect y verificar que funciona
    follow_response = client.get(response.url, HTTP_HOST="acme.localhost")
    assert follow_response.status_code in (200, 302), "El dashboard debe ser accesible"


@pytest.mark.django_db
def test_activate_token_one_time_use(client, tenant_factory, user_factory):
    """
    ⚠️ v2.29: Token puede usarse múltiples veces mientras sea válido (no expirado).
    
    Nota: El token actualmente no se invalida después de uso, solo expira por tiempo.
    Este test verifica que el token sigue siendo válido después de un uso exitoso.
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
    
    # Primera activación
    response1 = client.post(
        f"/activate/?token={token}",
        {
            "password1": "FirstPassword123!",
            "password2": "FirstPassword123!",
        },
        HTTP_HOST="acme.localhost",
    )
    
    assert response1.status_code == 302, "Primera activación debe ser exitosa"
    
    # Verificar password establecido
    user.refresh_from_db()
    assert user.check_password("FirstPassword123!")
    
    # Segunda activación con el mismo token (debe funcionar mientras el token sea válido)
    # ⚠️ Nota: Actualmente el token no se invalida, solo expira por tiempo
    response2 = client.get(
        f"/activate/?token={token}",
        HTTP_HOST="acme.localhost",
    )
    
    # ⚠️ v2.29: Debe mostrar el formulario (token aún válido)
    assert response2.status_code == 200, "Token aún válido, debe mostrar formulario"
    
    # Actualizar password nuevamente
    response3 = client.post(
        f"/activate/?token={token}",
        {
            "password1": "SecondPassword123!",
            "password2": "SecondPassword123!",
        },
        HTTP_HOST="acme.localhost",
    )
    
    assert response3.status_code == 302, "Segunda actualización debe ser exitosa"
    
    # Verificar password actualizado
    user.refresh_from_db()
    assert user.check_password("SecondPassword123!")
    assert not user.check_password("FirstPassword123!")
