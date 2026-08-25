"""
Aislamiento multi-tenant de las vistas HTML nuevas (django-tables2 + HTMX,
PLAN_UNICO_CORRECCIONES.md Fase 5-BIS) que reemplazan las grillas Tabulator
de empleados, contratos y resoluciones DIAN.

Estas vistas no pasan por DRF (no son ViewSets) -- usan SintelDSVMixin
directamente, asi que necesitan su propia verificacion, no basta con la
cobertura ya existente sobre /api/v1/empleados/.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django_tenants.utils import schema_context
from rest_framework import status

from apps.public.tenants.models import TenantMembership
from apps.tenant.empleados.models import Contrato, Devengo, Empleado, LiquidacionPrestacion, ResolucionDIAN
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile

User = get_user_model()


def _setup_tenant(tenant, username, email, sufijo):
    with schema_context(tenant.schema_name):
        emp = Empresa.objects.first()
        user = User.objects.create_user(username=username, email=email, password="password")
        TenantProfile.objects.create(user=user, empresa=emp, rol="ADMIN")
        with schema_context('public'):
            TenantMembership.objects.create(client=tenant, user=user, rol="ADMIN")

        empleado = Empleado.objects.create(
            empresa=emp, tipo_documento="CC", numero_documento=f"100{sufijo}",
            primer_nombre="Empleado", primer_apellido=sufijo,
            email=f"empleado{sufijo}@t.com", fecha_ingreso="2026-01-01",
            eps="EPS001", afp="AFP001", arl="ARL001",
        )
        contrato = Contrato.objects.create(
            empresa=emp, empleado=empleado, tipo="INDEFINIDO",
            fecha_inicio="2026-01-01", salario_mensual=2000000, cargo=f"Cargo {sufijo}",
        )
        ResolucionDIAN.objects.create(
            empresa=emp, numero_resolucion=f"RES-{sufijo}", rango_desde=1, rango_hasta=1000,
            fecha_resolucion="2026-01-01", fecha_fin="2027-01-01", prefijo=f"P{sufijo}",
        )
        Devengo.objects.create(
            empresa=emp, empleado=empleado, contrato=contrato,
            periodo_mes="2026-01", fecha_pago="2026-01-31",
            salario_base=2000000, salud_empleado=80000, pension_empleado=80000,
            neto_pagar=1840000,
        )
        LiquidacionPrestacion.objects.create(
            empresa=emp, empleado=empleado, contrato=contrato,
            tipo_liquidacion="PRIMA_SERVICIOS", fecha_corte="2026-06-30",
            dias_base_calculo=180, base_salarial=2000000, valor_total=1000000,
        )
        return empleado


@pytest.mark.django_db
def test_multitenant_isolation_empleados_tablas_html(client, tenant1, tenant2):
    _setup_tenant(tenant1, "euser1", "eu1@t.com", "Uno")
    _setup_tenant(tenant2, "euser2", "eu2@t.com", "Dos")

    with schema_context(tenant1.schema_name):
        user1 = User.objects.get(username="euser1")
        client.force_login(user1)
    host1 = f"{tenant1.schema_name}.sintel.net.co"

    # Empleados
    resp = client.get("/ui/empleados/tabla/", HTTP_HOST=host1)
    assert resp.status_code == status.HTTP_200_OK
    body = resp.content.decode()
    assert "100Uno" in body
    assert "100Dos" not in body

    # Contratos
    resp = client.get("/ui/empleados/contratos/tabla/", HTTP_HOST=host1)
    assert resp.status_code == status.HTTP_200_OK
    body = resp.content.decode()
    assert "Empleado Uno" in body
    assert "Empleado Dos" not in body

    # Resoluciones DIAN
    resp = client.get("/ui/empleados/resoluciones/tabla/", HTTP_HOST=host1)
    assert resp.status_code == status.HTTP_200_OK
    body = resp.content.decode()
    assert "RES-Uno" in body
    assert "RES-Dos" not in body

    # Sin sesion: debe redirigir a login (LoginRequiredMixin), no filtrar en silencio
    anon_client = Client()
    resp = anon_client.get("/ui/empleados/tabla/", HTTP_HOST=host1)
    assert resp.status_code in (status.HTTP_302_FOUND, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_multitenant_isolation_empleados_master_detail_html(client, tenant1, tenant2):
    """
    Aislamiento multi-tenant de las 4 vistas Master-Detail (Nominas y
    Liquidaciones) -- las mismas garantias que el resto de vistas HTML de
    esta app, mas la resolucion correcta de empleado_uuid entre tenants
    (un empleado_uuid de tenant2 no debe filtrar datos si se envia con
    sesion de tenant1, porque el filtro empresa_id+uuid no lo encontraria).
    """
    empleado1 = _setup_tenant(tenant1, "muser1", "mu1@t.com", "Uno")
    empleado2 = _setup_tenant(tenant2, "muser2", "mu2@t.com", "Dos")

    with schema_context(tenant1.schema_name):
        user1 = User.objects.get(username="muser1")
        client.force_login(user1)
    host1 = f"{tenant1.schema_name}.sintel.net.co"

    # Master de Nominas: solo empleados de tenant1
    resp = client.get("/ui/empleados/nominas/master/tabla/", HTTP_HOST=host1)
    assert resp.status_code == status.HTTP_200_OK
    body = resp.content.decode()
    assert "Empleado Uno" in body
    assert "Empleado Dos" not in body

    # Detail de Nominas: empleado propio -> debe mostrar su historial
    resp = client.get(f"/ui/empleados/nominas/detalle/tabla/?empleado_uuid={empleado1.uuid}", HTTP_HOST=host1)
    assert resp.status_code == status.HTTP_200_OK
    assert "2026-01" in resp.content.decode()

    # Detail de Nominas: empleado_uuid de OTRO tenant -> no debe resolver el empleado (IDOR)
    resp = client.get(f"/ui/empleados/nominas/detalle/tabla/?empleado_uuid={empleado2.uuid}", HTTP_HOST=host1)
    assert resp.status_code == status.HTTP_200_OK
    body = resp.content.decode()
    assert "Empleado Dos" not in body
    assert "Selecciona un empleado" in body  # cae al estado "sin empleado" -- uuid no encontrado en este tenant

    # Master de Liquidaciones: solo empleados de tenant1
    resp = client.get("/ui/empleados/liquidaciones/master/tabla/", HTTP_HOST=host1)
    assert resp.status_code == status.HTTP_200_OK
    body = resp.content.decode()
    assert "Empleado Uno" in body
    assert "Empleado Dos" not in body

    # Detail de Liquidaciones: empleado propio -> debe mostrar su historial
    resp = client.get(f"/ui/empleados/liquidaciones/detalle/tabla/?empleado_uuid={empleado1.uuid}", HTTP_HOST=host1)
    assert resp.status_code == status.HTTP_200_OK
    assert "Prima" in resp.content.decode()

    # Sin sesion: debe redirigir a login
    anon_client = Client()
    resp = anon_client.get("/ui/empleados/nominas/master/tabla/", HTTP_HOST=host1)
    assert resp.status_code in (status.HTTP_302_FOUND, status.HTTP_403_FORBIDDEN)
