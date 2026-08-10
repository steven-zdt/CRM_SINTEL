"""
F22: mapeo MovimientoInventario -> TransaccionEconomica (logica pura, sin DB).

No hereda SintelTenantTestCase deliberadamente: _mapear_a_dto() no toca la
base de datos salvo para ENTRADA_COMPRA con documento_origen_id poblado
(resolucion de proveedor, cubierta aparte en
test_f22_extractor_inventario_integration.py) - estos tests usan instancias
de modelo sin guardar para verificar la matriz de conceptos/lados/montos
rapido, sin pagar el costo de crear un schema de tenant completo.
"""
from datetime import date, datetime
from decimal import Decimal

from django.test import SimpleTestCase

from apps.tenant.contabilidad.integracion.dtos import TipoTransaccion
from apps.tenant.contabilidad.integracion.extractores.inventario import ExtractorInventario
from apps.tenant.inventario.models import MovimientoInventario, Producto


def _movimiento(tipo, cantidad='10', costo_unitario='5.00', documento_origen_id=None,
                 documento_origen_modelo=None, cliente_referencia=None, origen_referencia=None):
    producto = Producto(id=1, empresa_id=1, codigo='PROD-1', nombre='Producto Uno')
    return MovimientoInventario(
        id=99,
        empresa_id=1,
        producto=producto,
        tipo=tipo,
        cantidad=Decimal(cantidad),
        costo_unitario=Decimal(costo_unitario),
        created_at=datetime(2026, 6, 15, 10, 0, 0),
        documento_origen_id=documento_origen_id,
        documento_origen_modelo=documento_origen_modelo,
        documento_origen_app='compras' if documento_origen_modelo else None,
        origen_referencia=origen_referencia,
        cliente_referencia=cliente_referencia,
    )


