"""
Test de la tabla server-rendered de Areas (Fase 5-BIS, django-tables2 + HTMX).

Verifica:
1. La vista responde 200 tras login por sesion.
2. Las areas de la empresa se renderizan con su sede correctamente.
3. La busqueda por nombre/codigo/sede filtra la tabla.
4. No se expone ninguna columna "Responsable" (campo huerfano que no existe
   en el modelo Area ni en ningun serializer -- ver nota en tables.py).
"""
import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context

from apps.public.tenants.models import TenantMembership
from apps.tenant.empresa.models import Area, Empresa, Sede
from apps.tenant.perfil.models import TenantProfile

User = get_user_model()


@pytest.fixture
def _admin_con_areas(tenant):
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.only('id').first()
        sede = Sede.objects.create(empresa=empresa, nombre='Sede Principal')
        Area.objects.create(empresa=empresa, sede=sede, nombre='Contabilidad', codigo_funcionamiento='CTB-01')
        Area.objects.create(empresa=empresa, sede=sede, nombre='Recursos Humanos', codigo_funcionamiento='RRHH-01')

        admin_user = User.objects.create(username="admin_area", email="admin_area@example.com")
        TenantProfile.objects.create(user=admin_user, empresa=empresa, rol="ADMIN")

    TenantMembership.objects.create(client=tenant, user=admin_user, is_active=True, rol="ADMIN")
    return admin_user


@pytest.mark.django_db
def test_tabla_areas_render(client, tenant, _admin_con_areas):
    with schema_context(tenant.schema_name):
        client.force_login(_admin_con_areas)

    r = client.get("/ui/empresa/areas/tabla/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200, f"Status inesperado: {r.status_code}: {r.content[:500]}"
    html = r.content.decode("utf-8")
    assert "Contabilidad" in html
    assert "Recursos Humanos" in html
    assert "CTB-01" in html
    assert "Sede Principal" in html
    assert "Responsable" not in html  # columna huerfana deliberadamente omitida


@pytest.mark.django_db
def test_tabla_areas_busqueda(client, tenant, _admin_con_areas):
    with schema_context(tenant.schema_name):
        client.force_login(_admin_con_areas)

    r = client.get("/ui/empresa/areas/tabla/?q=Contabilidad", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200
    html = r.content.decode("utf-8")
    assert "Contabilidad" in html
    assert "Recursos Humanos" not in html
