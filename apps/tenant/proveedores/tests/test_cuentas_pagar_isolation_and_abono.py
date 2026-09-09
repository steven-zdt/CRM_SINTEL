"""PROVEEDORES-01: cobertura de CuentasPagar que faltaba (ya senalada como
NP-PROV-001 en una auditoria previa, `.agent/AUDITORIA_CODIGO_COMPLETA.md`,
y aun no cerrada): aislamiento multi-tenant real, y las reglas de negocio de
`CuentasPagarBusinessService.registrar_abono` (monto > saldo, acumulacion,
transicion de estado SIN_PAGO -> PARCIAL -> PAGADA).
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from django_tenants.utils import schema_context
from rest_framework.exceptions import ValidationError

from apps.tenant.empresa.models import Empresa
from apps.tenant.proveedores.models import CuentasPagar, Proveedor
from apps.tenant.proveedores.services.business_service import CuentasPagarBusinessService

pytestmark = pytest.mark.django_db


def _empresa(schema):
    with schema_context(schema):
        return Empresa.objects.only("id").first()


def _crear_proveedor(empresa, numero_documento="800900900"):
    return Proveedor.objects.create(
        empresa=empresa, razon_social="Proveedor CxP", numero_documento=numero_documento, tipo_documento="NIT",
    )


def _crear_cuenta(empresa, proveedor, numero_factura, valor_total="1000.00"):
    hoy = timezone.now().date()
    return CuentasPagar.objects.create(
        empresa=empresa, proveedor=proveedor, numero_factura=numero_factura,
        valor_total=Decimal(valor_total),
        fecha_emision=hoy, fecha_vencimiento=hoy + timedelta(days=30),
    )


# --------------------------------------------------------------------------- #
# Aislamiento multi-tenant (gap NP-PROV-001)
# --------------------------------------------------------------------------- #

def test_cuentas_pagar_no_cruza_tenants(tenant, tenant_b):
    with schema_context(tenant.schema_name):
        empresa_a = _empresa(tenant.schema_name)
        proveedor_a = _crear_proveedor(empresa_a)
        cuenta_a = _crear_cuenta(empresa_a, proveedor_a, "FA-001")

    with schema_context(tenant_b.schema_name):
        # El schema de B no ve NADA de las CxP de A (aislamiento real de PostgreSQL).
        assert CuentasPagar.objects.count() == 0
        assert not CuentasPagar.objects.filter(numero_factura="FA-001").exists()

    with schema_context(tenant.schema_name):
        # sigue existiendo en su propio tenant
        assert CuentasPagar.objects.filter(uuid=cuenta_a.uuid).exists()


def test_registrar_abono_no_encuentra_cuenta_de_otro_tenant(tenant, tenant_b):
    """CuentasPagarBusinessService.registrar_abono filtra por empresa_id --
    el UUID de una cuenta de tenant A no debe ser abonable desde tenant B
    aunque alguien conociera el UUID (empresa_id siempre viene del contexto
    real del request/servicio, nunca del cliente)."""
    with schema_context(tenant.schema_name):
        empresa_a = _empresa(tenant.schema_name)
        proveedor_a = _crear_proveedor(empresa_a)
        cuenta_a = _crear_cuenta(empresa_a, proveedor_a, "FA-002")
        cuenta_a_uuid = str(cuenta_a.uuid)

    with schema_context(tenant_b.schema_name):
        empresa_b = _empresa(tenant_b.schema_name)
        with pytest.raises(ValidationError):
            CuentasPagarBusinessService.registrar_abono(
                cuenta_pagar_uuid=cuenta_a_uuid, monto="100.00",
                observaciones="", empresa_id=empresa_b.id,
            )


# --------------------------------------------------------------------------- #
# Reglas de negocio de registrar_abono
# --------------------------------------------------------------------------- #

def test_registrar_abono_actualiza_saldo_y_estado_parcial(tenant):
    with schema_context(tenant.schema_name):
        empresa = _empresa(tenant.schema_name)
        proveedor = _crear_proveedor(empresa)
        cuenta = _crear_cuenta(empresa, proveedor, "FA-010", valor_total="1000.00")
        assert cuenta.estado_pago == "SIN_PAGO"

        actualizada = CuentasPagarBusinessService.registrar_abono(
            cuenta_pagar_uuid=str(cuenta.uuid), monto="400.00",
            observaciones="primer abono", empresa_id=empresa.id,
        )
        assert actualizada.valor_pagado == Decimal("400.00")
        assert actualizada.saldo == Decimal("600.00")
        assert actualizada.estado_pago == "PARCIAL"
        assert "primer abono" in actualizada.observaciones


def test_registrar_abono_acumula_y_marca_pagada_al_completar(tenant):
    with schema_context(tenant.schema_name):
        empresa = _empresa(tenant.schema_name)
        proveedor = _crear_proveedor(empresa)
        cuenta = _crear_cuenta(empresa, proveedor, "FA-011", valor_total="1000.00")

        CuentasPagarBusinessService.registrar_abono(
            cuenta_pagar_uuid=str(cuenta.uuid), monto="400.00", observaciones="", empresa_id=empresa.id,
        )
        final = CuentasPagarBusinessService.registrar_abono(
            cuenta_pagar_uuid=str(cuenta.uuid), monto="600.00", observaciones="", empresa_id=empresa.id,
        )
        assert final.valor_pagado == Decimal("1000.00")
        assert final.saldo == Decimal("0.00")
        assert final.estado_pago == "PAGADA"


def test_registrar_abono_rechaza_monto_mayor_al_saldo(tenant):
    with schema_context(tenant.schema_name):
        empresa = _empresa(tenant.schema_name)
        proveedor = _crear_proveedor(empresa)
        cuenta = _crear_cuenta(empresa, proveedor, "FA-012", valor_total="1000.00")

        with pytest.raises(ValidationError):
            CuentasPagarBusinessService.registrar_abono(
                cuenta_pagar_uuid=str(cuenta.uuid), monto="1000.01", observaciones="", empresa_id=empresa.id,
            )
        cuenta.refresh_from_db()
        assert cuenta.valor_pagado == Decimal("0.00")
        assert cuenta.estado_pago == "SIN_PAGO"


def test_registrar_abono_rechaza_monto_mayor_al_saldo_restante_tras_abono_previo(tenant):
    with schema_context(tenant.schema_name):
        empresa = _empresa(tenant.schema_name)
        proveedor = _crear_proveedor(empresa)
        cuenta = _crear_cuenta(empresa, proveedor, "FA-013", valor_total="1000.00")

        CuentasPagarBusinessService.registrar_abono(
            cuenta_pagar_uuid=str(cuenta.uuid), monto="700.00", observaciones="", empresa_id=empresa.id,
        )
        # saldo restante = 300.00 -- un abono de 300.01 debe rechazarse
        with pytest.raises(ValidationError):
            CuentasPagarBusinessService.registrar_abono(
                cuenta_pagar_uuid=str(cuenta.uuid), monto="300.01", observaciones="", empresa_id=empresa.id,
            )


def test_registrar_abono_rechaza_monto_cero_o_negativo(tenant):
    with schema_context(tenant.schema_name):
        empresa = _empresa(tenant.schema_name)
        proveedor = _crear_proveedor(empresa)
        cuenta = _crear_cuenta(empresa, proveedor, "FA-014", valor_total="1000.00")

        with pytest.raises(ValidationError):
            CuentasPagarBusinessService.registrar_abono(
                cuenta_pagar_uuid=str(cuenta.uuid), monto="0.00", observaciones="", empresa_id=empresa.id,
            )
        with pytest.raises(ValidationError):
            CuentasPagarBusinessService.registrar_abono(
                cuenta_pagar_uuid=str(cuenta.uuid), monto="-50.00", observaciones="", empresa_id=empresa.id,
            )


def test_registrar_abono_cuenta_inexistente_falla(tenant):
    with schema_context(tenant.schema_name):
        empresa = _empresa(tenant.schema_name)
        import uuid as uuid_lib
        with pytest.raises(ValidationError):
            CuentasPagarBusinessService.registrar_abono(
                cuenta_pagar_uuid=str(uuid_lib.uuid4()), monto="10.00", observaciones="", empresa_id=empresa.id,
            )