class ExtractorInventarioMappingTests(SimpleTestCase):
    """SimpleTestCase: prohibe acceso a DB salvo con allow_database_queries -
    garantiza que estos tests realmente no dependen de un schema de tenant."""

    def setUp(self):
        self.extractor = ExtractorInventario(empresa_id=1)

    def test_entrada_compra_lineas_inventario_debe_pasivo_haber(self):
        mov = _movimiento(MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA, cantidad='10', costo_unitario='5.00')
        dto = self.extractor._mapear_a_dto(mov)

        self.assertEqual(dto.tipo, TipoTransaccion.COMPRA_INVENTARIO)
        self.assertEqual(dto.fecha, date(2026, 6, 15))
        self.assertEqual(len(dto.lineas), 2)
        self.assertEqual(dto.lineas[0].concepto, 'INVENTARIO_PRODUCTO')
        self.assertEqual(dto.lineas[0].lado, 'DEBE')
        self.assertEqual(dto.lineas[0].monto, Decimal('50.00'))
        self.assertEqual(dto.lineas[1].concepto, 'PASIVO_COMPRA_INVENTARIO')
        self.assertEqual(dto.lineas[1].lado, 'HABER')
        self.assertEqual(dto.lineas[1].monto, Decimal('50.00'))
        self.assertEqual(dto.documento_origen.app_label, 'inventario')
        self.assertEqual(dto.documento_origen.modelo, 'MovimientoInventario')
        self.assertEqual(dto.documento_origen.id, 99)
        self.assertEqual(dto.documento_origen.numero, 'MOV-99')

    def test_salida_venta_lineas_costo_venta_debe_inventario_haber(self):
        mov = _movimiento(MovimientoInventario.TipoMovimiento.SALIDA_VENTA, cantidad='4', costo_unitario='25.00')
        dto = self.extractor._mapear_a_dto(mov)

        self.assertEqual(dto.tipo, TipoTransaccion.SALIDA_INVENTARIO_VENTA)
        self.assertEqual(dto.lineas[0].concepto, 'COSTO_VENTA_PRODUCTO')
        self.assertEqual(dto.lineas[0].lado, 'DEBE')
        self.assertEqual(dto.lineas[1].concepto, 'INVENTARIO_PRODUCTO')
        self.assertEqual(dto.lineas[1].lado, 'HABER')
        for linea in dto.lineas:
            self.assertEqual(linea.monto, Decimal('100.00'))

    def test_entrada_ajuste_lineas_inventario_debe_ingreso_ajuste_haber(self):
        mov = _movimiento(MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, cantidad='2', costo_unitario='10.00')
        dto = self.extractor._mapear_a_dto(mov)

        self.assertEqual(dto.tipo, TipoTransaccion.AJUSTE_INVENTARIO)
        self.assertEqual(dto.lineas[0].concepto, 'INVENTARIO_PRODUCTO')
        self.assertEqual(dto.lineas[0].lado, 'DEBE')
        self.assertEqual(dto.lineas[1].concepto, 'INGRESO_AJUSTE_INVENTARIO')
        self.assertEqual(dto.lineas[1].lado, 'HABER')

    def test_entrada_devolucion_lineas_inventario_debe_costo_venta_devolucion_haber(self):
        mov = _movimiento(MovimientoInventario.TipoMovimiento.ENTRADA_DEVOLUCION, cantidad='1', costo_unitario='30.00')
        dto = self.extractor._mapear_a_dto(mov)

        self.assertEqual(dto.tipo, TipoTransaccion.AJUSTE_INVENTARIO)
        self.assertEqual(dto.lineas[0].concepto, 'INVENTARIO_PRODUCTO')
        self.assertEqual(dto.lineas[0].lado, 'DEBE')
        self.assertEqual(dto.lineas[1].concepto, 'COSTO_VENTA_DEVOLUCION')
        self.assertEqual(dto.lineas[1].lado, 'HABER')

    def test_salida_baja_lineas_gasto_deterioro_debe_inventario_haber(self):
        mov = _movimiento(MovimientoInventario.TipoMovimiento.SALIDA_BAJA, cantidad='3', costo_unitario='8.00')
        dto = self.extractor._mapear_a_dto(mov)

        self.assertEqual(dto.tipo, TipoTransaccion.BAJA_INVENTARIO)
        self.assertEqual(dto.lineas[0].concepto, 'GASTO_DETERIORO_INVENTARIO')
        self.assertEqual(dto.lineas[1].concepto, 'INVENTARIO_PRODUCTO')

    def test_salida_consumo_usa_concepto_distinto_de_salida_baja_mismo_tipo_transaccion(self):
        mov = _movimiento(MovimientoInventario.TipoMovimiento.SALIDA_CONSUMO, cantidad='1', costo_unitario='8.00')
        dto = self.extractor._mapear_a_dto(mov)

        self.assertEqual(dto.tipo, TipoTransaccion.BAJA_INVENTARIO)
        self.assertEqual(dto.lineas[0].concepto, 'GASTO_CONSUMO_INTERNO')

    def test_tercero_generico_cuando_no_hay_proveedor_resoluble(self):
        mov = _movimiento(
            MovimientoInventario.TipoMovimiento.SALIDA_VENTA, cliente_referencia='Cliente Mostrador',
        )
        dto = self.extractor._mapear_a_dto(mov)
        self.assertIn('Cliente Mostrador', dto.tercero.razon_social)
        self.assertEqual(dto.tercero.nit, '')

    def test_traslado_salida_no_esta_en_tipos_contabilizables(self):
        from apps.tenant.contabilidad.integracion.extractores.inventario import (
            _TIPOS_CONTABILIZABLES,
        )
        self.assertNotIn(MovimientoInventario.TipoMovimiento.TRASLADO_SALIDA, _TIPOS_CONTABILIZABLES)
        self.assertNotIn(MovimientoInventario.TipoMovimiento.TRASLADO_ENTRADA, _TIPOS_CONTABILIZABLES)

    def test_tipos_de_activo_fijo_no_estan_en_tipos_contabilizables(self):
        from apps.tenant.contabilidad.integracion.extractores.inventario import (
            _TIPOS_CONTABILIZABLES,
        )
        for tipo in (
            MovimientoInventario.TipoMovimiento.ASIGNACION_RESPONSABLE,
            MovimientoInventario.TipoMovimiento.TRASLADO_MANTENIMIENTO,
            MovimientoInventario.TipoMovimiento.RETORNO_MANTENIMIENTO,
            MovimientoInventario.TipoMovimiento.SALIDA_BAJA_ACTIVO,
        ):
            self.assertNotIn(tipo, _TIPOS_CONTABILIZABLES)
