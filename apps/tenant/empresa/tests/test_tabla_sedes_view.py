"""
Test de la tabla server-rendered de Sedes (Fase 5-BIS, django-tables2 + HTMX).

Verifica:
1. La vista responde 200 tras login por sesion.
2. Las sedes de la empresa se renderizan correctamente.
3. La busqueda por nombre/direccion filtra la tabla.
"""
import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context

from apps.public.tenants.models import TenantMembership
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile

User = get_user_model()


@pytest.fixture
def _admin_con_sedes(tenant):
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.only('id').first()
        Sede.objects.create(empresa=empresa, nombre='Sede Norte', direccion='Calle 100', encargado_nombre='Ana Perez')
        Sede.objects.create(empresa=empresa, nombre='Sede Sur', direccion='Calle 1', encargado_nombre='')

        admin_user = User.objects.create(username="admin_sede", email="admin_sede@example.com")
        TenantProfile.objects.create(user=admin_user, empresa=empresa, rol="ADMIN")

    TenantMembership.objects.create(client=tenant, user=admin_user, is_active=True, rol="ADMIN")
    return admin_user


@pytest.mark.django_db
def test_tabla_sedes_render(client, tenant, _admin_con_sedes):
    with schema_context(tenant.schema_name):
        client.force_login(_admin_con_sedes)

    r = client.get("/ui/empresa/sedes/tabla/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200, f"Status inesperado: {r.status_code}: {r.content[:500]}"
    html = r.content.decode("utf-8")
    assert "Sede Norte" in html
    assert "Sede Sur" in html
    assert "Ana Perez" in html
    assert "Sin asignar" in html  # Sede Sur sin encargado_nombre


@pytest.mark.django_db
def test_tabla_sedes_busqueda(client, tenant, _admin_con_sedes):
    with schema_context(tenant.schema_name):
        client.force_login(_admin_con_sedes)

    r = client.get("/ui/empresa/sedes/tabla/?q=Norte", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200
    html = r.content.decode("utf-8")
    assert "Sede Norte" in html
    assert "Sede Sur" not in html
