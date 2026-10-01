"""
Tests del endpoint DataTables MANUAL de Documentos Pendientes de
Contabilizar (piloto DataTables 3.x extendido a Contabilidad, ver
docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md y
DocumentosPendientesViewSet.dt()).

POST /api/v1/contabilidad/pendientes/dt/ -- contrato DataTables {draw,
recordsTotal, recordsFiltered, data}, aislamiento de tenant (DSV), filtro
por columna 0 (tipo_doc) y busqueda global (numero/tercero_nombre). No pasa
por apps/shared/datatable.py::DataTableServer -- la fuente mezcla 4 modelos
de 4 apps en una lista Python (ver docstring de dt()).
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from rest_framework import status

from apps.public.tenants.models import TenantMembership
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.perfil.models import TenantProfile

User = get_user_model()

DT_URL = "/api/v1/contabilidad/pendientes/dt/"


def _crear_factura_pendiente(empresa, numero, receptor="Cliente Pendiente SAS"):
    # naturaleza=VENTA: _construir_pendientes() usa receptor_razon_social
    # como tercero_nombre en ese caso (es_venta=True) -- ver
    # DocumentosPendientesViewSet._construir_pendientes().
    return Factura.objects.create(
        empresa=empresa,
        numero=numero,
        prefijo="FAC",
        consecutivo=1,
        tipo="FE",
        estado="BORRADOR",
        fecha_emision="2026-06-01",
        emisor_nit="900123456",
        emisor_razon_social="Empresa Emisora SAS",
        receptor_nit="800654321",
        receptor_razon_social=receptor,
        subtotal=Decimal("100000.00"),
        impuestos=Decimal("19000.00"),
        total=Decimal("119000.00"),
        naturaleza="VENTA",
    )


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
def test_pendientes_dt_requiere_autenticacion(client, tenant1):
    resp = client.post(
        DT_URL,
        data=_dt_payload(),
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_pendientes_dt_contrato_basico(client, tenant1):
    emp = _login_tenant(client, tenant1, "user_pend_contrato")
    with schema_context(tenant1.schema_name):
        _crear_factura_pendiente(emp, "FAC-PEND-1")

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
    numeros = [row["numero"] for row in body["data"]]
    assert "FAC-PEND-1" in numeros
    fila = next(r for r in body["data"] if r["numero"] == "FAC-PEND-1")
    assert fila["tipo_doc"] == "FACTURA"
    assert fila["app_label"] == "facturas"


@pytest.mark.django_db
def test_pendientes_dt_aislamiento_tenant(client, tenant1, tenant2):
    emp1 = _login_tenant(client, tenant1, "user_pend_t1")
    with schema_context(tenant1.schema_name):
        _crear_factura_pendiente(emp1, "FAC-PEND-T1")

    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        user2 = User.objects.create_user(
            username="user_pend_t2", email="u2@t.com", password="password"
        )
        TenantProfile.objects.create(user=user2, empresa=emp2, rol="ADMIN")
        with schema_context("public"):
            TenantMembership.objects.create(client=tenant2, user=user2, rol="ADMIN")
        _crear_factura_pendiente(emp2, "FAC-PEND-T2")

    resp = client.post(
        DT_URL,
        data=_dt_payload(),
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK
    numeros = [row["numero"] for row in resp.json()["data"]]
    assert "FAC-PEND-T1" in numeros
    assert "FAC-PEND-T2" not in numeros


@pytest.mark.django_db
def test_pendientes_dt_busqueda_global(client, tenant1):
    emp = _login_tenant(client, tenant1, "user_pend_search")
    with schema_context(tenant1.schema_name):
        _crear_factura_pendiente(emp, "FAC-SEARCH-1", receptor="Buscable SAS")
        _crear_factura_pendiente(emp, "FAC-SEARCH-2", receptor="Otro Cliente SAS")

    payload = _dt_payload(search={"value": "Buscable"})
    resp = client.post(
        DT_URL,
        data=payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK
    numeros = [row["numero"] for row in resp.json()["data"]]
    assert "FAC-SEARCH-1" in numeros
    assert "FAC-SEARCH-2" not in numeros


@pytest.mark.django_db
def test_pendientes_dt_filtro_tipo_doc(client, tenant1):
    emp = _login_tenant(client, tenant1, "user_pend_tipo")
    with schema_context(tenant1.schema_name):
        _crear_factura_pendiente(emp, "FAC-TIPO-1")

    payload = _dt_payload(columns=[{"search": {"value": "GASTO"}}])
    resp = client.post(
        DT_URL,
        data=payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK
    numeros = [row["numero"] for row in resp.json()["data"]]
    assert "FAC-TIPO-1" not in numeros
