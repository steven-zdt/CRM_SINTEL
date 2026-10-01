"""
Tests del endpoint DataTables de Libro Diario (piloto DataTables 3.x
extendido a Contabilidad, ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md
y LibroDiarioViewSet.dt()).

POST /api/v1/contabilidad/libro-diario/dt/ -- contrato DataTables {draw,
recordsTotal, recordsFiltered, data, resumen}, consulta AsientoContable
directo (no los extractores cross-app de list()/get_libro_diario_periodo(),
que se dejan intactos y siguen cubiertos por test_api_contabilidad.py).

Cubre especificamente el hallazgo real corregido en esta migracion: dt()
resuelve periodo_uuid via PeriodoContable (list() nunca lo leia, solo
`periodo`/`fecha_inicio`+`fecha_fin`).
"""

import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from rest_framework import status

from apps.public.tenants.models import TenantMembership
from apps.tenant.contabilidad.models import AsientoContable, PeriodoContable
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile

User = get_user_model()

DT_URL = "/api/v1/contabilidad/libro-diario/dt/"


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
def test_libro_diario_dt_requiere_autenticacion(client, tenant1):
    resp = client.post(
        f"{DT_URL}?fecha_inicio=2026-01-01&fecha_fin=2026-01-31",
        data=_dt_payload(),
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_libro_diario_dt_por_rango_fechas(client, tenant1):
    emp = _login_tenant(client, tenant1, "user_libro_rango")
    with schema_context(tenant1.schema_name):
        AsientoContable.objects.create(
            empresa=emp,
            numero="LD-1",
            fecha="2026-06-15",
            descripcion="Asiento Libro Diario",
            estado="APROBADO",
            total_debe=500,
            total_haber=500,
        )
        # Fuera del rango consultado -- no debe aparecer.
        AsientoContable.objects.create(
            empresa=emp,
            numero="LD-FUERA",
            fecha="2026-05-01",
            descripcion="Fuera de rango",
            estado="APROBADO",
            total_debe=100,
            total_haber=100,
        )

    resp = client.post(
        f"{DT_URL}?fecha_inicio=2026-06-01&fecha_fin=2026-06-30",
        data=_dt_payload(),
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert set(body.keys()) == {"draw", "recordsTotal", "recordsFiltered", "data", "resumen"}
    numeros = [row["numero"] for row in body["data"]]
    assert "LD-1" in numeros
    assert "LD-FUERA" not in numeros
    assert body["resumen"]["total_asientos"] == 1
    assert body["resumen"]["cuadrados"] == 1


@pytest.mark.django_db
def test_libro_diario_dt_resuelve_periodo_uuid(client, tenant1):
    """
    Hallazgo real: list() (endpoint viejo) ignoraba periodo_uuid en
    silencio -- dt() debe resolverlo correctamente via PeriodoContable.
    """
    emp = _login_tenant(client, tenant1, "user_libro_periodo")
    with schema_context(tenant1.schema_name):
        periodo = PeriodoContable.objects.create(
            empresa=emp,
            periodo="2026-07",
            fecha_inicio="2026-07-01",
            fecha_fin="2026-07-31",
            estado="ABIERTO",
        )
        AsientoContable.objects.create(
            empresa=emp,
            numero="LD-PERIODO",
            fecha="2026-07-10",
            descripcion="Asiento en periodo",
            estado="APROBADO",
            total_debe=200,
            total_haber=200,
        )
        # Fuera del periodo -- no debe aparecer aunque el mes actual real lo incluyera.
        AsientoContable.objects.create(
            empresa=emp,
            numero="LD-OTRO-MES",
            fecha="2026-08-05",
            descripcion="Otro mes",
            estado="APROBADO",
            total_debe=300,
            total_haber=300,
        )

    resp = client.post(
        f"{DT_URL}?periodo_uuid={periodo.uuid}",
        data=_dt_payload(),
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK
    numeros = [row["numero"] for row in resp.json()["data"]]
    assert "LD-PERIODO" in numeros
    assert "LD-OTRO-MES" not in numeros


@pytest.mark.django_db
def test_libro_diario_dt_periodo_uuid_de_otro_tenant_no_resuelve(client, tenant1, tenant2):
    """DSV: un periodo_uuid de OTRO tenant no debe filtrar datos (404, no fallback silencioso)."""
    _login_tenant(client, tenant1, "user_libro_dsv1")
    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        periodo2 = PeriodoContable.objects.create(
            empresa=emp2,
            periodo="2026-09",
            fecha_inicio="2026-09-01",
            fecha_fin="2026-09-30",
            estado="ABIERTO",
        )

    resp = client.post(
        f"{DT_URL}?periodo_uuid={periodo2.uuid}",
        data=_dt_payload(),
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_libro_diario_dt_aislamiento_tenant(client, tenant1, tenant2):
    emp1 = _login_tenant(client, tenant1, "user_libro_t1")
    with schema_context(tenant1.schema_name):
        AsientoContable.objects.create(
            empresa=emp1,
            numero="LD-T1",
            fecha="2026-06-10",
            descripcion="Asiento Tenant Uno",
            estado="APROBADO",
            total_debe=100,
            total_haber=100,
        )

    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        user2 = User.objects.create_user(
            username="user_libro_t2", email="u2@t.com", password="password"
        )
        TenantProfile.objects.create(user=user2, empresa=emp2, rol="ADMIN")
        with schema_context("public"):
            TenantMembership.objects.create(client=tenant2, user=user2, rol="ADMIN")
        AsientoContable.objects.create(
            empresa=emp2,
            numero="LD-T2",
            fecha="2026-06-10",
            descripcion="Asiento Tenant Dos",
            estado="APROBADO",
            total_debe=200,
            total_haber=200,
        )

    resp = client.post(
        f"{DT_URL}?fecha_inicio=2026-06-01&fecha_fin=2026-06-30",
        data=_dt_payload(),
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK
    numeros = [row["numero"] for row in resp.json()["data"]]
    assert "LD-T1" in numeros
    assert "LD-T2" not in numeros
