"""
Tests del listado de Proyectos: KPIs (HTMX, ProyectoKpisView) + grilla
(DataTables, ProyectoViewSet.dt()). Migrado desde django-tables2/HTMX -- ver
docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md (patron extendido aqui).

Verifica:
1. /ui/proyectos/tabla/ (ProyectoKpisView) responde 200 y calcula los KPIs
   agregados (total, cartera, avance promedio, etc.) correctamente
   server-side sobre TODOS los proyectos de la empresa. A diferencia de la
   version django-tables2, los KPIs ya no se filtran por fase (?fase=) --
   simplificacion deliberada de esta pasada, los KPIs reflejan siempre el
   total de la empresa.
2. POST /api/v1/proyectos/dt/ sirve la grilla; el filtro por columna
   (columna 1, fase_actual) se aplica correctamente.
"""

from decimal import Decimal

import pytest
from django_tenants.utils import schema_context

from apps.public.tenants.models import TenantMembership
from apps.tenant.empresa.models import Empresa
from apps.tenant.proyectos.models import Proyecto

DT_URL = "/api/v1/proyectos/dt/"


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
def _tres_proyectos(tenant):
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.only("id").first()
        Proyecto.objects.create(
            empresa=empresa,
            nombre="Proyecto Ejecucion",
            fase_actual="EJECUCION",
            estado_tarea="EN_PROCESO",
            valor_contrato_proyectado=Decimal("1000000.00"),
            porcentaje_avance=60,
        )
        Proyecto.objects.create(
            empresa=empresa,
            nombre="Proyecto Cierre",
            fase_actual="CIERRE",
            estado_tarea="COMPLETADO",
            valor_contrato_proyectado=Decimal("2000000.00"),
            porcentaje_avance=100,
        )
        Proyecto.objects.create(
            empresa=empresa,
            nombre="Proyecto Borrador",
            fase_actual="BORRADOR",
            estado_tarea="PENDIENTE",
            valor_contrato_proyectado=Decimal("500000.00"),
            porcentaje_avance=0,
        )
    return empresa


def _login(client, django_user_model, tenant, empresa, username, email):
    admin_user = django_user_model.objects.create(username=username, email=email)
    TenantMembership.objects.create(client=tenant, user=admin_user, is_active=True, rol="ADMIN")
    with schema_context(tenant.schema_name):
        from apps.tenant.perfil.models import TenantProfile

        TenantProfile.objects.create(user=admin_user, empresa=empresa, rol="ADMIN")
        # django.contrib.sessions esta en TENANT_APPS (sesiones aisladas por
        # schema, ver config/settings.py) -- force_login() debe ejecutarse
        # dentro del schema del tenant para que la sesion se guarde en la
        # tabla django_session correcta, la misma que consultara luego
        # SessionMiddleware una vez el request cambie a este schema.
        client.force_login(admin_user)
    return admin_user


@pytest.mark.django_db
def test_tabla_proyectos_kpis_agregados(client, django_user_model, tenant, _tres_proyectos):
    _login(
        client, django_user_model, tenant, _tres_proyectos, "admin_proy", "admin_proy@example.com"
    )

    r = client.get("/ui/proyectos/tabla/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200, f"Status inesperado: {r.status_code}: {r.content[:500]}"
    assert r.context["kpis"]["total"] == 3
    assert r.context["kpis"]["ejecucion"] == 1
    assert r.context["kpis"]["completados"] == 1
    assert r.context["kpis"]["pendientes"] == 1
    assert r.context["kpis"]["cartera"] == Decimal("3500000.00")
    assert r.context["kpis"]["avance_prom"] == 53  # round((60+100+0)/3)


@pytest.mark.django_db
def test_dt_proyectos_contrato_basico(client, django_user_model, tenant, _tres_proyectos):
    _login(
        client, django_user_model, tenant, _tres_proyectos, "admin_proy2", "admin_proy2@example.com"
    )

    resp = client.post(
        DT_URL,
        data=_dt_payload(),
        content_type="application/json",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )
    assert resp.status_code == 200
    nombres = [row["nombre"] for row in resp.json()["data"]]
    assert "Proyecto Ejecucion" in nombres
    assert "Proyecto Cierre" in nombres
    assert "Proyecto Borrador" in nombres


@pytest.mark.django_db
def test_dt_proyectos_filtro_columna_fase(client, django_user_model, tenant, _tres_proyectos):
    _login(
        client, django_user_model, tenant, _tres_proyectos, "admin_proy3", "admin_proy3@example.com"
    )

    payload = _dt_payload(
        columns=[
            {},
            {"search": {"value": "EJECUCION"}},
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
    body = resp.json()
    nombres = [row["nombre"] for row in body["data"]]
    assert "Proyecto Ejecucion" in nombres
    assert "Proyecto Cierre" not in nombres
    assert "Proyecto Borrador" not in nombres
    assert body["recordsFiltered"] == 1
