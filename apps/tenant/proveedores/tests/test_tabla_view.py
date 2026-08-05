"""
Test de la tabla server-rendered de Proveedores (Fase 5-BIS, django-tables2 + HTMX).

Verifica:
1. La vista responde 200 tras login por sesion.
2. La columna "Cuentas por Pagar" usa ProveedorSelector.get_cuentas_pagar_resumen
   (misma logica que ProveedorViewSet.list() en la API DRF) — un proveedor sin
   facturas de compra muestra "Sin facturas".
3. La busqueda por razon_social/numero_documento filtra la tabla.
"""
import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context

from apps.public.tenants.models import TenantMembership
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor

User = get_user_model()


@pytest.fixture
def _dos_proveedores(tenant):
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.only('id').first()
        Proveedor.objects.create(
            empresa=empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="800111222", razon_social="Proveedor Alfa SAS",
            regimen_tributario="ORDINARIO", activo=True,
        )
        Proveedor.objects.create(
            empresa=empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="800333444", razon_social="Proveedor Beta SAS",
            regimen_tributario="ORDINARIO", activo=False,
        )
    return empresa


@pytest.fixture
def _admin_proveedores(tenant, _dos_proveedores):
    admin_user = User.objects.create(username="admin_prov", email="admin_prov@example.com")
    TenantMembership.objects.create(client=tenant, user=admin_user, is_active=True, rol="ADMIN")
    with schema_context(tenant.schema_name):
        TenantProfile.objects.create(user=admin_user, empresa=_dos_proveedores, rol="ADMIN")
    return admin_user


@pytest.mark.django_db
def test_tabla_proveedores_render_y_cartera_vacia(client, tenant, _admin_proveedores):
    with schema_context(tenant.schema_name):
        client.force_login(_admin_proveedores)

    r = client.get("/ui/proveedores/tabla/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200, f"Status inesperado: {r.status_code}: {r.content[:500]}"
    html = r.content.decode("utf-8")
    assert "Proveedor Alfa SAS" in html
    assert "Proveedor Beta SAS" in html
    assert "Sin facturas" in html
    # data-uuid en <tr> para el click-en-fila (row_attrs en tables.py)
    assert 'data-uuid="' in html


@pytest.mark.django_db
def test_tabla_proveedores_busqueda(client, tenant, _admin_proveedores):
    with schema_context(tenant.schema_name):
        client.force_login(_admin_proveedores)

    r = client.get("/ui/proveedores/tabla/?q=Alfa", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200
    html = r.content.decode("utf-8")
    assert "Proveedor Alfa SAS" in html
    assert "Proveedor Beta SAS" not in html
