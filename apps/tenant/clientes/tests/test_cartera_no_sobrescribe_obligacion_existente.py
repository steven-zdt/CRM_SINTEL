"""
Regresion (2026-09-12, hallazgo C-2): el formulario manual "Nueva
Obligacion" (POST /api/v1/clientes/cartera/) llamaba a
CarteraBusinessService.registrar_cartera() -- un get_or_create() idempotente
pensado para sincronizacion ETL (unico invocador real hoy es este mismo
endpoint, ver docs/integration/CROSS_APP_FINDINGS.md). Si se reenviaba el
mismo (cliente, numero_factura) ya existente, la rama "not created"
sobreescribia valor_pagado sin locking, sin guarda de "ya PAGADA" y sin
CarteraNota -- bypaseando por completo registrar_abono(), la unica via de
pago autorizada (ver seccion 14 del encargo: "Ningun otro dominio debe
permitir modificar valor_pagado/saldo/estado_pago").

Fix: CarteraViewSet.create() ahora rechaza con 409 si ya existe una
obligacion para (empresa, cliente, numero_factura), sin tocar la semantica
de upsert de registrar_cartera() en si (cubierta por su propio test,
test_cartera_crud_api.py, para el uso ETL futuro).

Ver docs/remediation/AUDIT_BASELINE_20260912.md hallazgo C-2.
"""
from decimal import Decimal

import pytest
from django_tenants.utils import schema_context

from apps.tenant.clientes.models import Cartera, Cliente
from apps.tenant.clientes.services.business_service import CarteraBusinessService
from apps.tenant.empresa.models import Empresa


@pytest.mark.django_db
def test_post_duplicado_no_sobrescribe_abono_ya_registrado(client, admin_user, tenant):
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        cliente = Cliente.objects.create(
            empresa=empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900444555", razon_social="Cliente C2",
            regimen_tributario="ORDINARIO", activo=True,
        )
        cartera = Cartera.objects.create(
            empresa=empresa, cliente=cliente, numero_factura="FE-C2-1",
            fecha_emision="2026-06-01", fecha_vencimiento="2026-07-01",
            valor_total=Decimal("1000000.00"),
        )
        CarteraBusinessService.registrar_abono(
            empresa_id=empresa.id, cartera_uuid=cartera.uuid, monto=Decimal("300000.00"),
        )
        cartera.refresh_from_db()
        assert cartera.valor_pagado == Decimal("300000.00")
        cliente_id = cliente.id

    host = f"{tenant.schema_name}.sintel.net.co"

    # Reenviar "Nueva Obligacion" con el mismo (cliente, numero_factura) y un
    # valor_pagado distinto -- antes del fix, esto sobrescribia el abono ya
    # registrado sin pasar por registrar_abono().
    resp = client.post(
        "/api/v1/clientes/cartera/",
        data={
            "cliente": cliente_id,
            "numero_factura": "FE-C2-1",
            "fecha_emision": "2026-06-01",
            "fecha_vencimiento": "2026-07-01",
            "valor_total": "1000000.00",
            "valor_pagado": "999999.00",
        },
        content_type="application/json",
        HTTP_HOST=host,
    )

    assert resp.status_code == 409, resp.content

    with schema_context(tenant.schema_name):
        cartera.refresh_from_db()
        assert cartera.valor_pagado == Decimal("300000.00"), (
            "valor_pagado fue sobrescrito por el POST duplicado -- el "
            "bypass de registrar_abono() sigue abierto."
        )

    # Sanity check: la via legitima de creacion (cliente/numero_factura
    # nuevos) sigue funcionando sin cambios.
    resp_nueva = client.post(
        "/api/v1/clientes/cartera/",
        data={
            "cliente": cliente_id,
            "numero_factura": "FE-C2-2",
            "fecha_emision": "2026-06-01",
            "fecha_vencimiento": "2026-07-01",
            "valor_total": "500000.00",
        },
        content_type="application/json",
        HTTP_HOST=host,
    )
    assert resp_nueva.status_code == 201, resp_nueva.content
