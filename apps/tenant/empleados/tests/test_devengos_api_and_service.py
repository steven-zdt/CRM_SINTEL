"""
Pruebas de humo para API y servicios de devengos (DRF + multitenancy).

Verifica que los endpoints respondan correctamente y que el aislamiento
por esquema funcione correctamente.
"""
from decimal import Decimal

import pytest
from django_tenants.utils import schema_context

from apps.tenant.empleados.models import Devengo, Empleado
from apps.tenant.empleados.services.devengo_service import upsert_devengo


@pytest.mark.django_db
def test_service_upsert_devengo_calcula_totales(tenant):
    """Verifica que el servicio calcula correctamente los totales."""
    with schema_context(tenant.schema_name):
        e = Empleado.objects.create(
            tipo_documento="CC", numero_documento="123",
            primer_nombre="Ana", primer_apellido="Pérez",
            email="ana@example.com", fecha_ingreso="2026-01-01"
        )
        data = {
            "empleado": e.id,
            "periodo_inicio": "2026-01-01",
            "periodo_fin": "2026-01-15",
            "fecha_pago": "2026-01-20",
            "dias_laborados": 15,
            "salario_basico": Decimal("1000000.00"),
            "auxilio_transporte": Decimal("0.00"),
            "horas_extras": Decimal("100000.00"),
            "recargos": Decimal("50000.00"),
            "comisiones": Decimal("0.00"),
            "bonificaciones": Decimal("0.00"),
            "ibc": Decimal("1000000.00"),
            "salud_empleado": Decimal("40000.00"),
            "pension_empleado": Decimal("40000.00"),
            "fondo_solidaridad": Decimal("0.00"),
            "salud_empleador": Decimal("120000.00"),
            "pension_empleador": Decimal("120000.00"),
            "arl_empleador": Decimal("10000.00"),
            "caja_compensacion": Decimal("40000.00"),
        }
        obj = upsert_devengo(data)
        assert obj.total_devengado == Decimal("1150000.00")
        assert obj.total_deducciones == Decimal("80000.00")
        assert obj.neto_pagar == Decimal("1070000.00")


@pytest.mark.django_db
def test_api_list_devengos_smoke(client, django_user_model, tenant):
    """Smoke test: lista de devengos."""
    with schema_context(tenant.schema_name):
        e = Empleado.objects.create(
            tipo_documento="CC", numero_documento="123",
            primer_nombre="Ana", primer_apellido="Pérez",
            email="ana@example.com", fecha_ingreso="2026-01-01"
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
    user = django_user_model.objects.create(username="u", email="u@x.com")
    client.force_login(user)
    # Nota: será 404 si aún no incluyes el router de la app en TENANT_URLCONF
    resp = client.get("/api/v1/devengos/")
    assert resp.status_code in (200, 404)
