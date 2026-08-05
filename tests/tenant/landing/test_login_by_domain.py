"""
Tests para login por dominio del tenant.

Verifica que:
- /login/ está disponible bajo el dominio del tenant
- Login exitoso redirige a /dashboard/
- Usuario sin membresía recibe 403 o redirección
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.urls import reverse

from apps.public.tenants.models import Client, Domain, TenantMembership

User = get_user_model()

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.urls("config.urls_tenant"),
]


@pytest.fixture
def tenant_with_domain(db):
    """Crea un tenant con dominio para tests."""
    connection.set_schema_to_public()

    tenant = Client.objects.create(
        nombre="Cliente Test", schema_name="cliente_test", is_active=True, on_trial=True
    )

    Domain.objects.create(
        tenant=tenant, domain="cliente-test.localhost", is_primary=True
    )

    return tenant


@pytest.fixture
def user_owner(db):
    """Crea un usuario propietario del tenant."""
    connection.set_schema_to_public()
    return User.objects.create_user(
        email="owner@cliente-test.com",
        password="Secr3tPass!",
        is_staff=False,
        is_active=True,
    )


@pytest.fixture
def user_without_membership(db):
    """Crea un usuario SIN membresía en el tenant."""
    connection.set_schema_to_public()
    return User.objects.create_user(
        email="user@none.com", password="Secr3tPass!", is_staff=False, is_active=True
    )


@pytest.fixture
def membership(db, tenant_with_domain, user_owner):
    """Crea membresía activa para el usuario propietario."""
    connection.set_schema_to_public()
    return TenantMembership.objects.create(
        client=tenant_with_domain,
        user=user_owner,
        rol="ADMIN",
        is_primary_admin=True,
        is_active=True,
    )


def test_login_route_available(client, tenant_with_domain):
    """
    Test A: /login/ está disponible bajo el dominio del tenant.

    Objetivo: Verificar que la ruta /login/ responde correctamente
    cuando se accede desde el dominio del tenant.
    """
    response = client.get("/login/", HTTP_HOST="cliente-test.localhost")

    # Debe retornar 200 (formulario) o 302 (redirección si ya está autenticado)
    assert response.status_code in (
        200,
        302,
    ), f"Se esperaba 200 o 302, pero se recibió {response.status_code}"


def test_login_success_redirects_to_dashboard(
    client, tenant_with_domain, user_owner, membership
):
    """
    Test B: Login exitoso redirige a /dashboard/.

    Objetivo: Verificar que después de un login exitoso, el usuario
    es redirigido al dashboard del tenant.
    """
    # Intentar login
    response = client.post(
        "/login/",
        {
            "username": user_owner.email,  # Usar email como username
            "password": "Secr3tPass!",
        },
        HTTP_HOST="cliente-test.localhost",
    )

    # Debe retornar 302 (redirección) o 303
    assert response.status_code in (302, 303), (
        f"Se esperaba 302 o 303, pero se recibió {response.status_code}. "
        f"Respuesta: {response.content.decode('utf-8')[:200]}"
    )

    # Verificar que redirige a /dashboard/
    location = response.headers.get("Location", "")
    assert (
        location.endswith("/dashboard/") or "/dashboard/" in location
    ), f"Se esperaba redirección a /dashboard/, pero se recibió: {location}"


def test_forbidden_without_membership(
    client, tenant_with_domain, user_without_membership
):
    """
    Test C: Usuario sin membresía → 403 o redirección.

    Objetivo: Verificar que un usuario autenticado pero sin membresía
    en el tenant recibe 403 o es redirigido a /login/.
    """
    # Intentar login (puede fallar en authenticate si TenantAwareBackend está activo)
    login_response = client.post(
        "/login/",
        {
            "username": user_without_membership.email,
            "password": "Secr3tPass!",
        },
        HTTP_HOST="cliente-test.localhost",
    )

    # Si el login falla (por TenantAwareBackend), el usuario no se autentica
    # Si el login pasa pero no hay membresía, el middleware debe bloquear

    # Intentar acceder al dashboard directamente (simulando usuario autenticado)
    # Primero autenticamos manualmente para bypassear TenantAwareBackend
    client.force_login(user_without_membership)

    # Intentar acceder al dashboard
    dashboard_response = client.get("/dashboard/", HTTP_HOST="cliente-test.localhost")

    # Debe retornar 403 o redirección a /login/
    assert dashboard_response.status_code in (
        302,
        403,
    ), f"Se esperaba 302 o 403, pero se recibió {dashboard_response.status_code}"

    if dashboard_response.status_code == 302:
        location = dashboard_response.headers.get("Location", "")
        assert (
            "/login/" in location
        ), f"Se esperaba redirección a /login/, pero se recibió: {location}"


def test_login_with_invalid_credentials(client, tenant_with_domain):
    """
    Test D: Login con credenciales inválidas retorna error.

    Objetivo: Verificar que intentar login con credenciales incorrectas
    muestra un error en el formulario.
    """
    response = client.post(
        "/login/",
        {
            "username": "nonexistent@test.com",
            "password": "WrongPassword!",
        },
        HTTP_HOST="cliente-test.localhost",
    )

    # Debe retornar 200 con errores en el formulario (no redirección)
    assert (
        response.status_code == 200
    ), f"Se esperaba 200 con errores, pero se recibió {response.status_code}"

    # Verificar que hay errores en la respuesta
    content = response.content.decode("utf-8")
    assert (
        "error" in content.lower()
        or "inválid" in content.lower()
        or "incorrect" in content.lower()
    ), "Se esperaba un mensaje de error en la respuesta"


def test_authenticated_user_redirected_from_login(
    client, tenant_with_domain, user_owner, membership
):
    """
    Test E: Usuario autenticado es redirigido desde /login/ al dashboard.

    Objetivo: Verificar que si un usuario ya autenticado intenta acceder
    a /login/, es redirigido automáticamente al dashboard.
    """
    # Autenticar al usuario
    client.force_login(user_owner)

    # Intentar acceder a /login/
    response = client.get("/login/", HTTP_HOST="cliente-test.localhost")

    # Debe redirigir al dashboard
    assert response.status_code in (
        302,
        303,
    ), f"Se esperaba 302 o 303, pero se recibió {response.status_code}"

    location = response.headers.get("Location", "")
    assert (
        location.endswith("/dashboard/") or "/dashboard/" in location
    ), f"Se esperaba redirección a /dashboard/, pero se recibió: {location}"
