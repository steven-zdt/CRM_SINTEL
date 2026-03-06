"""
Tests para verificar que el tenant público y rutas públicas no son bloqueadas.

⚠️ IMPORTANTE: Estos tests previenen que el middleware bloquee incorrectamente
el tenant público (schema_name == "public") y rutas públicas como /login/, /admin/login/, etc.
"""
import pytest
from django.db import connection
from django_tenants.utils import get_public_schema_name
from apps.public.tenants.models import Client, Domain

pytestmark = [
    pytest.mark.django_db,
]


@pytest.fixture
def public_tenant(db):
    """Obtener o crear el tenant público."""
    connection.set_schema_to_public()
    tenant, _ = Client.objects.get_or_create(
        schema_name=get_public_schema_name(),
        defaults={
            "nombre": "Tenant Público",
            "is_active": True,
            "on_trial": False
        }
    )
    return tenant


@pytest.fixture
def private_tenant(db):
    """Crea un tenant privado para tests."""
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


def test_public_tenant_root_is_not_forbidden(client, public_tenant):
    """
    Test: Tenant público (host público / schema=public) no es bloqueado.
    
    Objetivo: Verificar que el tenant público puede acceder a rutas raíz
    sin recibir 403 Forbidden.
    """
    # Acceder a la raíz del tenant público
    r = client.get("/", HTTP_HOST="localhost")  # público
    # Puede ser 200, 302 (redirección) o 404 (ruta no existe), pero NO debe ser 403
    assert r.status_code != 403, \
        "El tenant público NO debe recibir 403 Forbidden en la raíz."
    assert r.status_code in (200, 302, 404), \
        f"Se esperaba 200, 302 o 404, pero se recibió {r.status_code}. " \
        f"El tenant público no debe ser bloqueado."


def test_public_tenant_admin_is_not_forbidden(client, public_tenant):
    """
    Test: Admin del tenant público no es bloqueado.
    
    Objetivo: Verificar que el admin del tenant público puede accederse
    sin recibir 403 Forbidden.
    """
    # Acceder al admin del tenant público
    r = client.get("/admin/", HTTP_HOST="localhost")  # público
    # Puede ser 200, 302 (redirección) o 404 (ruta no existe), pero NO debe ser 403
    assert r.status_code != 403, \
        "El admin del tenant público NO debe recibir 403 Forbidden."
    assert r.status_code in (200, 302, 404), \
        f"Se esperaba 200, 302 o 404, pero se recibió {r.status_code}. " \
        f"El admin del tenant público no debe ser bloqueado."


def test_login_pages_do_not_loop(client, private_tenant):
    """
    Test: Páginas de login no crean loops de redirección.
    
    Objetivo: Verificar que las páginas de login responden correctamente
    sin crear bucles infinitos de redirección.
    """
    # Acceder a /login/ del tenant privado
    r1 = client.get("/login/", HTTP_HOST="cliente.localhost")
    # Puede ser 200, 302 o 404, pero NO debe ser 403
    assert r1.status_code != 403, \
        "La página de login NO debe recibir 403 Forbidden."
    assert r1.status_code in (200, 302, 404), \
        f"Se esperaba 200, 302 o 404, pero se recibió {r1.status_code}."
    
    # Acceder a /admin/login/ del tenant público
    r2 = client.get("/admin/login/", HTTP_HOST="localhost")
    # Puede ser 200, 302 o 404, pero NO debe ser 403
    assert r2.status_code != 403, \
        "La página de admin/login NO debe recibir 403 Forbidden."
    assert r2.status_code in (200, 302, 404), \
        f"Se esperaba 200, 302 o 404, pero se recibió {r2.status_code}."


def test_well_known_paths_are_not_blocked(client, private_tenant):
    """
    Test: Rutas /.well-known/* no son bloqueadas.
    
    Objetivo: Verificar que las rutas well-known (como /.well-known/appspecific/com.chrome.devtools.json)
    no son bloqueadas por el middleware.
    """
    # Acceder a una ruta well-known
    r = client.get("/.well-known/appspecific/com.chrome.devtools.json", HTTP_HOST="cliente.localhost")
    # Puede ser 200 (existe) o 404 (no existe), pero NO debe ser 403
    assert r.status_code != 403, \
        f"Las rutas /.well-known/* no deben ser bloqueadas. Status: {r.status_code}"
    assert r.status_code in (200, 404), \
        f"Se esperaba 200 o 404, pero se recibió {r.status_code}."


def test_static_files_are_not_blocked(client, private_tenant):
    """
    Test: Archivos estáticos no son bloqueados.
    
    Objetivo: Verificar que los archivos estáticos (/static/*) no son bloqueados
    por el middleware.
    """
    # Intentar acceder a un archivo estático (puede no existir)
    r = client.get("/static/css/test.css", HTTP_HOST="cliente.localhost")
    # Puede ser 404 (no existe) o 200 (existe), pero NO debe ser 403
    assert r.status_code != 403, \
        f"Los archivos estáticos no deben ser bloqueados. Status: {r.status_code}"


def test_media_files_are_not_blocked(client, private_tenant):
    """
    Test: Archivos media no son bloqueados.
    
    Objetivo: Verificar que los archivos media (/media/*) no son bloqueados
    por el middleware.
    """
    # Intentar acceder a un archivo media (puede no existir)
    r = client.get("/media/test.jpg", HTTP_HOST="cliente.localhost")
    # Puede ser 404 (no existe) o 200 (existe), pero NO debe ser 403
    assert r.status_code != 403, \
        f"Los archivos media no deben ser bloqueados. Status: {r.status_code}"


def test_public_landing_page_is_not_blocked(client, private_tenant):
    """
    Test: Página de landing pública (/) no es bloqueada.
    
    Objetivo: Verificar que la página de landing (/) no requiere membresía
    y no es bloqueada por el middleware.
    """
    # Acceder a la landing page (pública)
    r = client.get("/", HTTP_HOST="cliente.localhost")
    assert r.status_code in (200, 302), \
        f"Se esperaba 200 o 302, pero se recibió {r.status_code}."
    # Específicamente, NO debe ser 403
    assert r.status_code != 403, \
        "La landing page pública NO debe recibir 403 Forbidden."
