"""
Tests del listado de Clientes: KPIs (HTMX, ClienteKpisView) + grilla
(DataTables, ClienteViewSet.dt()). Migrado desde django-tables2/HTMX -- ver
docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md (patron extendido aqui).

Verifica:
1. /ui/clientes/tabla/ (ClienteKpisView) responde 200 y calcula los KPIs
   correctamente server-side (ClienteSelector.get_kpis, reutilizado de la API).
2. POST /api/v1/clientes/dt/ sirve la grilla; el filtro por tipo (columna 1,
   tipo_persona) se aplica correctamente.
3. La columna Cartera usa ClienteSelector.get_cartera_resumen (misma logica
   que ClienteViewSet.list() en la API DRF, via serializer_context) — un
   cliente sin facturas muestra cartera_resumen.total_count == 0.
"""

import pytest
from django_tenants.utils import schema_context

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa

DT_URL = "/api/v1/clientes/dt/"


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


@pytest.fixture
def _dos_clientes(tenant):
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.only("id").first()
        Cliente.objects.create(
            empresa=empresa,
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            numero_documento="900111222",
            razon_social="Cliente Juridico SAS",
            regimen_tributario="ORDINARIO",
            es_retenedor=True,
            activo=True,
        )
        Cliente.objects.create(
            empresa=empresa,
            tipo_persona="NATURAL",
            tipo_documento="CC",
            numero_documento="1000222333",
            razon_social="Cliente Natural",
            regimen_tributario="SIMPLE",
            es_retenedor=False,
            activo=True,
        )
    return empresa


@pytest.mark.django_db
def test_tabla_clientes_kpis(client, tenant, admin_user, _dos_clientes):
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    r = client.get("/ui/clientes/tabla/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200, f"Status inesperado: {r.status_code}: {r.content[:500]}"
    assert r.context["kpis"]["total"] == 2
    assert r.context["kpis"]["activos"] == 2
    assert r.context["kpis"]["juridicas"] == 1
    assert r.context["kpis"]["naturales"] == 1
    assert r.context["kpis"]["retenedores"] == 1


@pytest.mark.django_db
def test_dt_clientes_contrato_y_cartera(client, tenant, admin_user, _dos_clientes):
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    resp = client.post(
        DT_URL,
        data=_dt_payload(),
        content_type="application/json",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )
    assert resp.status_code == 200
    body = resp.json()
    nombres = [row["razon_social"] for row in body["data"]]
    assert "Cliente Juridico SAS" in nombres
    assert "Cliente Natural" in nombres
    # Sin facturas -> cartera_map vacio -> cartera_resumen en cero
    for row in body["data"]:
        assert row["cartera_resumen"]["total_count"] == 0


@pytest.mark.django_db
def test_dt_clientes_filtro_columna_tipo_persona(client, tenant, admin_user, _dos_clientes):
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    payload = _dt_payload(
        columns=[
            {},
            {"search": {"value": "JURIDICA"}},
            {},
            {},
            {},
            {},
        ]
    )
    resp = client.post(
        DT_URL,
        data=payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )
    assert resp.status_code == 200
    nombres = [row["razon_social"] for row in resp.json()["data"]]
    assert "Cliente Juridico SAS" in nombres
    assert "Cliente Natural" not in nombres
