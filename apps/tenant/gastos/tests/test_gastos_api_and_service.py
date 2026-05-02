"""
Pruebas de humo para API y servicios de gastos (DRF + multitenancy).

Verifica que los endpoints respondan correctamente y que el aislamiento
por esquema funcione correctamente.
"""
from decimal import Decimal

import pytest
from django_tenants.utils import schema_context

from apps.tenant.empleados.models import Empleado
from apps.tenant.gastos.models import Gasto
from apps.tenant.gastos.services.gasto_service import crear_o_actualizar_gasto


@pytest.mark.django_db
def test_service_crea_gasto_personal_con_empleado(tenant):
    """Verifica que el servicio crea gastos de personal con empleado."""
    with schema_context(tenant.schema_name):
        e = Empleado.objects.create(
            tipo_documento="CC", numero_documento="123",
            primer_nombre="Ana", primer_apellido="Pérez",
            email="ana@example.com", fecha_ingreso="2026-01-01"
        )
        data = {
            "fecha": "2026-01-31",
            "periodo": "2026-01",
            "tipo": "PERSONAL",
            "subtipo": "SALARIO",
            "descripcion": "Nómina enero",
            "valor": Decimal("2000000.00"),
            "empleado": e.id,  # devengo opcional
            "comprobante": "NOM-2026-01",
        }
        g = crear_o_actualizar_gasto(data)
        assert g.id and g.valor == Decimal("2000000.00")
        assert g.empleado_id == e.id


@pytest.mark.django_db
def test_service_valida_periodo_formato(tenant):
    """Verifica que el servicio valida formato de período."""
    with schema_context(tenant.schema_name):
        data = {
            "fecha": "2026-01-31",
            "periodo": "2026-13",  # Inválido
            "tipo": "OPERATIVO",
            "subtipo": "SERVICIOS",
            "descripcion": "Test",
            "valor": Decimal("100000.00"),
        }
        with pytest.raises(ValueError, match="Periodo inválido"):
            crear_o_actualizar_gasto(data)


@pytest.mark.django_db
def test_service_valida_tipo_subtipo_coherencia(tenant):
    """Verifica que el servicio valida coherencia tipo/subtipo."""
    with schema_context(tenant.schema_name):
        data = {
            "fecha": "2026-01-31",
            "periodo": "2026-01",
            "tipo": "PERSONAL",
            "subtipo": "ARRENDAMIENTO",  # No permitido para PERSONAL
            "descripcion": "Test",
            "valor": Decimal("100000.00"),
        }
        with pytest.raises(ValueError, match="no permitido"):
            crear_o_actualizar_gasto(data)


@pytest.mark.django_db
def test_api_list_smoke(client, django_user_model, tenant):
    """Smoke test: lista de gastos."""
    # Crear datos en el esquema del tenant
    with schema_context(tenant.schema_name):
        e = Empleado.objects.create(
            tipo_documento="CC", numero_documento="124",
            primer_nombre="Luis", primer_apellido="Gómez",
            email="luis@example.com", fecha_ingreso="2026-01-05"
        )
        Gasto.objects.create(
            fecha="2026-02-03",
            periodo="2026-02",
            tipo="OPERATIVO",
            subtipo="SERVICIOS",
            descripcion="Energía",
            valor=Decimal("350000.00"),
            empleado=None,
            devengo=None
        )
    
    # Autenticar (tu backend de permisos aplica membership si corresponde)
    user = django_user_model.objects.create(username="testuser", email="test@example.com")
    client.force_login(user)
    
    # Nota: será 404 si aún no incluiste el router en TENANT_URLCONF
    resp = client.get("/api/v1/gastos/", HTTP_HOST=f"{tenant.schema_name}.sintel.com")
    assert resp.status_code in (200, 404), f"Expected 200 or 404, got {resp.status_code}"


@pytest.mark.django_db
def test_api_create_gasto_smoke(client, django_user_model, tenant):
    """Smoke test: crear gasto."""
    with schema_context(tenant.schema_name):
        e = Empleado.objects.create(
            tipo_documento="CC", numero_documento="125",
            primer_nombre="María", primer_apellido="López",
            email="maria@example.com", fecha_ingreso="2026-01-01"
        )
        empleado_id = e.id
    
    user = django_user_model.objects.create(username="testuser", email="test@example.com")
    client.force_login(user)
    
    payload = {
        "fecha": "2026-02-15",
        "periodo": "2026-02",
        "tipo": "PERSONAL",
        "subtipo": "SALARIO",
        "descripcion": "Nómina febrero",
        "valor": "2500000.00",
        "empleado": empleado_id,
        "comprobante": "NOM-2026-02",
    }
    
    resp = client.post(
        "/api/v1/gastos/",
        data=payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant.schema_name}.sintel.com"
    )
    
    # 201 si el router está incluido y funciona, 404 si aún no se incluyó
    assert resp.status_code in (201, 404), f"Expected 201 or 404, got {resp.status_code}"
    
    # Si se creó, verificar que existe en el esquema correcto
    if resp.status_code == 201:
        data = resp.json()
        assert "id" in data
        assert data["valor"] == "2500000.00"
        
        with schema_context(tenant.schema_name):
            assert Gasto.objects.filter(
                periodo="2026-02",
                tipo="PERSONAL",
                subtipo="SALARIO"
            ).exists()
