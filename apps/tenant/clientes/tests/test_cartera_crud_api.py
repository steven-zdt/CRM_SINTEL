import pytest
from django_tenants.utils import schema_context
from decimal import Decimal

from apps.public.tenants.models import TenantMembership
from apps.tenant.clientes.models import Cliente, Cartera
from apps.tenant.clientes.services.business_service import CarteraBusinessService
from apps.tenant.clientes.services.selectors import CarteraSelector
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura

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

    Hallazgo real (v3.8.0, Pull Model AGENTS.md §18, ver
    apps/tenant/clientes/.agent/AUDITORIA_FLUJO_CLIENTES.md): list() y
    kpis() de CarteraViewSet leen de Factura.naturaleza='VENTA' (fuente
    de verdad), NO del modelo Cartera -- este ultimo solo respalda
    create()/registrar-abono()/destroy(). El test original creaba solo
    un Cartera y esperaba verlo en list()/kpis(), lo cual quedo
    desactualizado tras la migracion al Pull Model.
    """
    # force_login debe escribir la sesion en el esquema del tenant: sessions
    # esta en TENANT_APPS (aislado por esquema) y la request real solo la lee
    # despues de que TenantMainMiddleware cambia de esquema (ver settings.py).
    with schema_context(tenant.schema_name):
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

        # Fuente de verdad de list()/kpis() (Pull Model): Factura.naturaleza=VENTA.
        factura = Factura.objects.create(
            empresa=empresa,
            numero="FE-456",
            consecutivo=456,
            naturaleza=Factura.Naturaleza.VENTA,
            estado_pago=Factura.EstadoPago.NO_PAGADA,
            emisor_nit=empresa.nit,
            emisor_razon_social=empresa.razon_social,
            receptor_nit=cliente.numero_documento,
            receptor_razon_social=cliente.razon_social,
            cliente_uuid=cliente.uuid,
            fecha_emision="2026-06-01T00:00:00Z",
            payment_due_date="2026-07-01",
            subtotal=Decimal("500.00"),
            total=Decimal("500.00"),
        )

        # Fuente de verdad de create()/registrar-abono()/destroy(): Cartera.
        cartera = Cartera.objects.create(
            empresa=empresa,
            cliente=cliente,
            numero_factura="FE-456",
            factura_uuid=str(factura.uuid),
            fecha_emision="2026-06-01",
            fecha_vencimiento="2026-07-01",
            valor_total=Decimal("500.00"),
            valor_pagado=Decimal("0.00"),
        )

    # 1. Test GET list (lee de Factura.VENTA, no de Cartera)
    resp = client.get("/api/v1/clientes/cartera/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["numero_factura"] == "FE-456"

    # 2. Test GET kpis (lee de Factura.VENTA, no de Cartera)
    resp = client.get("/api/v1/clientes/cartera/kpis/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")
    assert resp.status_code == 200
    kpis = resp.json()
    assert Decimal(kpis["pendiente_monto"]) == Decimal("500.00")
    assert kpis["pendiente_count"] == 1

    # 3. Test POST registrar-abono (opera sobre Cartera directamente)
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
