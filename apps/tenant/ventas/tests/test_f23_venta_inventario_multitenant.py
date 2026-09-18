"""
F23.18: aislamiento multi-tenant real de la salida de inventario por venta
(2 schemas, fixtures tenant1/tenant2 -- mismo patron ya establecido en F21/F22
y en apps/tenant/ventas/tests/test_multitenant_isolation.py). Empresa es
singleton por schema, "Empresa A/B" se modela como 2 tenants reales.

VENTAS-COMPRAS-FACTURAS-01 (2026-09-09): `procesar_y_facturar_venta()`
rechaza por defecto (Fase 8). Este test mockea el flag a True -- prueba el
aislamiento de datos del pipeline interno, no el bloqueo de produccion.
"""
from decimal import Decimal
from unittest import mock

import pytest
from django_tenants.utils import schema_context

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import MovimientoInventario, Producto
from apps.tenant.inventario.services.business_service import KardexService
from apps.tenant.ventas.services.business_service import VentaBusinessService


def _preparar_tenant(empresa, sufijo, stock):
    cliente = Cliente.objects.create(
        empresa=empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
        numero_documento=f"F23-MT-{sufijo}", razon_social=f"Cliente MT F23 {sufijo}",
        regimen_tributario="ORDINARIO",
    )
    producto = Producto.objects.create(
        empresa=empresa, codigo=f"PROD-MT-F23-{sufijo}", nombre=f"Producto MT F23 {sufijo}",
        stock_actual=Decimal("0"), costo_promedio=Decimal("10.00"),
    )
    KardexService.registrar_movimiento(
        empresa_id=empresa.id, producto_id=producto.id,
        tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
        cantidad=Decimal(stock), costo_unitario=Decimal("10.00"),
    )
    return cliente, producto


@pytest.mark.django_db
def test_venta_de_un_tenant_no_afecta_stock_ni_movimientos_de_otro_tenant(tenant1, tenant2):
    with schema_context(tenant1.schema_name):
        emp1 = Empresa.objects.first()
        cliente1, producto1 = _preparar_tenant(emp1, "T1", "50")

        payload1 = {
            "cliente": str(cliente1.uuid), "fecha_emision": "2026-06-05",
            "items": [{
                "descripcion": "Venta T1", "cantidad": "10", "precio_unitario": "20.00",
                "porcentaje_iva": "19", "producto_id": str(producto1.uuid),
            }],
        }
        with mock.patch(
            "apps.tenant.ventas.services.business_service.EMISION_FISCAL_VENTA_AUTORIZADA", True,
        ):
            ok, venta1, code = VentaBusinessService.procesar_y_facturar_venta(
                empresa=emp1, payload=payload1, sede_id=None,
            )
        assert ok, venta1
        producto1.refresh_from_db()
        assert producto1.stock_actual == Decimal("40.000")
        # _preparar_tenant() ya genero 1 ENTRADA_AJUSTE (stock inicial) antes
        # de facturar -- filtrar por SALIDA_VENTA para el movimiento real de
        # esta venta.
        assert MovimientoInventario.objects.filter(
            empresa=emp1, tipo=MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
        ).count() == 1

    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        _cliente2, producto2 = _preparar_tenant(emp2, "T2", "99")

        # El producto/stock de tenant2 no debe existir ni haberse tocado por la venta de tenant1
        # (schemas fisicamente separados -- ni siquiera comparten filas).
        assert Producto.objects.filter(codigo="PROD-MT-F23-T1").count() == 0
        producto2.refresh_from_db()
        assert producto2.stock_actual == Decimal("99.000")
        # _preparar_tenant() ya genero su propio ENTRADA_AJUSTE (stock inicial)
        # para tenant2 -- lo que se verifica es que NO haya ningun SALIDA_VENTA
        # (la venta de tenant1 nunca debio tocar el schema de tenant2).
        assert MovimientoInventario.objects.filter(empresa=emp2).count() == 1
        assert MovimientoInventario.objects.filter(
            empresa=emp2, tipo=MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
        ).count() == 0
