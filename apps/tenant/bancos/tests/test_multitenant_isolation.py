"""
Aislamiento multi-tenant de las vistas HTML nuevas (django-tables2 + HTMX,
PLAN_UNICO_CORRECCIONES.md Fase 5-BIS) que reemplazan las grillas Tabulator
de bancos (cuentas bancarias, extractos bancarios).

Estas vistas no pasan por DRF (no son ViewSets) -- usan SintelDSVMixin
directamente, asi que necesitan su propia verificacion, no basta con la
cobertura ya existente sobre /api/v1/bancos/.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django_tenants.utils import schema_context
from rest_framework import status

from apps.public.tenants.models import TenantMembership
from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile

User = get_user_model()


def _setup_tenant(tenant, username, email, sufijo):
    with schema_context(tenant.schema_name):
        emp = Empresa.objects.first()
        user = User.objects.create_user(username=username, email=email, password="password")
        TenantProfile.objects.create(user=user, empresa=emp, rol="ADMIN")
        with schema_context('public'):
            TenantMembership.objects.create(client=tenant, user=user, rol="ADMIN")

        cuenta = CuentaBancaria.objects.create(
            empresa=emp, nombre=f"Cuenta Corriente {sufijo}", banco="BANCOLOMBIA",
            tipo="CORRIENTE", numero=f"00{sufijo}",
        )
        ExtractoBancario.objects.create(
            empresa=emp, cuenta=cuenta, mes=1, anio=2026,
            saldo_inicial=1000, saldo_final=2000,
        )
        return user


@pytest.mark.django_db
def test_multitenant_isolation_bancos_tablas_html(client, tenant1, tenant2):
    _setup_tenant(tenant1, "buser1", "bu1@t.com", "Uno")
    _setup_tenant(tenant2, "buser2", "bu2@t.com", "Dos")

    with schema_context(tenant1.schema_name):
        user1 = User.objects.get(username="buser1")

    client.force_login(user1)
    host1 = f"{tenant1.schema_name}.sintel.net.co"

    # Cuentas
    resp = client.get("/ui/bancos/cuentas/tabla/", HTTP_HOST=host1)
    assert resp.status_code == status.HTTP_200_OK
    body = resp.content.decode()
    assert "Cuenta Corriente Uno" in body
    assert "Cuenta Corriente Dos" not in body

    # Extractos
    resp = client.get("/ui/bancos/extractos/tabla/", HTTP_HOST=host1)
    assert resp.status_code == status.HTTP_200_OK

    # Sin sesion: debe redirigir a login (LoginRequiredMixin), no filtrar en silencio
    anon_client = Client()
    resp = anon_client.get("/ui/bancos/cuentas/tabla/", HTTP_HOST=host1)
    assert resp.status_code in (status.HTTP_302_FOUND, status.HTTP_403_FORBIDDEN)
