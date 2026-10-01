"""
Tests del endpoint DataTables server-side de Cuentas Bancarias (mismo patron
ya validado en Ventas -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md
-- extendido aqui a un segundo modulo, confirmado por el usuario).

POST /api/v1/bancos/cuentas/dt/ -- contrato DataTables {draw, recordsTotal,
recordsFiltered, data}, aislamiento de tenant (DSV), whitelist de
orden/filtro por columna.
"""

import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from rest_framework import status

from apps.public.tenants.models import TenantMembership
from apps.tenant.bancos.models import CuentaBancaria
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile

User = get_user_model()

DT_URL = "/api/v1/bancos/cuentas/dt/"


def _login_tenant(client, tenant, username):
    with schema_context(tenant.schema_name):
        emp = Empresa.objects.first()
        user = User.objects.create_user(
            username=username, email=f"{username}@t.com", password="password"
        )
        TenantProfile.objects.create(user=user, empresa=emp, rol="ADMIN")
        with schema_context("public"):
            TenantMembership.objects.create(client=tenant, user=user, rol="ADMIN")
    with schema_context(tenant.schema_name):
        client.force_login(user)
    return emp


def _dt_payload(**overrides):
    payload = {
        "draw": 1,
        "start": 0,
        "length": 10,
        "search": {"value": ""},
        "order": [],
        "columns": [],
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_cuenta_dt_requiere_autenticacion(client, tenant1):
    resp = client.post(
        DT_URL,
        data=_dt_payload(),
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_cuenta_dt_contrato_basico(client, tenant1):
    emp = _login_tenant(client, tenant1, "user_dt_contrato")
    with schema_context(tenant1.schema_name):
        CuentaBancaria.objects.create(
            empresa=emp,
            nombre="Cuenta DT Contrato",
            banco="BANCOLOMBIA",
            tipo="CORRIENTE",
            numero="001",
        )

    resp = client.post(
        DT_URL,
        data=_dt_payload(),
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert set(body.keys()) == {"draw", "recordsTotal", "recordsFiltered", "data"}
    assert body["draw"] == 1
    assert body["recordsTotal"] >= 1
    assert any(row["nombre"] == "Cuenta DT Contrato" for row in body["data"])


@pytest.mark.django_db
def test_cuenta_dt_aislamiento_tenant(client, tenant1, tenant2):
    emp1 = _login_tenant(client, tenant1, "user_dt_t1")
    with schema_context(tenant1.schema_name):
        CuentaBancaria.objects.create(
            empresa=emp1,
            nombre="Cuenta DT Tenant Uno",
            banco="BANCOLOMBIA",
            tipo="CORRIENTE",
            numero="T1",
        )

    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        user2 = User.objects.create_user(
            username="user_dt_t2", email="u2@t.com", password="password"
        )
        TenantProfile.objects.create(user=user2, empresa=emp2, rol="ADMIN")
        with schema_context("public"):
            TenantMembership.objects.create(client=tenant2, user=user2, rol="ADMIN")
        CuentaBancaria.objects.create(
            empresa=emp2,
            nombre="Cuenta DT Tenant Dos",
            banco="DAVIVIENDA",
            tipo="AHORROS",
            numero="T2",
        )

    resp = client.post(
        DT_URL,
        data=_dt_payload(),
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK
    nombres = [row["nombre"] for row in resp.json()["data"]]
    assert "Cuenta DT Tenant Uno" in nombres
    assert "Cuenta DT Tenant Dos" not in nombres


@pytest.mark.django_db
def test_cuenta_dt_filtro_columna_banco_exact(client, tenant1):
    emp = _login_tenant(client, tenant1, "user_dt_banco")
    with schema_context(tenant1.schema_name):
        CuentaBancaria.objects.create(
            empresa=emp,
            nombre="Cuenta Bancolombia",
            banco="BANCOLOMBIA",
            tipo="CORRIENTE",
            numero="B1",
        )
        CuentaBancaria.objects.create(
            empresa=emp,
            nombre="Cuenta Davivienda",
            banco="DAVIVIENDA",
            tipo="AHORROS",
            numero="B2",
        )

    payload = _dt_payload(
        columns=[
            {},
            {"search": {"value": "DAVIVIENDA"}},
            {},
            {},
            {},
        ]
    )
    resp = client.post(
        DT_URL,
        data=payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    nombres = [row["nombre"] for row in body["data"]]
    assert "Cuenta Davivienda" in nombres
    assert "Cuenta Bancolombia" not in nombres
    assert body["recordsFiltered"] == 1


@pytest.mark.django_db
def test_cuenta_dt_filtro_columna_estado_exact(client, tenant1):
    emp = _login_tenant(client, tenant1, "user_dt_estado")
    with schema_context(tenant1.schema_name):
        CuentaBancaria.objects.create(
            empresa=emp,
            nombre="Cuenta Activa",
            banco="BANCOLOMBIA",
            tipo="CORRIENTE",
            numero="A1",
            activo=True,
        )
        CuentaBancaria.objects.create(
            empresa=emp,
            nombre="Cuenta Inactiva",
            banco="BANCOLOMBIA",
            tipo="CORRIENTE",
            numero="A2",
            activo=False,
        )

    payload = _dt_payload(
        columns=[
            {},
            {},
            {},
            {},
            {"search": {"value": "false"}},
        ]
    )
    resp = client.post(
        DT_URL,
        data=payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    nombres = [row["nombre"] for row in body["data"]]
    assert "Cuenta Inactiva" in nombres
    assert "Cuenta Activa" not in nombres
    assert body["recordsFiltered"] == 1


@pytest.mark.django_db
def test_cuenta_dt_whitelist_columna_y_orden_no_declarados(client, tenant1):
    emp = _login_tenant(client, tenant1, "user_dt_whitelist")
    with schema_context(tenant1.schema_name):
        CuentaBancaria.objects.create(
            empresa=emp,
            nombre="Cuenta Whitelist",
            banco="BANCOLOMBIA",
            tipo="CORRIENTE",
            numero="W1",
        )

    payload = _dt_payload(
        order=[{"column": 99, "dir": "asc"}],
        columns=[{"search": {"value": "x"}}] * 2
        + [{"search": {"value": "y"}}] * 3
        + [{"search": {"value": "z"}}] * 10,
    )
    resp = client.post(
        DT_URL,
        data=payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    # No debe romper (500) por columnas fuera de rango (>=5) ni por el orden
    # por columna 99 (no declarada en fields_map).
    assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_cuenta_dt_busqueda_global(client, tenant1):
    emp = _login_tenant(client, tenant1, "user_dt_search")
    with schema_context(tenant1.schema_name):
        CuentaBancaria.objects.create(
            empresa=emp,
            nombre="Cuenta Buscable Unica",
            banco="BANCOLOMBIA",
            tipo="CORRIENTE",
            numero="S1",
        )
        CuentaBancaria.objects.create(
            empresa=emp,
            nombre="Otra Cuenta",
            banco="DAVIVIENDA",
            tipo="AHORROS",
            numero="S2",
        )

    payload = _dt_payload(search={"value": "Buscable"})
    resp = client.post(
        DT_URL,
        data=payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK
    nombres = [row["nombre"] for row in resp.json()["data"]]
    assert "Cuenta Buscable Unica" in nombres
    assert "Otra Cuenta" not in nombres
