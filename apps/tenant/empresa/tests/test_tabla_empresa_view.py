"""
Test de la tabla server-rendered de Empresa (singleton, Fase 5-BIS,
django-tables2 + HTMX).

Verifica:
1. La vista responde 200 tras login por sesion.
2. Los datos de la empresa del tenant se renderizan correctamente.
3. La busqueda por NIT/razon social filtra la tabla.
"""
import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context

from apps.public.tenants.models import TenantMembership
from apps.tenant.perfil.models import TenantProfile

User = get_user_model()


@pytest.fixture
def _admin_empresa(tenant):
    with schema_context(tenant.schema_name):
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.only('id').first()

        admin_user = User.objects.create(username="admin_empresa", email="admin_empresa@example.com")
        TenantProfile.objects.create(user=admin_user, empresa=empresa, rol="ADMIN")

    TenantMembership.objects.create(client=tenant, user=admin_user, is_active=True, rol="ADMIN")
    return admin_user


@pytest.mark.django_db
def test_tabla_empresa_render(client, tenant, _admin_empresa):
    with schema_context(tenant.schema_name):
        client.force_login(_admin_empresa)

    r = client.get("/ui/empresa/empresa/tabla/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200, f"Status inesperado: {r.status_code}: {r.content[:500]}"
    html = r.content.decode("utf-8")
    assert "EMPRESA TEST S.A.S." in html
    assert "901234567" in html


@pytest.mark.django_db
def test_tabla_empresa_busqueda(client, tenant, _admin_empresa):
    with schema_context(tenant.schema_name):
        client.force_login(_admin_empresa)

    r = client.get("/ui/empresa/empresa/tabla/?q=EMPRESA TEST", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200
    html = r.content.decode("utf-8")
    assert "EMPRESA TEST S.A.S." in html

    r2 = client.get("/ui/empresa/empresa/tabla/?q=NoExiste123", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")
    assert r2.status_code == 200
    html2 = r2.content.decode("utf-8")
    assert "EMPRESA TEST S.A.S." not in html2
