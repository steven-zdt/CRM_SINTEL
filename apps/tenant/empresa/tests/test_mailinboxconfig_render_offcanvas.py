"""
Test real de MailInboxConfigViewSet.render_offcanvas() (endpoint HTMX de
creacion/edicion de buzon de correo).

Bug real hallado y corregido en produccion (reportado por el usuario via
consola del navegador -- GET .../render-offcanvas/ 500): el metodo usaba
`logger.*` en 7 lugares, pero el modulo nunca define `logger` -- solo
`log`/`log_mailinbox` (logging.getLogger). NameError garantizado en
CUALQUIER llamada real: la pantalla de creacion/edicion de buzon nunca
funciono, bloqueando el primer paso de todo el flujo de Mail Hub (sin
poder crear un MailInboxConfig, no hay nada que sincronizar).
"""
import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context

from apps.public.tenants.models import TenantMembership
from apps.tenant.empresa.models import Empresa, MailInboxConfig
from apps.tenant.perfil.models import TenantProfile

User = get_user_model()


@pytest.fixture
def _admin_empresa(tenant):
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.only('id').first()
        admin_user = User.objects.create(username="admin_offcanvas", email="admin_offcanvas@example.com")
        TenantProfile.objects.create(user=admin_user, empresa=empresa, rol="ADMIN")

    TenantMembership.objects.create(client=tenant, user=admin_user, is_active=True, rol="ADMIN")
    return admin_user, empresa


@pytest.mark.django_db
def test_render_offcanvas_modo_creacion_no_crashea(client, tenant, _admin_empresa):
    """Sin ?id= -> modo creacion. Debe renderizar 200, nunca 500 por NameError."""
    admin_user, _ = _admin_empresa
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    r = client.get(
        "/api/v1/empresas/mail-inbox-config/render-offcanvas/",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )

    assert r.status_code == 200, f"Status inesperado: {r.status_code}: {r.content[:500]}"
    html = r.content.decode("utf-8")
    assert "Nueva Configuracion de Correo" in html or "offcanvas-mailinbox" in html


@pytest.mark.django_db
def test_render_offcanvas_modo_edicion_con_id_real_no_crashea(client, tenant, _admin_empresa):
    """Con ?id=<real> -> modo edicion. Debe renderizar 200 con los datos cargados."""
    admin_user, empresa = _admin_empresa
    with schema_context(tenant.schema_name):
        cfg = MailInboxConfig.objects.create(
            empresa=empresa, nombre="Buzon Test Offcanvas",
            email_address="test@example.com", provider="custom",
            imap_host="mail.example.com", imap_port=993, is_active=True,
        )
        client.force_login(admin_user)

    r = client.get(
        f"/api/v1/empresas/mail-inbox-config/render-offcanvas/?id={cfg.id}",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )

    assert r.status_code == 200, f"Status inesperado: {r.status_code}: {r.content[:500]}"
    html = r.content.decode("utf-8")
    assert "Buzon Test Offcanvas" in html


@pytest.mark.django_db
def test_render_offcanvas_id_inexistente_no_crashea(client, tenant, _admin_empresa):
    """Con ?id=<inexistente> -> rama 'no encontrada'. Debe renderizar 200, no 500."""
    admin_user, _ = _admin_empresa
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    r = client.get(
        "/api/v1/empresas/mail-inbox-config/render-offcanvas/?id=999999",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )

    assert r.status_code == 200, f"Status inesperado: {r.status_code}: {r.content[:500]}"
