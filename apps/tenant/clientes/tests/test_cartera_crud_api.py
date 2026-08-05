import pytest
from django_tenants.utils import schema_context
from decimal import Decimal

from apps.public.tenants.models import TenantMembership
from apps.tenant.clientes.models import Cliente, Cartera
from apps.tenant.clientes.services.business_service import CarteraBusinessService
from apps.tenant.clientes.services.selectors import CarteraSelector
from apps.tenant.empresa.models import Empresa

@pytest.mark.django_db
def test_cartera_creation_and_abono(tenant):
    """
    Test Cartera creation, automatic balance/state calculation, and abono service logic.
    """
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        if not empresa:
            empresa = Empresa.objects.create(
                nombre="Empresa Test",
                razon_social="EMPRESA TEST S.A.S.",
                nit="901234567",
            )

        cliente = Cliente.objects.create(
            empresa=empresa,
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            numero_documento="900111222",
            razon_social="Cliente Test Cartera",
            regimen_tributario="ORDINARIO",
            activo=True,
        )

        data = {
            "cliente_id": cliente.id,
            "numero_factura": "FE-123",
            "factura_uuid": "12345678-1234-5678-1234-567812345678",
            "fecha_emision": "2026-06-01",
            "fecha_vencimiento": "2026-07-01",
            "valor_total": Decimal("1000.00"),
            "valor_pagado": Decimal("0.00"),
            "observaciones": "Test obligation",
        }

        cartera, created = CarteraBusinessService.registrar_cartera(empresa.id, data)
        assert created is True
        assert cartera.saldo == Decimal("1000.00")
        assert cartera.estado_pago == "SIN_PAGO"

        # Verify idempotency: duplicate registration updates values
        data["valor_total"] = Decimal("1200.00")
        cartera, created = CarteraBusinessService.registrar_cartera(empresa.id, data)
        assert created is False
        assert cartera.valor_total == Decimal("1200.00")
        assert cartera.saldo == Decimal("1200.00")

        # Test abono
        cartera, abono_aplicado = CarteraBusinessService.registrar_abono(
            empresa_id=empresa.id,
            cartera_uuid=cartera.uuid,
            monto=Decimal("400.00")
        )
        assert abono_aplicado == Decimal("400.00")
        assert cartera.valor_pagado == Decimal("400.00")
        assert cartera.saldo == Decimal("800.00")
        assert cartera.estado_pago == "PARCIAL"

        # Full payment
        cartera, abono_aplicado = CarteraBusinessService.registrar_abono(
            empresa_id=empresa.id,
            cartera_uuid=cartera.uuid,
            monto=Decimal("800.00")
        )
        assert abono_aplicado == Decimal("800.00")
        assert cartera.valor_pagado == Decimal("1200.00")
        assert cartera.saldo == Decimal("0.00")
        assert cartera.estado_pago == "PAGADA"


@pytest.mark.django_db
def test_cartera_api_endpoints(client, admin_user, tenant):
    """
    Test Cartera REST endpoints: list, kpis, and registrar-abono.
    """
    client.force_login(admin_user)

    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        if not empresa:
            empresa = Empresa.objects.create(
                nombre="Empresa Test",
                razon_social="EMPRESA TEST S.A.S.",
                nit="901234567",
            )

        cliente = Cliente.objects.create(
            empresa=empresa,
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            numero_documento="900111222",
            razon_social="Cliente Test Cartera",
            regimen_tributario="ORDINARIO",
            activo=True,
        )

        cartera = Cartera.objects.create(
            empresa=empresa,
            cliente=cliente,
            numero_factura="FE-456",
            factura_uuid="87654321-4321-8765-4321-876543210987",
            fecha_emision="2026-06-01",
            fecha_vencimiento="2026-07-01",
            valor_total=Decimal("500.00"),
            valor_pagado=Decimal("0.00"),
        )

    # 1. Test GET list
    resp = client.get("/api/v1/clientes/cartera/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["numero_factura"] == "FE-456"

    # 2. Test GET kpis
    resp = client.get("/api/v1/clientes/cartera/kpis/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")
    assert resp.status_code == 200
    kpis = resp.json()
    assert Decimal(kpis["pendiente_monto"]) == Decimal("500.00")
    assert kpis["pendiente_count"] == 1

    # 3. Test POST registrar-abono
    resp = client.post(
        f"/api/v1/clientes/cartera/{cartera.uuid}/registrar-abono/",
        data={"monto": "200.00"},
        content_type="application/json",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co"
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert Decimal(res_data["saldo"]) == Decimal("300.00")
    assert res_data["estado_pago"] == "PARCIAL"
