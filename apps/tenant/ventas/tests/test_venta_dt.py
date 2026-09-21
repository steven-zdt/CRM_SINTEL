"""
Tests del endpoint DataTables server-side de Ventas (piloto DataTables 3.x +
ColumnControl, ver docs/ux/TABLES_FORMS_RELEASE_GATE.md y
apps/shared/datatable.py).

POST /api/v1/ventas/dt/ -- contrato DataTables {draw, recordsTotal,
recordsFiltered, data}, aislamiento de tenant (DSV), whitelist de
orden/filtro por columna.
"""
import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from rest_framework import status

from apps.public.tenants.models import TenantMembership
from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.ventas.models import Venta

User = get_user_model()

DT_URL = "/api/v1/ventas/dt/"


def _crear_cliente(empresa, numero_documento, razon_social):
    return Cliente.objects.create(
        empresa=empresa,
        tipo_persona="JURIDICA",
        tipo_documento="NIT",
        numero_documento=numero_documento,
        razon_social=razon_social,
        regimen_tributario="ORDINARIO",
    )


def _login_tenant(client, tenant, username):
    with schema_context(tenant.schema_name):
        emp = Empresa.objects.first()
        user = User.objects.create_user(username=username, email=f"{username}@t.com", password="password")
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
def test_venta_dt_requiere_autenticacion(client, tenant1):
    resp = client.post(
        DT_URL,
        data=_dt_payload(),
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_venta_dt_contrato_basico(client, tenant1):
    emp = _login_tenant(client, tenant1, "user_dt_contrato")
    with schema_context(tenant1.schema_name):
        cliente = _crear_cliente(emp, "9001", "Cliente Contrato SAS")
        Venta.objects.create(
            empresa=emp, cliente=cliente, fecha_emision="2026-06-01",
            numero_factura="DT-CONTRATO-1", subtotal="100.00", total_neto="100.00",
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
    assert any(row["numero_factura"] == "DT-CONTRATO-1" or row.get("factura_numero") == "DT-CONTRATO-1" for row in body["data"])


@pytest.mark.django_db
def test_venta_dt_aislamiento_tenant(client, tenant1, tenant2):
    emp1 = _login_tenant(client, tenant1, "user_dt_t1")
    with schema_context(tenant1.schema_name):
        cliente1 = _crear_cliente(emp1, "9101", "Cliente DT Tenant Uno")
        Venta.objects.create(
            empresa=emp1, cliente=cliente1, fecha_emision="2026-06-01",
            numero_factura="DT-T1", subtotal="100.00", total_neto="100.00",
        )

    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        user2 = User.objects.create_user(username="user_dt_t2", email="u2@t.com", password="password")
        TenantProfile.objects.create(user=user2, empresa=emp2, rol="ADMIN")
        with schema_context("public"):
            TenantMembership.objects.create(client=tenant2, user=user2, rol="ADMIN")
        cliente2 = _crear_cliente(emp2, "9102", "Cliente DT Tenant Dos")
        Venta.objects.create(
            empresa=emp2, cliente=cliente2, fecha_emision="2026-06-01",
            numero_factura="DT-T2", subtotal="200.00", total_neto="200.00",
        )

    resp = client.post(
        DT_URL,
        data=_dt_payload(),
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK
    numeros = [row["numero_factura"] for row in resp.json()["data"]]
    assert "DT-T1" in numeros
    assert "DT-T2" not in numeros


@pytest.mark.django_db
def test_venta_dt_filtro_columna_estado_exact(client, tenant1):
    emp = _login_tenant(client, tenant1, "user_dt_estado")
    with schema_context(tenant1.schema_name):
        cliente = _crear_cliente(emp, "9201", "Cliente Estado SAS")
        Venta.objects.create(
            empresa=emp, cliente=cliente, fecha_emision="2026-06-01",
            numero_factura="DT-BORRADOR", subtotal="10.00", total_neto="10.00",
            estado=Venta.Estado.BORRADOR,
        )
        Venta.objects.create(
            empresa=emp, cliente=cliente, fecha_emision="2026-06-01",
            numero_factura="DT-ANULADA", subtotal="10.00", total_neto="10.00",
            estado=Venta.Estado.ANULADA,
        )

    payload = _dt_payload(columns=[
        {}, {}, {"search": {"value": "ANULADA"}}, {}, {},
    ])
    resp = client.post(
        DT_URL, data=payload, content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    numeros = [row["numero_factura"] for row in body["data"]]
    assert "DT-ANULADA" in numeros
    assert "DT-BORRADOR" not in numeros
    assert body["recordsFiltered"] == 1


@pytest.mark.django_db
def test_venta_dt_filtro_columna_numero_range(client, tenant1):
    emp = _login_tenant(client, tenant1, "user_dt_range")
    with schema_context(tenant1.schema_name):
        cliente = _crear_cliente(emp, "9301", "Cliente Range SAS")
        Venta.objects.create(
            empresa=emp, cliente=cliente, fecha_emision="2026-06-01",
            numero_factura="DT-BARATA", subtotal="50.00", total_neto="50.00",
        )
        Venta.objects.create(
            empresa=emp, cliente=cliente, fecha_emision="2026-06-01",
            numero_factura="DT-CARA", subtotal="5000.00", total_neto="5000.00",
        )

    payload = _dt_payload(columns=[
        {}, {}, {}, {}, {"search": {"value": "1000~"}},
    ])
    resp = client.post(
        DT_URL, data=payload, content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK
    numeros = [row["numero_factura"] for row in resp.json()["data"]]
    assert "DT-CARA" in numeros
    assert "DT-BARATA" not in numeros


@pytest.mark.django_db
def test_venta_dt_whitelist_columna_y_orden_no_declarados(client, tenant1):
    emp = _login_tenant(client, tenant1, "user_dt_whitelist")
    with schema_context(tenant1.schema_name):
        cliente = _crear_cliente(emp, "9401", "Cliente Whitelist SAS")
        Venta.objects.create(
            empresa=emp, cliente=cliente, fecha_emision="2026-06-01",
            numero_factura="DT-WL", subtotal="10.00", total_neto="10.00",
        )

    payload = _dt_payload(
        order=[{"column": 99, "dir": "asc"}],
        columns=[{"search": {"value": "x"}}] * 3 + [{}, {"search": {"value": "y"}}] + [{"search": {"value": "z"}}] * 10,
    )
    resp = client.post(
        DT_URL, data=payload, content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    # No debe romper (500) ni filtrar por columnas no declaradas (indice 0 es
    # "cliente__razon_social" con ICONTAINS real -- "x" no matchea nada, es el
    # comportamiento esperado de un filtro DECLARADO; el punto de este test es
    # que columnas fuera de rango (>=5) y el orden por columna 99 no rompan).
    assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_venta_dt_busqueda_global(client, tenant1):
    emp = _login_tenant(client, tenant1, "user_dt_search")
    with schema_context(tenant1.schema_name):
        cliente = _crear_cliente(emp, "9501", "Cliente Buscable SAS")
        Venta.objects.create(
            empresa=emp, cliente=cliente, fecha_emision="2026-06-01",
            numero_factura="DT-SEARCH-1", subtotal="10.00", total_neto="10.00",
        )
        otro_cliente = _crear_cliente(emp, "9502", "Otro Cliente SAS")
        Venta.objects.create(
            empresa=emp, cliente=otro_cliente, fecha_emision="2026-06-01",
            numero_factura="DT-SEARCH-2", subtotal="10.00", total_neto="10.00",
        )

    payload = _dt_payload(search={"value": "Buscable"})
    resp = client.post(
        DT_URL, data=payload, content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK
    numeros = [row["numero_factura"] for row in resp.json()["data"]]
    assert "DT-SEARCH-1" in numeros
    assert "DT-SEARCH-2" not in numeros
