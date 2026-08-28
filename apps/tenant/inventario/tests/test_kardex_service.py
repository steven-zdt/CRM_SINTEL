"""
Tests directos de KardexService (motor de stock, SSoT del modulo Inventario).

Gap real confirmado en FASE 49/50 de la mision de modernizacion (2026-08-27,
docs/inventario/INVENTARIO_BASELINE.md): existian 24 tests en el modulo pero
ninguno ejercitaba KardexService.registrar_movimiento()/actualizar_movimiento()/
eliminar_movimiento()/registrar_movimiento_activo() directamente -- el motor
de stock del modulo no tenia cobertura propia, solo se ejercitaba
indirectamente via F21 (traslados) y algunos tests de otras apps (ventas,
compras, facturas) que lo consumen.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import ActivoFijo, MovimientoInventario, Producto
from apps.tenant.inventario.services.business_service import KardexService
from tests.tenant.base_test import SintelTenantTestCase


class KardexServiceStockCalculationTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Kardex Test", nit="900000001", direccion="Calle 1",
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa, codigo="KDX-001", nombre="Producto Kardex",
        )

    def test_registrar_entrada_incrementa_stock(self):
        KardexService.registrar_movimiento(
            empresa_id=self.empresa.id,
            producto_id=self.producto.id,
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
            cantidad=Decimal("10"),
        )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, Decimal("10.000"))

    def test_registrar_salida_decrementa_stock(self):
        KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=self.producto.id,
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA, cantidad=Decimal("10"),
        )
        KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=self.producto.id,
            tipo=MovimientoInventario.TipoMovimiento.SALIDA_VENTA, cantidad=Decimal("4"),
        )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, Decimal("6.000"))

    def test_salida_con_stock_insuficiente_es_rechazada(self):
        with self.assertRaises(ValidationError):
            KardexService.registrar_movimiento(
                empresa_id=self.empresa.id, producto_id=self.producto.id,
                tipo=MovimientoInventario.TipoMovimiento.SALIDA_VENTA, cantidad=Decimal("1"),
            )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, Decimal("0.000"))
        self.assertFalse(
            MovimientoInventario.objects.filter(empresa=self.empresa, producto=self.producto).exists()
        )

    def test_cantidad_cero_o_negativa_es_rechazada(self):
        with self.assertRaises(ValidationError):
            KardexService.registrar_movimiento(
                empresa_id=self.empresa.id, producto_id=self.producto.id,
                tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, cantidad=Decimal("0"),
            )
        with self.assertRaises(ValidationError):
            KardexService.registrar_movimiento(
                empresa_id=self.empresa.id, producto_id=self.producto.id,
                tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, cantidad=Decimal("-5"),
            )

    def test_tipo_invalido_es_rechazado(self):
        with self.assertRaises(ValidationError):
            KardexService.registrar_movimiento(
                empresa_id=self.empresa.id, producto_id=self.producto.id,
                tipo="TIPO_QUE_NO_EXISTE", cantidad=Decimal("1"),
            )

    def test_producto_inactivo_no_admite_movimientos(self):
        self.producto.activo = False
        self.producto.save(update_fields=["activo"])
        with self.assertRaises(ValidationError):
            KardexService.registrar_movimiento(
                empresa_id=self.empresa.id, producto_id=self.producto.id,
                tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, cantidad=Decimal("1"),
            )

    def test_producto_de_otra_empresa_es_rechazado(self):
        otra_empresa_id = self.empresa.id + 999999
        with self.assertRaises(ValidationError):
            KardexService.registrar_movimiento(
                empresa_id=otra_empresa_id, producto_id=self.producto.id,
                tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, cantidad=Decimal("1"),
            )

    def test_calcular_stock_es_entradas_menos_salidas(self):
        for tipo, cantidad in [
            (MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA, "20"),
            (MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, "5"),
            (MovimientoInventario.TipoMovimiento.SALIDA_VENTA, "8"),
            (MovimientoInventario.TipoMovimiento.SALIDA_CONSUMO, "2"),
        ]:
            KardexService.registrar_movimiento(
                empresa_id=self.empresa.id, producto_id=self.producto.id,
                tipo=tipo, cantidad=Decimal(cantidad),
            )
        # 20 + 5 - 8 - 2 = 15
        self.assertEqual(
            KardexService.calcular_stock(self.producto.id, self.empresa.id), Decimal("15")
        )


class KardexServiceMutationTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Kardex Mut Test", nit="900000002", direccion="Calle 2",
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa, codigo="KDX-002", nombre="Producto Kardex Mut",
        )
        self.movimiento = KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=self.producto.id,
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA, cantidad=Decimal("10"),
        )

    def test_actualizar_movimiento_recalcula_stock(self):
        KardexService.actualizar_movimiento(
            movimiento=self.movimiento, empresa_id=self.empresa.id, nueva_cantidad=Decimal("25"),
        )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, Decimal("25.000"))

    def test_actualizar_movimiento_cantidad_no_positiva_es_rechazada(self):
        with self.assertRaises(ValidationError):
            KardexService.actualizar_movimiento(
                movimiento=self.movimiento, empresa_id=self.empresa.id, nueva_cantidad=Decimal("0"),
            )

    def test_actualizar_movimiento_de_otra_empresa_es_rechazado(self):
        otra_empresa_id = self.empresa.id + 999999
        with self.assertRaises(ValidationError):
            KardexService.actualizar_movimiento(
                movimiento=self.movimiento, empresa_id=otra_empresa_id, nueva_cantidad=Decimal("5"),
            )
        self.producto.refresh_from_db()
        # El stock no debe haberse tocado.
        self.assertEqual(self.producto.stock_actual, Decimal("10.000"))

    def test_eliminar_movimiento_recalcula_stock(self):
        KardexService.eliminar_movimiento(movimiento=self.movimiento, empresa_id=self.empresa.id)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, Decimal("0.000"))
        self.assertFalse(MovimientoInventario.objects.filter(pk=self.movimiento.pk).exists())

    def test_eliminar_movimiento_de_otra_empresa_es_rechazado(self):
        otra_empresa_id = self.empresa.id + 999999
        with self.assertRaises(ValidationError):
            KardexService.eliminar_movimiento(movimiento=self.movimiento, empresa_id=otra_empresa_id)
        self.assertTrue(MovimientoInventario.objects.filter(pk=self.movimiento.pk).exists())


class KardexServiceActivoFijoTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Kardex Activo Test", nit="900000003", direccion="Calle 3",
        )
        self.activo = ActivoFijo.objects.create(
            empresa=self.empresa, codigo="ACT-KDX-001", nombre="Laptop Kardex Test",
        )

    def test_asignacion_responsable_no_cambia_estado(self):
        KardexService.registrar_movimiento_activo(
            empresa_id=self.empresa.id, activo_fijo_id=self.activo.id,
            tipo=MovimientoInventario.TipoMovimiento.ASIGNACION_RESPONSABLE,
        )
        self.activo.refresh_from_db()
        self.assertEqual(self.activo.estado, ActivoFijo.Estado.ACTIVO)

    def test_traslado_a_mantenimiento_cambia_estado(self):
        KardexService.registrar_movimiento_activo(
            empresa_id=self.empresa.id, activo_fijo_id=self.activo.id,
            tipo=MovimientoInventario.TipoMovimiento.TRASLADO_MANTENIMIENTO,
        )
        self.activo.refresh_from_db()
        self.assertEqual(self.activo.estado, ActivoFijo.Estado.MANTENIMIENTO)

    def test_retorno_de_mantenimiento_vuelve_a_activo(self):
        self.activo.estado = ActivoFijo.Estado.MANTENIMIENTO
        self.activo.save(update_fields=["estado"])
        KardexService.registrar_movimiento_activo(
            empresa_id=self.empresa.id, activo_fijo_id=self.activo.id,
            tipo=MovimientoInventario.TipoMovimiento.RETORNO_MANTENIMIENTO,
        )
        self.activo.refresh_from_db()
        self.assertEqual(self.activo.estado, ActivoFijo.Estado.ACTIVO)

    def test_baja_de_activo_cambia_estado_a_baja(self):
        KardexService.registrar_movimiento_activo(
            empresa_id=self.empresa.id, activo_fijo_id=self.activo.id,
            tipo=MovimientoInventario.TipoMovimiento.SALIDA_BAJA_ACTIVO,
        )
        self.activo.refresh_from_db()
        self.assertEqual(self.activo.estado, ActivoFijo.Estado.BAJA)

    def test_tipo_de_producto_es_rechazado_para_activo(self):
        with self.assertRaises(ValidationError):
            KardexService.registrar_movimiento_activo(
                empresa_id=self.empresa.id, activo_fijo_id=self.activo.id,
                tipo=MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
            )

    def test_activo_de_otra_empresa_es_rechazado(self):
        otra_empresa_id = self.empresa.id + 999999
        with self.assertRaises(ValidationError):
            KardexService.registrar_movimiento_activo(
                empresa_id=otra_empresa_id, activo_fijo_id=self.activo.id,
                tipo=MovimientoInventario.TipoMovimiento.ASIGNACION_RESPONSABLE,
            )
