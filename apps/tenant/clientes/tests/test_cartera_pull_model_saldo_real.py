"""
Auditoria "Clientes + Cartera" (2026-09-11) — contradiccion real encontrada
y corregida: CarteraViewSet.list()/kpis() leen de Factura.naturaleza=VENTA
(Pull Model, AGENTS.md §18) e INFERIAN valor_pagado/saldo del enum
Factura.estado_pago (3 valores) en vez de leer el monto REAL de los abonos
ya registrados en `Cartera` (fuente de verdad real, ver
CarteraBusinessService.registrar_abono()).

Antes de este fix: una factura con un abono parcial de $300.000 sobre
$1.000.000 se mostraba en la pestana Cartera como "Sin Pago, saldo
$1.000.000" -- IGNORANDO el abono ya registrado. Este archivo demuestra el
escenario corregido: list()/kpis() ahora reflejan el saldo real de
Cartera cuando existe una obligacion vinculada a esa factura.
"""
from decimal import Decimal

import pytest
from django_tenants.utils import schema_context

from apps.tenant.clientes.models import Cartera, Cliente
from apps.tenant.clientes.services.business_service import CarteraBusinessService
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura


@pytest.mark.django_db
def test_list_y_kpis_reflejan_abono_parcial_real_de_cartera(client, admin_user, tenant):
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        cliente = Cliente.objects.create(
            empresa=empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900222333", razon_social="Cliente Saldo Real",
            regimen_tributario="ORDINARIO", activo=True,
        )
        factura = Factura.objects.create(
            empresa=empresa, numero="FE-SALDO-1", consecutivo=999,
            naturaleza=Factura.Naturaleza.VENTA,
            estado_pago=Factura.EstadoPago.PAGO_PARCIAL,
            emisor_nit=empresa.nit, emisor_razon_social=empresa.razon_social,
            receptor_nit=cliente.numero_documento, receptor_razon_social=cliente.razon_social,
            cliente_uuid=cliente.uuid,
            fecha_emision="2026-06-01T00:00:00Z", payment_due_date="2026-07-01",
            subtotal=Decimal("1000000.00"), total=Decimal("1000000.00"),
        )
        cartera = Cartera.objects.create(
            empresa=empresa, cliente=cliente, numero_factura="FE-SALDO-1",
            factura_uuid=str(factura.uuid),
            fecha_emision="2026-06-01", fecha_vencimiento="2026-07-01",
            valor_total=Decimal("1000000.00"),
        )
        CarteraBusinessService.registrar_abono(
            empresa_id=empresa.id, cartera_uuid=cartera.uuid, monto=Decimal("300000.00"),
        )

    resp = client.get("/api/v1/clientes/cartera/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")
    assert resp.status_code == 200
    rows = resp.json()["results"]
    assert len(rows) == 1
    row = rows[0]
    # Antes del fix: valor_pagado='0.00', saldo='1000000.00' (bug).
    assert Decimal(row["valor_pagado"]) == Decimal("300000.00")
    assert Decimal(row["saldo"]) == Decimal("700000.00")
    assert row["estado_pago"] == "PARCIAL"

    resp_kpis = client.get("/api/v1/clientes/cartera/kpis/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")
    assert resp_kpis.status_code == 200
    kpis = resp_kpis.json()
    # Antes del fix: pendiente_monto contaba el total completo (1.000.000).
    assert Decimal(kpis["pendiente_monto"]) == Decimal("700000.00")
    assert kpis["pendiente_count"] == 1


@pytest.mark.django_db
def test_list_sin_cartera_asociada_mantiene_fallback_anterior(client, admin_user, tenant):
    """Factura VENTA nunca tocada por Cartera: se mantiene el fallback
    basado en Factura.estado_pago (comportamiento previo, sin regresion)."""
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        cliente = Cliente.objects.create(
            empresa=empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900222334", razon_social="Cliente Sin Cartera",
            regimen_tributario="ORDINARIO", activo=True,
        )
        Factura.objects.create(
            empresa=empresa, numero="FE-SALDO-2", consecutivo=1000,
            naturaleza=Factura.Naturaleza.VENTA,
            estado_pago=Factura.EstadoPago.NO_PAGADA,
            emisor_nit=empresa.nit, emisor_razon_social=empresa.razon_social,
            receptor_nit=cliente.numero_documento, receptor_razon_social=cliente.razon_social,
            cliente_uuid=cliente.uuid,
            fecha_emision="2026-06-01T00:00:00Z", payment_due_date="2026-07-01",
            subtotal=Decimal("500000.00"), total=Decimal("500000.00"),
        )

    resp = client.get("/api/v1/clientes/cartera/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")
    assert resp.status_code == 200
    row = resp.json()["results"][0]
    assert Decimal(row["valor_pagado"]) == Decimal("0.00")
    assert Decimal(row["saldo"]) == Decimal("500000.00")
    assert row["estado_pago"] == "SIN_PAGO"
