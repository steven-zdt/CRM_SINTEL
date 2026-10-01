"""
Regresion (2026-09-12, hallazgo CO-1, docs/remediation/AUDIT_BASELINE_20260912.md):
una PlantillaOrdenCompra con vigente=False era invisible en toda la UI --
el unico punto de acceso era el dropdown de "Nueva Orden", que fuerza
vigente_only=True (PlantillaOrdenCompraViewSet.render_offcanvas_crear). No
existia ninguna pantalla donde ver/gestionar las plantillas ya creadas.

Fix: pantalla nueva que lista TODAS las plantillas (vigente_only=False), con
acciones Editar y Activar/Desactivar por fila. Migrada a DataTables -- POST
/api/v1/compras/plantillas/dt/ (PlantillaOrdenCompraViewSet.dt(), ver
docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md); PlantillaOrdenCompraTable/
PlantillaOrdenCompraTableView (django-tables2) retirados.
"""

import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from rest_framework import status

from apps.public.tenants.models import TenantMembership
from apps.tenant.compras.models import PlantillaOrdenCompra
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile

User = get_user_model()


@pytest.mark.django_db
def test_plantilla_inactiva_aparece_en_pantalla_de_gestion(client, tenant1):
    with schema_context(tenant1.schema_name):
        empresa = Empresa.objects.first()
        user = User.objects.create_user(username="co1_user", email="co1@t.com", password="password")
        TenantProfile.objects.create(user=user, empresa=empresa, rol="ADMIN")
        with schema_context("public"):
            TenantMembership.objects.create(client=tenant1, user=user, rol="ADMIN")

        PlantillaOrdenCompra.objects.create(
            empresa=empresa,
            nombre="Plantilla Activa CO1",
            prefijo="ACT",
            rango_desde=1,
            rango_hasta=1000,
            consecutivo_actual=1,
            vigente=True,
        )
        PlantillaOrdenCompra.objects.create(
            empresa=empresa,
            nombre="Plantilla Inactiva CO1",
            prefijo="INA",
            rango_desde=1,
            rango_hasta=1000,
            consecutivo_actual=1,
            vigente=False,
        )

    with schema_context(tenant1.schema_name):
        client.force_login(user)

    dt_payload = {
        "draw": 1,
        "start": 0,
        "length": 10,
        "search": {"value": ""},
        "order": [],
        "columns": [],
    }
    resp = client.post(
        "/api/v1/compras/plantillas/dt/",
        data=dt_payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK, resp.content
    nombres = [row["nombre"] for row in resp.json()["data"]]

    # Antes del fix: no existia esta ruta y no habia forma de ver ninguna
    # plantilla inactiva en ninguna pantalla.
    assert "Plantilla Activa CO1" in nombres
    assert (
        "Plantilla Inactiva CO1" in nombres
    ), "La plantilla inactiva sigue sin aparecer en la pantalla de gestion."
