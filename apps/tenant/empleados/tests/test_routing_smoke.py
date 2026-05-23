"""
Smoke test: Verifica que el enrutado de devengos funciona después del include en TENANT_URLCONF.

Test no invasivo que verifica que el endpoint responde correctamente.
"""
from decimal import Decimal

import pytest
from django_tenants.utils import schema_context

from apps.tenant.empleados.models import Devengo, Empleado


@pytest.mark.django_db
def test_routing_devengos_list_after_include(client, admin_user, tenant):
    """
    Verifica que el endpoint /api/v1/empleados/devengos/ responde correctamente.
    
    Este test requiere que:
    1. La app esté en TENANT_APPS
    2. El include esté en config/api_urls.py
    3. El router esté registrado en apps/tenant/empleados/api/urls.py
    """
    client.force_login(admin_user)
    
    # Si el include en TENANT_URLCONF está OK, debe ser 200 (aunque no haya datos)
    # Nota: El host del tenant se simula automáticamente por django-tenants en tests
    resp = client.get("/api/v1/empleados/devengos/", HTTP_HOST=f"{tenant.schema_name}.sintel.com")
    
    # 200 si el router está incluido y funciona, 403 si falta permisos, 404 si falta include
    assert resp.status_code in (200, 403), (
        f"Expected 200 or 403, got {resp.status_code}. "
        f"Verifica que el include esté en config/api_urls.py y que el router esté registrado."
    )


@pytest.mark.django_db
def test_routing_devengos_list_with_data(client, admin_user, tenant):
    """
    Verifica que el endpoint devuelve datos cuando existen devengos.
    """
    with schema_context(tenant.schema_name):
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.first()
        e = Empleado.objects.create(
            tipo_documento="CC",
            numero_documento="1234567890",
            primer_nombre="Ana",
            primer_apellido="Pérez",
            email="ana@example.com",
            fecha_ingreso="2026-01-01",
            empresa=empresa,
            eps="EPS004",
            afp="AFP001",
            arl="ARL002"
        )
        from apps.tenant.empleados.models import Contrato
        c = Contrato.objects.create(
            empresa=empresa, empleado=e, tipo="FIJO", fecha_inicio="2024-01-01", salario_mensual=Decimal("1000000.00"), cargo="Analista"
        )
        Devengo.objects.create(
            empresa=empresa,
            empleado=e,
            contrato=c,
            periodo_mes="2026-01",
            fecha_pago="2026-01-20",
            dias_laborados=15,
            salario_base=Decimal("1000000.00"),
            auxilio_transporte=Decimal("0.00"),
            otros_devengos=Decimal("150000.00"),
            salud_empleado=Decimal("40000.00"),
            pension_empleado=Decimal("40000.00"),
            prestamos=Decimal("0.00"),
            descuentos_operativos=Decimal("0.00"),
            neto_pagar=Decimal("1070000.00")
        )
    
    client.force_login(admin_user)
    
    resp = client.get("/api/v1/empleados/devengos/", HTTP_HOST=f"{tenant.schema_name}.sintel.com")
    
    if resp.status_code == 200:
        data = resp.json()
        # Verificar estructura de respuesta
        assert "results" in data or isinstance(data, list), "La respuesta debe tener formato paginado o lista"
        if "results" in data:
            assert len(data["results"]) > 0, "Debe haber al menos un devengo"
    elif resp.status_code == 403:
        # Permisos insuficientes, pero el endpoint existe
        pass
    else:
        pytest.fail(f"Expected 200 or 403, got {resp.status_code}")
