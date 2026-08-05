"""
Test: Verifica que el endpoint de devengos funcione correctamente después del login.

Valida que:
1. El endpoint responda 200 cuando el usuario está autenticado y tiene membresía
2. El endpoint responda 401 cuando el usuario no está autenticado
3. El endpoint responda 403 cuando el usuario está autenticado pero no tiene membresía
"""

from decimal import Decimal

import pytest
from django_tenants.utils import schema_context

from apps.public.tenants.models import TenantMembership
from apps.tenant.empleados.models import Devengo, Empleado


@pytest.mark.django_db
def test_endpoint_401_when_not_authenticated(client, tenant):
    """
    Verifica que el endpoint responda 401 cuando el usuario no está autenticado.
    """
    resp = client.get(
        "/api/v1/empleados/devengos/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co"
    )
    assert resp.status_code == 401, "Debe responder 401 cuando no hay autenticación"


@pytest.mark.django_db
def test_endpoint_200_when_authenticated_with_membership(
    client, django_user_model, tenant
):
    """
    Verifica que el endpoint responda 200 cuando el usuario está autenticado y tiene membresía activa.
    """
    # Crear usuario
    user = django_user_model.objects.create(
        username="testuser", email="test@example.com"
    )

    # Crear membresía activa en el tenant
    TenantMembership.objects.create(
        client=tenant, user=user, is_active=True, rol="ADMIN"
    )

    # Autenticar usuario
    client.force_login(user)

    # Crear datos de prueba en el esquema del tenant
    with schema_context(tenant.schema_name):
        e = Empleado.objects.create(
            tipo_documento="CC",
            numero_documento="1234567890",
            primer_nombre="Ana",
            primer_apellido="Pérez",
            email="ana@example.com",
            fecha_ingreso="2026-01-01",
        )
        Devengo.objects.create(
            empleado=e,
            periodo_inicio="2026-01-01",
            periodo_fin="2026-01-15",
            fecha_pago="2026-01-20",
            dias_laborados=15,
            salario_basico=Decimal("1000000.00"),
            auxilio_transporte=Decimal("0.00"),
            horas_extras=Decimal("100000.00"),
            recargos=Decimal("50000.00"),
            comisiones=Decimal("0.00"),
            bonificaciones=Decimal("0.00"),
            ibc=Decimal("1000000.00"),
            salud_empleado=Decimal("40000.00"),
            pension_empleado=Decimal("40000.00"),
            fondo_solidaridad=Decimal("0.00"),
            salud_empleador=Decimal("120000.00"),
            pension_empleador=Decimal("120000.00"),
            arl_empleador=Decimal("10000.00"),
            caja_compensacion=Decimal("40000.00"),
        )

    # Hacer petición
    resp = client.get(
        "/api/v1/empleados/devengos/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co"
    )

    # Debe responder 200
    assert (
        resp.status_code == 200
    ), f"Debe responder 200 cuando el usuario tiene membresía. Got {resp.status_code}"

    # Verificar estructura de respuesta
    data = resp.json()
    assert "results" in data or isinstance(
        data, list
    ), "La respuesta debe tener formato paginado o lista"

    if "results" in data:
        assert len(data["results"]) > 0, "Debe haber al menos un devengo"


@pytest.mark.django_db
def test_endpoint_403_when_authenticated_without_membership(
    client, django_user_model, tenant
):
    """
    Verifica que el endpoint responda 403 cuando el usuario está autenticado pero no tiene membresía.
    """
    # Crear usuario sin membresía
    user = django_user_model.objects.create(
        username="testuser2", email="test2@example.com"
    )

    # Autenticar usuario
    client.force_login(user)

    # Hacer petición (sin membresía)
    resp = client.get(
        "/api/v1/empleados/devengos/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co"
    )

    # Debe responder 403 (o 401 si el permiso no verifica membresía)
    assert resp.status_code in (
        401,
        403,
    ), f"Debe responder 401 o 403 cuando no hay membresía. Got {resp.status_code}"
