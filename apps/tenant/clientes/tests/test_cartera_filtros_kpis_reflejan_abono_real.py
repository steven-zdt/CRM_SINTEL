"""
Regresion (2026-09-12, hallazgo C-1): los filtros (?estado_pago=) y los KPIs
de Cartera (pendiente_count, pagado_monto, vencidas_count) leian
Factura.estado_pago, que registrar_abono() -- la unica via de pago
autorizada -- NUNCA escribe (solo escribe Cartera.valor_pagado/saldo/
estado_pago). Una factura pagada 100% solo via abono manual (nunca tocada
por la conciliacion bancaria, que es la unica que si escribe
Factura.estado_pago) nunca aparecia bajo ?estado_pago=PAGADA, seguia
contando en pendiente_count/vencidas_count, y su monto nunca entraba a
pagado_monto.

Nota metodologica (la propia auditoria senala que el test previo,
test_cartera_pull_model_saldo_real.py, enmascaraba este bug): aqui la
Factura se crea SIN forzar estado_pago a mano -- se deja en su default real
(NO_PAGADA) y es registrar_abono() el UNICO mecanismo que cambia el estado,
igual que en produccion.

Ver docs/remediation/AUDIT_BASELINE_20260912.md hallazgo C-1.
"""
from decimal import Decimal

import pytest
from django_tenants.utils import schema_context

from apps.tenant.clientes.models import Cartera, Cliente
from apps.tenant.clientes.services.business_service import CarteraBusinessService
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura


@pytest.mark.django_db
def test_factura_pagada_solo_via_abono_manual_aparece_en_filtros_y_kpis(client, admin_user, tenant):
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        cliente = Cliente.objects.create(
            empresa=empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900333444", razon_social="Cliente Pagado Solo Cartera",
            regimen_tributario="ORDINARIO", activo=True,
        )
        # Factura.estado_pago se deja en su default real (NO_PAGADA) -- como
        # en produccion, ningun proceso lo mueve fuera de la conciliacion
        # bancaria. El pago aqui es 100% manual via Cartera.
        factura = Factura.objects.create(
            empresa=empresa, numero="FE-C1-1", consecutivo=1001,
            naturaleza=Factura.Naturaleza.VENTA,
            emisor_nit=empresa.nit, emisor_razon_social=empresa.razon_social,
            receptor_nit=cliente.numero_documento, receptor_razon_social=cliente.razon_social,
            cliente_uuid=cliente.uuid,
            fecha_emision="2026-06-01T00:00:00Z", payment_due_date="2020-07-01",
            subtotal=Decimal("1000000.00"), total=Decimal("1000000.00"),
        )
        assert factura.estado_pago == Factura.EstadoPago.NO_PAGADA

        cartera = Cartera.objects.create(
            empresa=empresa, cliente=cliente, numero_factura="FE-C1-1",
            factura_uuid=str(factura.uuid),
            fecha_emision="2026-06-01", fecha_vencimiento="2020-07-01",
            valor_total=Decimal("1000000.00"),
        )
        CarteraBusinessService.registrar_abono(
            empresa_id=empresa.id, cartera_uuid=cartera.uuid, monto=Decimal("1000000.00"),
        )
        cartera.refresh_from_db()
        assert cartera.estado_pago == "PAGADA"
        # Factura.estado_pago nunca se toco -- exactamente el escenario real.
        factura.refresh_from_db()
        assert factura.estado_pago == Factura.EstadoPago.NO_PAGADA

    host = f"{tenant.schema_name}.sintel.net.co"

    # 1) El filtro ?estado_pago=PAGADA debe incluirla.
    resp_pagada = client.get("/api/v1/clientes/cartera/?estado_pago=PAGADA", HTTP_HOST=host)
    assert resp_pagada.status_code == 200
    numeros_pagada = [r["numero_factura"] for r in resp_pagada.json()["results"]]
    assert "FE-C1-1" in numeros_pagada

    # 2) Los filtros SIN_PAGO/PARCIAL deben excluirla.
    resp_sin_pago = client.get("/api/v1/clientes/cartera/?estado_pago=SIN_PAGO", HTTP_HOST=host)
    assert "FE-C1-1" not in [r["numero_factura"] for r in resp_sin_pago.json()["results"]]

    resp_parcial = client.get("/api/v1/clientes/cartera/?estado_pago=PARCIAL", HTTP_HOST=host)
    assert "FE-C1-1" not in [r["numero_factura"] for r in resp_parcial.json()["results"]]

    # 3) ?vencidas=1 debe excluirla aunque su fecha de vencimiento ya paso
    #    (2020-07-01) -- esta pagada, no es una cuenta por cobrar vencida.
    resp_vencidas = client.get("/api/v1/clientes/cartera/?vencidas=1", HTTP_HOST=host)
    assert "FE-C1-1" not in [r["numero_factura"] for r in resp_vencidas.json()["results"]]

    # 4) KPIs: debe contar en pagado_monto, NUNCA en pendiente_count/vencidas_count.
    resp_kpis = client.get("/api/v1/clientes/cartera/kpis/", HTTP_HOST=host)
    assert resp_kpis.status_code == 200
    kpis = resp_kpis.json()
    assert Decimal(kpis["pagado_monto"]) >= Decimal("1000000.00")
    assert kpis["pendiente_count"] == 0
    assert kpis["vencidas_count"] == 0
