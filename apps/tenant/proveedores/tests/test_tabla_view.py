"""
Test del Directorio de Proveedores, migrado a DataTables (ver
docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md, patron extendido aqui) --
POST /api/v1/proveedores/dt/ (ProveedorViewSet.dt()).

Verifica:
1. El endpoint responde 200 tras login por sesion, con el contrato DataTables.
2. cuentas_pagar_resumen usa ProveedorSelector.get_cuentas_pagar_resumen
   (misma logica que ProveedorViewSet.list() en la API DRF, via
   serializer_context) — un proveedor sin facturas de compra muestra
   cuentas_pagar_resumen.total_count == 0.
3. La busqueda global por razon_social/numero_documento filtra la grilla.
"""

import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context

from apps.public.tenants.models import TenantMembership
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor

User = get_user_model()

DT_URL = "/api/v1/proveedores/dt/"


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
def _dos_proveedores(tenant):
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.only("id").first()
        Proveedor.objects.create(
            empresa=empresa,
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            numero_documento="800111222",
            razon_social="Proveedor Alfa SAS",
            regimen_tributario="ORDINARIO",
            activo=True,
        )
        Proveedor.objects.create(
            empresa=empresa,
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            numero_documento="800333444",
            razon_social="Proveedor Beta SAS",
            regimen_tributario="ORDINARIO",
            activo=False,
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
def test_dt_proveedores_contrato_y_cartera_vacia(client, tenant, _admin_proveedores):
    with schema_context(tenant.schema_name):
        client.force_login(_admin_proveedores)

    resp = client.post(
        DT_URL,
        data=_dt_payload(),
        content_type="application/json",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )
    assert resp.status_code == 200, f"Status inesperado: {resp.status_code}: {resp.content[:500]}"
    body = resp.json()
    nombres = [row["razon_social"] for row in body["data"]]
    assert "Proveedor Alfa SAS" in nombres
    assert "Proveedor Beta SAS" in nombres
    for row in body["data"]:
        assert row["cuentas_pagar_resumen"]["total_count"] == 0


@pytest.mark.django_db
def test_dt_proveedores_busqueda_global(client, tenant, _admin_proveedores):
    with schema_context(tenant.schema_name):
        client.force_login(_admin_proveedores)

    resp = client.post(
        DT_URL,
        data=_dt_payload(search={"value": "Alfa"}),
        content_type="application/json",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )
    assert resp.status_code == 200
    nombres = [row["razon_social"] for row in resp.json()["data"]]
    assert "Proveedor Alfa SAS" in nombres
    assert "Proveedor Beta SAS" not in nombres
