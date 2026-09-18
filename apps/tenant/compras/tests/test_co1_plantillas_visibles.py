"""
Regresion (2026-09-12, hallazgo CO-1, docs/remediation/AUDIT_BASELINE_20260912.md):
una PlantillaOrdenCompra con vigente=False era invisible en toda la UI --
el unico punto de acceso era el dropdown de "Nueva Orden", que fuerza
vigente_only=True (PlantillaOrdenCompraViewSet.render_offcanvas_crear). No
existia ninguna pantalla donde ver/gestionar las plantillas ya creadas.

Fix: pantalla nueva (PlantillaOrdenCompraTable + PlantillaOrdenCompraTableView,
ruta compras:plantillas-tabla) que lista TODAS las plantillas
(vigente_only=False), con acciones Editar y Activar/Desactivar por fila.
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
        with schema_context('public'):
            TenantMembership.objects.create(client=tenant1, user=user, rol="ADMIN")

        PlantillaOrdenCompra.objects.create(
            empresa=empresa, nombre="Plantilla Activa CO1", prefijo="ACT",
            rango_desde=1, rango_hasta=1000, consecutivo_actual=1, vigente=True,
        )
        PlantillaOrdenCompra.objects.create(
            empresa=empresa, nombre="Plantilla Inactiva CO1", prefijo="INA",
            rango_desde=1, rango_hasta=1000, consecutivo_actual=1, vigente=False,
        )

    with schema_context(tenant1.schema_name):
        client.force_login(user)

    resp = client.get("/ui/compras/plantillas/tabla/", HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    body = resp.content.decode()

    # Antes del fix: no existia esta ruta (404) y no habia forma de ver
    # ninguna plantilla inactiva en ninguna pantalla.
    assert "Plantilla Activa CO1" in body
    assert "Plantilla Inactiva CO1" in body, (
        "La plantilla inactiva sigue sin aparecer en la pantalla de gestion."
    )
