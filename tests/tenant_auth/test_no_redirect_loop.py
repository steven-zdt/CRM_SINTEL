"""
Tests para verificar que no hay loops de redirección en el login.

[WARNING] IMPORTANTE: Estos tests previenen bucles infinitos de redirección entre
/login/ y /admin/login/ cuando el middleware valida membresía.
"""
import pytest
from django.db import connection
from apps.public.tenants.models import Client, Domain

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.urls('config.urls_tenant'),
]


@pytest.fixture
def tenant_with_domain(db):
    """Crea un tenant con dominio para tests."""
    connection.set_schema_to_public()
    
    tenant = Client.objects.create(
        nombre="Cliente Test",
        schema_name="cliente_test",
        is_active=True,
        on_trial=True
    )
    
    Domain.objects.create(
        tenant=tenant,
        domain="cliente.localhost",
        is_primary=True
    )
    
    return tenant


def test_login_pages_do_not_loop(client, tenant_with_domain):
    """
    Test: Acceder a /login/ y /admin/login/ no debe provocar loops.
    
    Objetivo: Verificar que las páginas de login responden correctamente
    sin crear bucles infinitos de redirección.
    """
    # Acceder a /login/ del tenant
    r1 = client.get("/login/", HTTP_HOST="cliente.localhost")
    assert r1.status_code in (200, 302), \
        f"Se esperaba 200 o 302, pero se recibió {r1.status_code}. " \
        f"Esto podría indicar un loop de redirección."
    
    # Verificar que no hay múltiples redirecciones
    if r1.status_code == 302:
        location = r1.headers.get("Location", "")
        # No debe redirigir a /login/ de nuevo (loop)
        assert not location.endswith("/login/") or "no_tenant_access" not in location, \
            f"Posible loop detectado: redirige a {location}"
    
    # Acceder a /admin/login/ (puede estar bloqueado o redirigir)
    r2 = client.get("/admin/login/", HTTP_HOST="cliente.localhost")
    assert r2.status_code in (200, 302, 404), \
        f"Se esperaba 200, 302 o 404, pero se recibió {r2.status_code}."
    
    # Verificar que no hay múltiples redirecciones
    if r2.status_code == 302:
        location = r2.headers.get("Location", "")
        # No debe redirigir a /login/?no_tenant_access=1 en bucle
        assert not (location.endswith("/login/") and "no_tenant_access" in location), \
            f"Posible loop detectado: redirige a {location}"


def test_authenticated_user_can_access_login_page(client, tenant_with_domain):
    """
    Test: Usuario autenticado puede acceder a /login/ sin loops.
    
    Objetivo: Verificar que un usuario autenticado puede acceder a /login/
    y es redirigido al dashboard sin crear loops.
    """
    from django.contrib.auth import get_user_model
    from apps.public.tenants.models import TenantMembership
    
    User = get_user_model()
    connection.set_schema_to_public()
    
    # Crear usuario con membresía
    user = User.objects.create_user(
        email="owner@cliente.localhost",
        password="Secr3tPass!",
        is_staff=False,
        is_active=True
    )
    
    TenantMembership.objects.create(
        client=tenant_with_domain,
        user=user,
        rol="ADMIN",
        is_primary_admin=True,
        is_active=True
    )
    
    # Autenticar al usuario
    client.force_login(user)
    
    # Acceder a /login/ (debe redirigir al dashboard)
    r = client.get("/login/", HTTP_HOST="cliente.localhost")
    assert r.status_code in (302, 303), \
        f"Se esperaba 302 o 303 (redirección al dashboard), pero se recibió {r.status_code}."
    
    # Verificar que redirige al dashboard (no a /login/ de nuevo)
    location = r.headers.get("Location", "")
    assert "/dashboard/" in location or location.endswith("/dashboard/"), \
        f"Se esperaba redirección a /dashboard/, pero se recibió: {location}"


def test_static_files_bypass_membership_check(client, tenant_with_domain):
    """
    Test: Archivos estáticos no son interceptados por el middleware.
    
    Objetivo: Verificar que los archivos estáticos/media no son bloqueados
    por el middleware de membresía.
    """
    # Intentar acceder a un archivo estático (puede no existir, pero no debe dar 403)
    r = client.get("/static/css/test.css", HTTP_HOST="cliente.localhost")
    # Puede ser 404 (no existe) o 200 (existe), pero NO debe ser 403
    assert r.status_code != 403, \
        f"Los archivos estáticos no deben ser bloqueados por el middleware. " \
        f"Status: {r.status_code}"


def test_public_landing_page_bypasses_membership_check(client, tenant_with_domain):
    """
    Test: Página de landing pública no requiere membresía.
    
    Objetivo: Verificar que la página de landing (/) no requiere membresía
    y no crea loops de redirección.
    """
    # Acceder a la landing page (pública)
    r = client.get("/", HTTP_HOST="cliente.localhost")
    assert r.status_code in (200, 302), \
        f"Se esperaba 200 o 302, pero se recibió {r.status_code}."
    
    # Si redirige, no debe ser a /login/?no_tenant_access=1 (loop)
    if r.status_code == 302:
        location = r.headers.get("Location", "")
        assert "no_tenant_access" not in location, \
            f"La landing page pública no debe redirigir a login con no_tenant_access: {location}"
