"""
Aislamiento multi-tenant de los listados de Bancos: Cuentas y Extractos
migraron a DataTables (ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md
-- Cuentas cubierto tambien, con mas detalle, en test_cuenta_dt.py; aqui se
mantiene la verificacion de extremo a extremo contra POST
/api/v1/bancos/{cuentas,extractos}/dt/ en el mismo test, para no perder la
cobertura combinada historica). Los KPIs de conciliacion de Extractos
(BAN-09, ExtractoBancarioKpisView) siguen siendo una vista HTML
(django-tables2 + HTMX ya no aplica, pero LoginRequiredMixin si) -- no pasa
por DRF, usa SintelDSVMixin directamente, necesita su propia verificacion.
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
        with schema_context("public"):
            TenantMembership.objects.create(client=tenant, user=user, rol="ADMIN")

        cuenta = CuentaBancaria.objects.create(
            empresa=emp,
            nombre=f"Cuenta Corriente {sufijo}",
            banco="BANCOLOMBIA",
            tipo="CORRIENTE",
            numero=f"00{sufijo}",
        )
        ExtractoBancario.objects.create(
            empresa=emp,
            cuenta=cuenta,
            mes=1,
            anio=2026,
            saldo_inicial=1000,
            saldo_final=2000,
        )
        return user


@pytest.mark.django_db
def test_multitenant_isolation_bancos_tablas_html(client, tenant1, tenant2):
    _setup_tenant(tenant1, "buser1", "bu1@t.com", "Uno")
    _setup_tenant(tenant2, "buser2", "bu2@t.com", "Dos")

    with schema_context(tenant1.schema_name):
        user1 = User.objects.get(username="buser1")

    # force_login debe escribir la sesion en el esquema del tenant: sessions
    # esta en TENANT_APPS (aislado por esquema) y la request real solo la lee
    # despues de que TenantMainMiddleware cambia de esquema (ver settings.py).
    with schema_context(tenant1.schema_name):
        client.force_login(user1)
    host1 = f"{tenant1.schema_name}.sintel.net.co"

    # Cuentas (DataTables -- POST, no la vista HTML django-tables2 retirada)
    dt_payload = {
        "draw": 1,
        "start": 0,
        "length": 10,
        "search": {"value": ""},
        "order": [],
        "columns": [],
    }
    resp = client.post(
        "/api/v1/bancos/cuentas/dt/",
        data=dt_payload,
        content_type="application/json",
        HTTP_HOST=host1,
    )
    assert resp.status_code == status.HTTP_200_OK
    nombres = [row["nombre"] for row in resp.json()["data"]]
    assert "Cuenta Corriente Uno" in nombres
    assert "Cuenta Corriente Dos" not in nombres

    # Extractos (DataTables -- POST, no la vista HTML django-tables2 retirada)
    resp = client.post(
        "/api/v1/bancos/extractos/dt/",
        data=dt_payload,
        content_type="application/json",
        HTTP_HOST=host1,
    )
    assert resp.status_code == status.HTTP_200_OK
    cuentas_extracto = [row["cuenta_nombre"] for row in resp.json()["data"]]
    assert "Cuenta Corriente Uno" in cuentas_extracto
    assert "Cuenta Corriente Dos" not in cuentas_extracto

    # KPIs de conciliacion de Extractos (BAN-09, vista HTML)
    resp = client.get("/ui/bancos/extractos/tabla/", HTTP_HOST=host1)
    assert resp.status_code == status.HTTP_200_OK

    # Sin sesion: la vista HTML de KPIs (LoginRequiredMixin) debe redirigir a
    # login, no filtrar en silencio; los endpoints DataTables (DRF) deben
    # rechazar con 401/403.
    anon_client = Client()
    resp = anon_client.get("/ui/bancos/extractos/tabla/", HTTP_HOST=host1)
    assert resp.status_code in (status.HTTP_302_FOUND, status.HTTP_403_FORBIDDEN)
    resp = anon_client.post(
        "/api/v1/bancos/cuentas/dt/",
        data=dt_payload,
        content_type="application/json",
        HTTP_HOST=host1,
    )
    assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    resp = anon_client.post(
        "/api/v1/bancos/extractos/dt/",
        data=dt_payload,
        content_type="application/json",
        HTTP_HOST=host1,
    )
    assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
