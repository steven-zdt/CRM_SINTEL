"""
Mision "Clientes + Cartera" seccion 40/70 (2026-09-11): desglose de KPIs
(sin_pago_count/parcial_count/vencidas_count) y filtro `?vencidas=1` en
GET /api/v1/clientes/cartera/ (DEUDA-C04, centro de control operativo).
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django_tenants.utils import schema_context

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura


def _crear_factura_venta(empresa, cliente, numero, consecutivo, estado_pago, due_date, total="500000.00"):
    return Factura.objects.create(
        empresa=empresa, numero=numero, consecutivo=consecutivo,
        naturaleza=Factura.Naturaleza.VENTA, estado_pago=estado_pago,
        emisor_nit=empresa.nit, emisor_razon_social=empresa.razon_social,
        receptor_nit=cliente.numero_documento, receptor_razon_social=cliente.razon_social,
        cliente_uuid=cliente.uuid,
        fecha_emision="2026-01-01T00:00:00Z", payment_due_date=due_date,
        subtotal=Decimal(total), total=Decimal(total),
    )


@pytest.mark.django_db
def test_kpis_desglosa_sin_pago_parcial_y_vencidas(client, admin_user, tenant):
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    hoy = date.today()
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        cliente = Cliente.objects.create(
            empresa=empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900777888", razon_social="Cliente KPIs",
            regimen_tributario="ORDINARIO", activo=True,
        )
        # Sin pago, no vencida
        _crear_factura_venta(empresa, cliente, "FE-K-1", 1, Factura.EstadoPago.NO_PAGADA, hoy + timedelta(days=10))
        # Sin pago, VENCIDA
        _crear_factura_venta(empresa, cliente, "FE-K-2", 2, Factura.EstadoPago.NO_PAGADA, hoy - timedelta(days=5))
        # Pago parcial, no vencida
        _crear_factura_venta(empresa, cliente, "FE-K-3", 3, Factura.EstadoPago.PAGO_PARCIAL, hoy + timedelta(days=3))
        # Pagada (nunca cuenta como vencida aunque su fecha ya paso)
        _crear_factura_venta(empresa, cliente, "FE-K-4", 4, Factura.EstadoPago.PAGADA, hoy - timedelta(days=30))

    resp = client.get("/api/v1/clientes/cartera/kpis/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sin_pago_count"] == 2
    assert data["parcial_count"] == 1
    assert data["vencidas_count"] == 1
    assert data["total_count"] == 4


@pytest.mark.django_db
def test_filtro_vencidas_solo_retorna_pendientes_vencidas(client, admin_user, tenant):
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    hoy = date.today()
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        cliente = Cliente.objects.create(
            empresa=empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900777889", razon_social="Cliente Vencidas",
            regimen_tributario="ORDINARIO", activo=True,
        )
        _crear_factura_venta(empresa, cliente, "FE-V-1", 1, Factura.EstadoPago.NO_PAGADA, hoy - timedelta(days=1))
        _crear_factura_venta(empresa, cliente, "FE-V-2", 2, Factura.EstadoPago.NO_PAGADA, hoy + timedelta(days=1))
        _crear_factura_venta(empresa, cliente, "FE-V-3", 3, Factura.EstadoPago.PAGADA, hoy - timedelta(days=10))

    resp = client.get(
        "/api/v1/clientes/cartera/?vencidas=1", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )
    assert resp.status_code == 200
    rows = resp.json()["results"]
    assert len(rows) == 1
    assert rows[0]["numero_factura"] == "FE-V-1"
