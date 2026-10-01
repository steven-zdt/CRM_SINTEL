"""
Aislamiento multi-tenant de los listados de Contabilidad: Plan de Cuentas,
Periodos, Asientos, Retenciones y Plantillas migraron a DataTables (ver
docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md) -- todos POST contra
/api/v1/contabilidad/{cuentas-contables,periodos-contables,
asientos-contables,retenciones,plantillas-contables}/dt/.

Estos endpoints son DRF (BaseTenantViewSet) y ya tienen cobertura de
aislamiento generica en otros tests de la suite; este archivo se mantiene
como verificacion de extremo a extremo combinada para las 5 grillas del
modulo, historico desde cuando las vistas HTML (django-tables2 + HTMX, no
DRF) necesitaban su propia verificacion.
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


def _setup_tenant(tenant, username, email, empresa_nit_suffix, sufijo, mes):
    with schema_context(tenant.schema_name):
        emp = Empresa.objects.first()
        user = User.objects.create_user(username=username, email=email, password="password")
        TenantProfile.objects.create(user=user, empresa=emp, rol="ADMIN")
        with schema_context("public"):
            TenantMembership.objects.create(client=tenant, user=user, rol="ADMIN")

        CuentaContable.objects.create(
            empresa=emp,
            codigo=f"11{sufijo}",
            nombre=f"Caja General {sufijo}",
            tipo="ACTIVO",
        )
        PeriodoContable.objects.create(
            empresa=emp,
            periodo=f"2026-{mes}",
            fecha_inicio=f"2026-{mes}-01",
            fecha_fin=f"2026-{mes}-28",
            estado="ABIERTO",
        )
        AsientoContable.objects.create(
            empresa=emp,
            numero=f"AS-{sufijo}",
            fecha="2026-01-15",
            descripcion=f"Asiento Tenant {sufijo}",
            estado="BORRADOR",
            total_debe=1000,
            total_haber=1000,
        )
        Retencion.objects.create(
            empresa=emp,
            tipo="RETEFUENTE",
            porcentaje="2.50",
            base=1000,
            monto=25,
            documento_origen_app="facturas",
            documento_origen_modelo="Factura",
            documento_origen_id=1,
            naturaleza="VENTA",
        )
        PlantillaContable.objects.create(
            empresa=emp,
            nombre=f"Plantilla Venta {sufijo}",
            tipo_transaccion="VENTA",
            activo=True,
        )
        return user


@pytest.mark.django_db
def test_multitenant_isolation_contabilidad_tablas_html(client, tenant1, tenant2):
    _setup_tenant(tenant1, "cuser1", "cu1@t.com", "111", "Uno", mes="01")
    _setup_tenant(tenant2, "cuser2", "cu2@t.com", "222", "Dos", mes="02")

    with schema_context(tenant1.schema_name):
        user1 = User.objects.get(username="cuser1")

    # force_login debe escribir la sesion en el esquema del tenant: sessions
    # esta en TENANT_APPS (aislado por esquema) y la request real solo la lee
    # despues de que TenantMainMiddleware cambia de esquema (ver settings.py).
    with schema_context(tenant1.schema_name):
        client.force_login(user1)
    host1 = f"{tenant1.schema_name}.sintel.net.co"
    dt_payload = {
        "draw": 1,
        "start": 0,
        "length": 10,
        "search": {"value": ""},
        "order": [],
        "columns": [],
    }

    # Cuentas
    resp = client.post(
        "/api/v1/contabilidad/cuentas-contables/dt/",
        data=dt_payload,
        content_type="application/json",
        HTTP_HOST=host1,
    )
    assert resp.status_code == status.HTTP_200_OK
    nombres = [row["nombre"] for row in resp.json()["data"]]
    assert "Caja General Uno" in nombres
    assert "Caja General Dos" not in nombres

    # Periodos
    resp = client.post(
        "/api/v1/contabilidad/periodos-contables/dt/",
        data=dt_payload,
        content_type="application/json",
        HTTP_HOST=host1,
    )
    assert resp.status_code == status.HTTP_200_OK
    periodos = [row["periodo"] for row in resp.json()["data"]]
    assert "2026-01" in periodos
    assert "2026-02" not in periodos

    # Asientos
    resp = client.post(
        "/api/v1/contabilidad/asientos-contables/dt/",
        data=dt_payload,
        content_type="application/json",
        HTTP_HOST=host1,
    )
    assert resp.status_code == status.HTTP_200_OK
    descripciones = [row["descripcion"] for row in resp.json()["data"]]
    assert "Asiento Tenant Uno" in descripciones
    assert "Asiento Tenant Dos" not in descripciones

    # Retenciones
    resp = client.post(
        "/api/v1/contabilidad/retenciones/dt/",
        data=dt_payload,
        content_type="application/json",
        HTTP_HOST=host1,
    )
    assert resp.status_code == status.HTTP_200_OK

    # Plantillas
    resp = client.post(
        "/api/v1/contabilidad/plantillas-contables/dt/",
        data=dt_payload,
        content_type="application/json",
        HTTP_HOST=host1,
    )
    assert resp.status_code == status.HTTP_200_OK
    plantillas = [row["nombre"] for row in resp.json()["data"]]
    assert "Plantilla Venta Uno" in plantillas
    assert "Plantilla Venta Dos" not in plantillas

    # Sin sesion: ningun endpoint DataTables (DRF) debe filtrar en silencio --
    # todos deben rechazar con 401/403.
    anon_client = Client()
    for path in (
        "cuentas-contables",
        "periodos-contables",
        "asientos-contables",
        "retenciones",
        "plantillas-contables",
    ):
        resp = anon_client.post(
            f"/api/v1/contabilidad/{path}/dt/",
            data=dt_payload,
            content_type="application/json",
            HTTP_HOST=host1,
        )
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN), path
