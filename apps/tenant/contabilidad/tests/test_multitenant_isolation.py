"""
Aislamiento multi-tenant de las vistas HTML nuevas (django-tables2 + HTMX,
PLAN_UNICO_CORRECCIONES.md Fase 5-BIS) que reemplazan las grillas Tabulator
de contabilidad (cuentas, periodos, asientos, retenciones, plantillas).

Estas vistas no pasan por DRF (no son ViewSets) -- usan SintelDSVMixin
directamente, asi que necesitan su propia verificacion, no basta con la
cobertura ya existente sobre /api/v1/contabilidad/.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django_tenants.utils import schema_context
from rest_framework import status

from apps.public.tenants.models import TenantMembership
from apps.tenant.contabilidad.models import (
    AsientoContable,
    CuentaContable,
    PeriodoContable,
    PlantillaContable,
    Retencion,
)
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile

User = get_user_model()


def _setup_tenant(tenant, username, email, empresa_nit_suffix, sufijo):
    with schema_context(tenant.schema_name):
        emp = Empresa.objects.first()
        user = User.objects.create_user(username=username, email=email, password="password")
        TenantProfile.objects.create(user=user, empresa=emp, rol="ADMIN")
        with schema_context('public'):
            TenantMembership.objects.create(client=tenant, user=user, rol="ADMIN")

        CuentaContable.objects.create(
            empresa=emp, codigo=f"11{sufijo}", nombre=f"Caja General {sufijo}", tipo="ACTIVO",
        )
        PeriodoContable.objects.create(
            empresa=emp, periodo=f"2026-0{sufijo}", fecha_inicio="2026-01-01", fecha_fin="2026-01-31",
            estado="ABIERTO",
        )
        AsientoContable.objects.create(
            empresa=emp, numero=f"AS-{sufijo}", fecha="2026-01-15",
            descripcion=f"Asiento Tenant {sufijo}", estado="BORRADOR",
            total_debe=1000, total_haber=1000,
        )
        Retencion.objects.create(
            empresa=emp, tipo="RETEFUENTE", porcentaje="2.50", base=1000, monto=25,
            documento_origen_app="facturas", documento_origen_modelo="Factura",
            documento_origen_id=1, naturaleza="VENTA",
        )
        PlantillaContable.objects.create(
            empresa=emp, nombre=f"Plantilla Venta {sufijo}", tipo_transaccion="VENTA", activo=True,
        )
        return user


@pytest.mark.django_db
def test_multitenant_isolation_contabilidad_tablas_html(client, tenant1, tenant2):
    _setup_tenant(tenant1, "cuser1", "cu1@t.com", "111", "Uno")
    _setup_tenant(tenant2, "cuser2", "cu2@t.com", "222", "Dos")

    with schema_context(tenant1.schema_name):
        user1 = User.objects.get(username="cuser1")

    # force_login debe escribir la sesion en el esquema del tenant: sessions
    # esta en TENANT_APPS (aislado por esquema) y la request real solo la lee
    # despues de que TenantMainMiddleware cambia de esquema (ver settings.py).
    with schema_context(tenant1.schema_name):
        client.force_login(user1)
    host1 = f"{tenant1.schema_name}.sintel.net.co"

    # Cuentas
    resp = client.get("/ui/contabilidad/cuentas/tabla/", HTTP_HOST=host1)
    assert resp.status_code == status.HTTP_200_OK
    body = resp.content.decode()
    assert "Caja General Uno" in body
    assert "Caja General Dos" not in body

    # Periodos
    resp = client.get("/ui/contabilidad/periodos/tabla/", HTTP_HOST=host1)
    assert resp.status_code == status.HTTP_200_OK
    body = resp.content.decode()
    assert "2026-0Uno" in body
    assert "2026-0Dos" not in body

    # Asientos
    resp = client.get("/ui/contabilidad/asientos/tabla/", HTTP_HOST=host1)
    assert resp.status_code == status.HTTP_200_OK
    body = resp.content.decode()
    assert "Asiento Tenant Uno" in body
    assert "Asiento Tenant Dos" not in body

    # Retenciones
    resp = client.get("/ui/contabilidad/retenciones/tabla/", HTTP_HOST=host1)
    assert resp.status_code == status.HTTP_200_OK

    # Plantillas
    resp = client.get("/ui/contabilidad/plantillas/tabla/", HTTP_HOST=host1)
    assert resp.status_code == status.HTTP_200_OK
    body = resp.content.decode()
    assert "Plantilla Venta Uno" in body
    assert "Plantilla Venta Dos" not in body

    # Sin sesion: debe redirigir a login (LoginRequiredMixin), no filtrar en silencio
    anon_client = Client()
    resp = anon_client.get("/ui/contabilidad/cuentas/tabla/", HTTP_HOST=host1)
    assert resp.status_code in (status.HTTP_302_FOUND, status.HTTP_403_FORBIDDEN)
