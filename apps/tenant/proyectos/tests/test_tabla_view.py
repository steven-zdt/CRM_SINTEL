"""
Test de la tabla server-rendered de Proyectos (Fase 5-BIS, django-tables2 + HTMX).

Verifica:
1. La vista responde 200 tras login por sesion.
2. Los KPIs agregados (total, cartera, avance promedio, etc.) se calculan
   correctamente server-side sobre TODOS los proyectos filtrados por
   empresa_id -- no solo la pagina visible.
3. El filtro por fase (?fase=EJECUCION) se aplica tanto a la tabla como a
   los KPIs, replicando el comportamiento client-side original
   (dataFiltered recalculaba los KPIs sobre las filas filtradas).
"""
from decimal import Decimal

import pytest
from django_tenants.utils import schema_context

from apps.public.tenants.models import TenantMembership
from apps.tenant.empresa.models import Empresa
from apps.tenant.proyectos.models import Proyecto


@pytest.fixture
def _tres_proyectos(tenant):
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.only('id').first()
        Proyecto.objects.create(
            empresa=empresa, nombre='Proyecto Ejecucion',
            fase_actual='EJECUCION', estado_tarea='EN_PROCESO',
            valor_contrato_proyectado=Decimal('1000000.00'), porcentaje_avance=60,
        )
        Proyecto.objects.create(
            empresa=empresa, nombre='Proyecto Cierre',
            fase_actual='CIERRE', estado_tarea='COMPLETADO',
            valor_contrato_proyectado=Decimal('2000000.00'), porcentaje_avance=100,
        )
        Proyecto.objects.create(
            empresa=empresa, nombre='Proyecto Borrador',
            fase_actual='BORRADOR', estado_tarea='PENDIENTE',
            valor_contrato_proyectado=Decimal('500000.00'), porcentaje_avance=0,
        )
    return empresa


@pytest.mark.django_db
def test_tabla_proyectos_kpis_agregados_sobre_todo_el_filtrado(client, django_user_model, tenant, _tres_proyectos):
    admin_user = django_user_model.objects.create(username="admin_proy", email="admin_proy@example.com")
    TenantMembership.objects.create(client=tenant, user=admin_user, is_active=True, rol="ADMIN")

    with schema_context(tenant.schema_name):
        from apps.tenant.perfil.models import TenantProfile
        TenantProfile.objects.create(user=admin_user, empresa=_tres_proyectos, rol="ADMIN")
        # django.contrib.sessions esta en TENANT_APPS (sesiones aisladas por
        # schema, ver config/settings.py) -- force_login() debe ejecutarse
        # dentro del schema del tenant para que la sesion se guarde en la
        # tabla django_session correcta, la misma que consultara luego
        # SessionMiddleware una vez el request cambie a este schema.
        client.force_login(admin_user)

    r = client.get("/ui/proyectos/tabla/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200, f"Status inesperado: {r.status_code}: {r.content[:500]}"
    assert r.context["kpis"]["total"] == 3
    assert r.context["kpis"]["ejecucion"] == 1
    assert r.context["kpis"]["completados"] == 1
    assert r.context["kpis"]["pendientes"] == 1
    assert r.context["kpis"]["cartera"] == Decimal("3500000.00")
    assert r.context["kpis"]["avance_prom"] == 53  # round((60+100+0)/3)

    html = r.content.decode("utf-8")
    assert "Proyecto Ejecucion" in html
    assert "Proyecto Cierre" in html
    assert "Proyecto Borrador" in html


@pytest.mark.django_db
def test_tabla_proyectos_filtro_por_fase_afecta_tabla_y_kpis(client, django_user_model, tenant, _tres_proyectos):
    admin_user = django_user_model.objects.create(username="admin_proy2", email="admin_proy2@example.com")
    TenantMembership.objects.create(client=tenant, user=admin_user, is_active=True, rol="ADMIN")

    with schema_context(tenant.schema_name):
        from apps.tenant.perfil.models import TenantProfile
        TenantProfile.objects.create(user=admin_user, empresa=_tres_proyectos, rol="ADMIN")
        client.force_login(admin_user)

    r = client.get("/ui/proyectos/tabla/?fase=EJECUCION", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200
    assert r.context["kpis"]["total"] == 1
    assert r.context["kpis"]["cartera"] == Decimal("1000000.00")

    html = r.content.decode("utf-8")
    assert "Proyecto Ejecucion" in html
    assert "Proyecto Cierre" not in html
    assert "Proyecto Borrador" not in html
