"""
Tests del endpoint DataTables server-side de Cotizaciones (piloto
DataTables 3.x extendido a Cotizaciones, ver
docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md).

POST /api/v1/cotizaciones/dt/ -- contrato DataTables {draw, recordsTotal,
recordsFiltered, data}, aislamiento de tenant (DSV), filtro por columna
(estado EXACT) y busqueda global (numero_cotizacion/codigo_unico/cliente).

Sigue la convencion local de fixtures de esta app (conftest.py):
`tenant`/`tenant_b` (no `tenant1`/`tenant2`), `factory_empresa()`
(crea empresa+usuario+TenantMembership+TenantProfile), APIClient +
force_authenticate + credentials(HTTP_HOST=...) (no force_login) -- mismo
patron ya usado en test_api.py de esta misma app.
"""

import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from rest_framework.test import APIClient

from apps.tenant.cotizaciones.models import Cotizacion

User = get_user_model()

DT_URL = "/api/v1/cotizaciones/dt/"


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


def _api_client_autenticado(tenant, user):
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")
    return client


@pytest.mark.urls("config.urls_tenant")
@pytest.mark.django_db
def test_cotizacion_dt_requiere_autenticacion(tenant):
    client = APIClient()
    client.credentials(HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")
    resp = client.post(DT_URL, data=_dt_payload(), format="json")
    assert resp.status_code in (401, 403)


@pytest.mark.urls("config.urls_tenant")
@pytest.mark.django_db
def test_cotizacion_dt_contrato_basico(tenant, factory_empresa):
    empresa = factory_empresa()
    with schema_context(tenant.schema_name):
        Cotizacion.objects.create(
            empresa=empresa,
            numero_cotizacion="COT-DT-1",
            fecha_vencimiento="2026-12-31",
            estado="BORRADOR",
            total_con_impuestos="1000.00",
        )
        user = User.objects.get(email="admin@test.local")

    client = _api_client_autenticado(tenant, user)
    resp = client.post(DT_URL, data=_dt_payload(), format="json")
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert set(body.keys()) == {"draw", "recordsTotal", "recordsFiltered", "data"}
    numeros = [row["numero_cotizacion"] for row in body["data"]]
    assert "COT-DT-1" in numeros


@pytest.mark.urls("config.urls_tenant")
@pytest.mark.django_db
def test_cotizacion_dt_aislamiento_tenant(tenant, tenant_b, factory_empresa):
    empresa = factory_empresa()
    with schema_context(tenant.schema_name):
        Cotizacion.objects.create(
            empresa=empresa,
            numero_cotizacion="COT-T1",
            fecha_vencimiento="2026-12-31",
            estado="BORRADOR",
            total_con_impuestos="1000.00",
        )
        user = User.objects.get(email="admin@test.local")

    with schema_context(tenant_b.schema_name):
        from apps.tenant.empresa.models import Empresa

        empresa_b = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa B Cotizaciones",
            nit="900000794",
            direccion="Calle 2",
        )
        Cotizacion.objects.create(
            empresa=empresa_b,
            numero_cotizacion="COT-T2",
            fecha_vencimiento="2026-12-31",
            estado="BORRADOR",
            total_con_impuestos="2000.00",
        )

    client = _api_client_autenticado(tenant, user)
    resp = client.post(DT_URL, data=_dt_payload(), format="json")
    assert resp.status_code == 200, resp.content
    numeros = [row["numero_cotizacion"] for row in resp.json()["data"]]
    assert "COT-T1" in numeros
    assert "COT-T2" not in numeros


@pytest.mark.urls("config.urls_tenant")
@pytest.mark.django_db
def test_cotizacion_dt_filtro_columna_estado_exact(tenant, factory_empresa):
    """
    Regresion cubierta por el fix de apps/shared/datatable.py
    (_coerce_exact_value) -- un <select value="ACEPTADA"> (choice
    CharField, no booleano) debe seguir funcionando tal cual.
    """
    empresa = factory_empresa()
    with schema_context(tenant.schema_name):
        Cotizacion.objects.create(
            empresa=empresa,
            numero_cotizacion="COT-BORRADOR",
            fecha_vencimiento="2026-12-31",
            estado="BORRADOR",
            total_con_impuestos="1000.00",
        )
        Cotizacion.objects.create(
            empresa=empresa,
            numero_cotizacion="COT-ACEPTADA",
            fecha_vencimiento="2026-12-31",
            estado="ACEPTADA",
            total_con_impuestos="2000.00",
        )
        user = User.objects.get(email="admin@test.local")

    client = _api_client_autenticado(tenant, user)
    payload = _dt_payload(columns=[{}, {}, {}, {}, {"search": {"value": "ACEPTADA"}}])
    resp = client.post(DT_URL, data=payload, format="json")
    assert resp.status_code == 200, resp.content
    numeros = [row["numero_cotizacion"] for row in resp.json()["data"]]
    assert "COT-ACEPTADA" in numeros
    assert "COT-BORRADOR" not in numeros


@pytest.mark.urls("config.urls_tenant")
@pytest.mark.django_db
def test_cotizacion_dt_busqueda_global(tenant, factory_empresa):
    empresa = factory_empresa()
    with schema_context(tenant.schema_name):
        Cotizacion.objects.create(
            empresa=empresa,
            numero_cotizacion="COT-SEARCH-UNICA",
            fecha_vencimiento="2026-12-31",
            estado="BORRADOR",
            total_con_impuestos="1000.00",
        )
        Cotizacion.objects.create(
            empresa=empresa,
            numero_cotizacion="COT-OTRA",
            fecha_vencimiento="2026-12-31",
            estado="BORRADOR",
            total_con_impuestos="1000.00",
        )
        user = User.objects.get(email="admin@test.local")

    client = _api_client_autenticado(tenant, user)
    payload = _dt_payload(search={"value": "SEARCH-UNICA"})
    resp = client.post(DT_URL, data=payload, format="json")
    assert resp.status_code == 200, resp.content
    numeros = [row["numero_cotizacion"] for row in resp.json()["data"]]
    assert "COT-SEARCH-UNICA" in numeros
    assert "COT-OTRA" not in numeros
