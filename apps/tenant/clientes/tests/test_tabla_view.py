"""
Test de la tabla server-rendered de Clientes (Fase 5-BIS, django-tables2 + HTMX).

Verifica:
1. La vista responde 200 tras login por sesion.
2. Los KPIs (total, activos, juridicas, naturales, retenedores) se calculan
   correctamente server-side (ClienteSelector.get_kpis, reutilizado de la API).
3. El filtro por tipo (?filtro=JURIDICA) se aplica a la tabla.
4. La columna Cartera usa ClienteSelector.get_cartera_resumen (misma logica
   que ClienteViewSet.list() en la API DRF) — un cliente sin facturas
   muestra "Sin facturas".
"""
import pytest
from django_tenants.utils import schema_context

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa


@pytest.fixture
def _dos_clientes(tenant):
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.only('id').first()
        Cliente.objects.create(
            empresa=empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900111222", razon_social="Cliente Juridico SAS",
            regimen_tributario="ORDINARIO", es_retenedor=True, activo=True,
        )
        Cliente.objects.create(
            empresa=empresa, tipo_persona="NATURAL", tipo_documento="CC",
            numero_documento="1000222333", razon_social="Cliente Natural",
            regimen_tributario="SIMPLE", es_retenedor=False, activo=True,
        )
    return empresa


@pytest.mark.django_db
def test_tabla_clientes_kpis_y_render(client, tenant, admin_user, _dos_clientes):
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    r = client.get("/ui/clientes/tabla/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200, f"Status inesperado: {r.status_code}: {r.content[:500]}"
    assert r.context["kpis"]["total"] == 2
    assert r.context["kpis"]["activos"] == 2
    assert r.context["kpis"]["juridicas"] == 1
    assert r.context["kpis"]["naturales"] == 1
    assert r.context["kpis"]["retenedores"] == 1

    html = r.content.decode("utf-8")
    assert "Cliente Juridico SAS" in html
    assert "Cliente Natural" in html
    # Sin facturas -> cartera_map vacio -> "Sin facturas" en ambas filas
    assert "Sin facturas" in html


@pytest.mark.django_db
def test_tabla_clientes_filtro_por_tipo(client, tenant, admin_user, _dos_clientes):
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    r = client.get("/ui/clientes/tabla/?filtro=JURIDICA", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200
    html = r.content.decode("utf-8")
    assert "Cliente Juridico SAS" in html
    assert "Cliente Natural" not in html
