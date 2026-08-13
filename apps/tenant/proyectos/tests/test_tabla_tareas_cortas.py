"""
Test de la tabla server-rendered de Tareas Cortas (Fase 5-BIS, django-tables2 +
HTMX) -- panel "Nueva Tarea" embebido en Proyectos.

No existia cobertura previa para esta vista (backend nuevo, F31 Grupo 2).
Verifica:
1. La vista responde 200 tras login por sesion y renderiza tareas reales.
2. Los KPIs (total/en_proceso/completada/pendiente) se calculan server-side.
3. El filtro por estado (?estado=) y busqueda (?q=) se aplican server-side --
   reemplaza el filtrado client-side que hacia el Tabulator original
   (table.setFilter en nueva_tarea_list.js).
4. Los botones de accion usan data-uuid (uuid lookup, AGENTS.md).
"""
from datetime import date, timedelta

import pytest
from django_tenants.utils import schema_context

from apps.public.tenants.models import TenantMembership
from apps.tenant.empresa.models import Empresa
from apps.tenant.proyectos.models import TareaCorta


@pytest.fixture
def _tareas_cortas(tenant):
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.only('id').first()
        hoy = date.today()
        TareaCorta.objects.create(
            empresa=empresa, titulo='Instalar router',
            fecha_inicio=hoy, fecha_fin=hoy + timedelta(days=1),
            estado='PENDIENTE', prioridad='ALTA',
        )
        TareaCorta.objects.create(
            empresa=empresa, titulo='Revisar cableado',
            fecha_inicio=hoy, fecha_fin=hoy + timedelta(days=2),
            estado='EN_PROCESO', prioridad='NORMAL',
        )
        TareaCorta.objects.create(
            empresa=empresa, titulo='Configurar firewall',
            fecha_inicio=hoy, fecha_fin=hoy + timedelta(days=1),
            estado='COMPLETADA', prioridad='BAJA',
        )
    return empresa


def _login(client, django_user_model, tenant, empresa, username):
    admin_user = django_user_model.objects.create(username=username, email=f"{username}@example.com")
    TenantMembership.objects.create(client=tenant, user=admin_user, is_active=True, rol="ADMIN")
    with schema_context(tenant.schema_name):
        from apps.tenant.perfil.models import TenantProfile
        TenantProfile.objects.create(user=admin_user, empresa=empresa, rol="ADMIN")
        # django.contrib.sessions esta en TENANT_APPS -- force_login() debe
        # ejecutarse dentro del schema del tenant (ver test_tabla_view.py).
        client.force_login(admin_user)


@pytest.mark.django_db
def test_tabla_tareas_cortas_renderiza_y_calcula_kpis(client, django_user_model, tenant, _tareas_cortas):
    _login(client, django_user_model, tenant, _tareas_cortas, "admin_tc1")

    r = client.get("/ui/proyectos/tareas-cortas/tabla/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200, f"Status inesperado: {r.status_code}: {r.content[:500]}"
    assert r.context["kpi_total"] == 3
    assert r.context["kpi_proceso"] == 1
    assert r.context["kpi_completada"] == 1
    assert r.context["kpi_pendiente"] == 1

    html = r.content.decode("utf-8")
    assert "Instalar router" in html
    assert "Revisar cableado" in html
    assert "Configurar firewall" in html
    assert "btn-nt-avanzar" in html
    assert "btn-nt-delete" in html


@pytest.mark.django_db
def test_tabla_tareas_cortas_filtro_por_estado(client, django_user_model, tenant, _tareas_cortas):
    _login(client, django_user_model, tenant, _tareas_cortas, "admin_tc2")

    r = client.get(
        "/ui/proyectos/tareas-cortas/tabla/?estado=EN_PROCESO",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )

    assert r.status_code == 200
    assert r.context["kpi_total"] == 1
    html = r.content.decode("utf-8")
    assert "Revisar cableado" in html
    assert "Instalar router" not in html
    assert "Configurar firewall" not in html


@pytest.mark.django_db
def test_tabla_tareas_cortas_filtra_por_busqueda(client, django_user_model, tenant, _tareas_cortas):
    _login(client, django_user_model, tenant, _tareas_cortas, "admin_tc3")

    r = client.get(
        "/ui/proyectos/tareas-cortas/tabla/?q=firewall",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )

    assert r.status_code == 200
    html = r.content.decode("utf-8")
    assert "Configurar firewall" in html
    assert "Instalar router" not in html


@pytest.mark.django_db
def test_tabla_tareas_cortas_boton_acciones_usa_uuid(client, django_user_model, tenant, _tareas_cortas):
    _login(client, django_user_model, tenant, _tareas_cortas, "admin_tc4")

    with schema_context(tenant.schema_name):
        tarea = TareaCorta.objects.get(titulo='Instalar router')
    r = client.get("/ui/proyectos/tareas-cortas/tabla/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert f'data-uuid="{tarea.uuid}"' in r.content.decode("utf-8")
