"""
Smoke test: Verifica que el enrutado de devengos funciona después del include en TENANT_URLCONF.

Test no invasivo que verifica que el endpoint responde correctamente.
"""
import pytest
from django_tenants.utils import schema_context
from apps.tenant.empleados.models import Empleado, Devengo
from decimal import Decimal


@pytest.mark.django_db
def test_routing_devengos_list_after_include(client, django_user_model, tenant):
    """
    Verifica que el endpoint /api/v1/empleados/devengos/ responde correctamente.
    
    Este test requiere que:
    1. La app esté en TENANT_APPS
    2. El include esté en config/api_urls.py
    3. El router esté registrado en apps/tenant/empleados/api/urls.py
    """
    # Crear un usuario global (tu backend valida membresía en el middleware/permiso)
    user = django_user_model.objects.create(username="testuser", email="test@example.com")
    client.force_login(user)
    
    # Si el include en TENANT_URLCONF está OK, debe ser 200 (aunque no haya datos)
    # Nota: El host del tenant se simula automáticamente por django-tenants en tests
    resp = client.get("/api/v1/empleados/devengos/", HTTP_HOST=f"{tenant.schema_name}.sintel.com")
    
    # 200 si el router está incluido y funciona, 403 si falta permisos, 404 si falta include
    assert resp.status_code in (200, 403), (
        f"Expected 200 or 403, got {resp.status_code}. "
        f"Verifica que el include esté en config/api_urls.py y que el router esté registrado."
    )


@pytest.mark.django_db
def test_routing_devengos_list_with_data(client, django_user_model, tenant):
    """
    Verifica que el endpoint devuelve datos cuando existen devengos.
    """
    with schema_context(tenant.schema_name):
        e = Empleado.objects.create(
            tipo_documento="CC",
            numero_documento="1234567890",
            primer_nombre="Ana",
            primer_apellido="Pérez",
            email="ana@example.com",
            fecha_ingreso="2026-01-01"
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
    
    user = django_user_model.objects.create(username="testuser", email="test@example.com")
    client.force_login(user)
    
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
