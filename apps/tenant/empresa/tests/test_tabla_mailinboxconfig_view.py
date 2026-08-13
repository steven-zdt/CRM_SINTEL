"""
Test de la tabla server-rendered de MailInboxConfig (Fase 5-BIS,
django-tables2 + HTMX).

Verifica:
1. La vista responde 200 tras login por sesion.
2. Las configuraciones de buzon de la empresa se renderizan correctamente.
3. La busqueda por nombre/email/host filtra la tabla.

Nota: esta migracion corrigio de paso un bug funcional -- el template
Tabulator anterior (mailinbox_list.html) usaba los ids #grid-mailinbox /
#search-mailinbox, pero mailinboxconfig_list.js buscaba
#grid-mailinboxconfig / #search-mailinboxconfig -- la grilla nunca se
renderizaba (Tabulator fallaba silenciosamente con un console.warn).
"""
import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context

from apps.public.tenants.models import TenantMembership
from apps.tenant.empresa.models import Empresa, MailInboxConfig
from apps.tenant.perfil.models import TenantProfile

User = get_user_model()


@pytest.fixture
def _admin_con_buzones(tenant):
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.only('id').first()
        MailInboxConfig.objects.create(
            empresa=empresa, nombre='Facturas Gmail', email_address='facturas@example.com',
            provider='gmail', imap_host='imap.gmail.com', imap_port=993, is_active=True,
        )
        MailInboxConfig.objects.create(
            empresa=empresa, nombre='Soporte IMAP', email_address='soporte@example.com',
            provider='custom', imap_host='mail.example.com', imap_port=993, is_active=False,
        )

        admin_user = User.objects.create(username="admin_mailinbox", email="admin_mailinbox@example.com")
        TenantProfile.objects.create(user=admin_user, empresa=empresa, rol="ADMIN")

    TenantMembership.objects.create(client=tenant, user=admin_user, is_active=True, rol="ADMIN")
    return admin_user


@pytest.mark.django_db
def test_tabla_mailinboxconfig_render(client, tenant, _admin_con_buzones):
    with schema_context(tenant.schema_name):
        client.force_login(_admin_con_buzones)

    r = client.get("/ui/empresa/mailinboxconfig/tabla/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200, f"Status inesperado: {r.status_code}: {r.content[:500]}"
    html = r.content.decode("utf-8")
    assert "Facturas Gmail" in html
    assert "Soporte IMAP" in html
    assert "imap.gmail.com" in html


@pytest.mark.django_db
def test_tabla_mailinboxconfig_busqueda(client, tenant, _admin_con_buzones):
    with schema_context(tenant.schema_name):
        client.force_login(_admin_con_buzones)

    r = client.get("/ui/empresa/mailinboxconfig/tabla/?q=Gmail", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200
    html = r.content.decode("utf-8")
    assert "Facturas Gmail" in html
    assert "Soporte IMAP" not in html
