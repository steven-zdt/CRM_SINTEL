"""
F22: ExtractorInventario contra base de datos real (idempotencia, periodo
cerrado, reglas faltantes, traslados, tenant, E2E compra parcial y traslado).

Una sola clase con setUp compartido (mismo criterio de costo aprendido en F21:
cada TenantTestCase concreta paga su propio schema, ~3min — minimizar el
numero de clases, no el numero de metodos de test).
"""
from datetime import date
from decimal import Decimal

from django.utils import timezone

from apps.tenant.compras.models import PlantillaOrdenCompra
from apps.tenant.compras.services.business_service import RecepcionCompraBusinessService
from apps.tenant.contabilidad.integracion.extractores.inventario import ExtractorInventario
from apps.tenant.contabilidad.models import AsientoContable, PeriodoContable, ReglaContable
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.inventario.models import MovimientoInventario, Producto
from apps.tenant.inventario.services.business_service import (
    KardexService,
    TrasladoInventarioService,
)
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase

_REGLAS = [
    ("COMPRA_INVENTARIO", "INVENTARIO_PRODUCTO", "143505"),
    ("COMPRA_INVENTARIO", "PASIVO_COMPRA_INVENTARIO", "220505"),
    ("SALIDA_INVENTARIO_VENTA", "COSTO_VENTA_PRODUCTO", "613501"),
    ("SALIDA_INVENTARIO_VENTA", "INVENTARIO_PRODUCTO", "143505"),
    ("AJUSTE_INVENTARIO", "INVENTARIO_PRODUCTO", "143505"),
    ("AJUSTE_INVENTARIO", "INGRESO_AJUSTE_INVENTARIO", "425050"),
    ("AJUSTE_INVENTARIO", "COSTO_VENTA_DEVOLUCION", "613501"),
    ("BAJA_INVENTARIO", "GASTO_DETERIORO_INVENTARIO", "529901"),
    ("BAJA_INVENTARIO", "GASTO_CONSUMO_INTERNO", "519595"),
    ("BAJA_INVENTARIO", "INVENTARIO_PRODUCTO", "143505"),
]


class ExtractorInventarioTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa F22", nit="900000801", direccion="Calle F22",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede Bogota F22")
        self.perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor F22", numero_documento="F22-PROV-1", tipo_documento="NIT",
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa, nombre="Plantilla F22", prefijo="F22",
            rango_desde=1, rango_hasta=1000, consecutivo_actual=1, vigente=True,
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa, codigo="PROD-F22", nombre="Producto F22", stock_actual=Decimal("0"),
        )
        # KardexService.registrar_movimiento() estampa created_at con
        # timezone.now() real (no una fecha de prueba fija) -- el periodo debe
        # cubrir la fecha real de ejecucion, no un mes hardcodeado. Se usa el
        # año completo (no solo el mes actual) para no depender de en que
        # momento exacto del mes corre la suite completa.
        hoy = timezone.localdate()
        self.periodo = PeriodoContable.objects.create(
            empresa=self.empresa, periodo=hoy.strftime('%Y-%m'),
            fecha_inicio=date(hoy.year, 1, 1), fecha_fin=date(hoy.year, 12, 31), estado="ABIERTO",
        )
        for tipo_tx, concepto, cuenta in _REGLAS:
            ReglaContable.objects.create(
                empresa=self.empresa, tipo_transaccion=tipo_tx, concepto=concepto,
                cuenta_codigo=cuenta, activo=True,
            )

    def _crear_movimiento(self, tipo, cantidad, costo_unitario, sede_id=None):
        return KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=self.producto.id, tipo=tipo,
            cantidad=Decimal(cantidad), costo_unitario=Decimal(costo_unitario), sede_id=sede_id,
        )

    def _extractor(self):
        return ExtractorInventario(empresa_id=self.empresa.id)

    # ---- Entrada por compra (via cadena real Compras -> Recepcion) ----

    def _crear_y_confirmar_orden_recepcion(self, consecutivo, cantidad_ordenada, cantidad_recibida):
        from apps.tenant.compras.models import ItemOrdenCompra, OrdenCompra

        orden = OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede, proveedor=self.proveedor, plantilla=self.plantilla,
            fecha="2026-06-01", consecutivo=consecutivo, numero_documento=f"F22-OC-{consecutivo}",
            estado="APROBADA",
        )
        item = ItemOrdenCompra.objects.create(
            empresa=self.empresa, orden_compra=orden, descripcion="Item F22",
            item_inventario_uuid=self.producto.uuid,
            cantidad=Decimal(cantidad_ordenada), valor_unitario=Decimal("10.00"),
            subtotal=Decimal(cantidad_ordenada) * Decimal("10.00"), total=Decimal(cantidad_ordenada) * Decimal("10.00"),
        )
        data = {"orden_compra": orden, "fecha": "2026-06-05"}
        items_data = [{"item_orden_compra": item, "cantidad_recibida": Decimal(cantidad_recibida)}]
        ok, recepcion, _ = RecepcionCompraBusinessService.crear_recepcion(
            data, items_data, self.empresa, self.sede, self.perfil,
        )
        assert ok, recepcion
        ok, recepcion, _ = RecepcionCompraBusinessService.confirmar_recepcion(recepcion.uuid, self.empresa.id)
        assert ok, recepcion
        return orden, recepcion

    def test_entrada_compra_genera_asiento_balanceado_con_proveedor_real(self):
        self._crear_y_confirmar_orden_recepcion(consecutivo=1, cantidad_ordenada="20", cantidad_recibida="20")

        resultado = self._extractor().contabilizar_pendientes()
        self.assertEqual(resultado['contabilizados'], 1)
        self.assertEqual(resultado['omitidos'], 0)
        self.assertEqual(resultado['errores'], [])

        asiento = AsientoContable.objects.get(empresa=self.empresa, documento_origen_app='inventario')
        self.assertEqual(asiento.documento_origen_modelo, 'MovimientoInventario')
        self.assertEqual(asiento.debe_total, asiento.haber_total)
        self.assertEqual(asiento.debe_total, Decimal('200.00'))  # 20 * 10.00

        movimiento = MovimientoInventario.objects.get(empresa=self.empresa, tipo='ENTRADA_COMPRA')
        self.assertEqual(asiento.documento_origen_id, movimiento.id)

        movs_contables = list(asiento.movimientos.all())
        self.assertEqual(len(movs_contables), 2)
        codigos = {m.cuenta_codigo for m in movs_contables}
        self.assertEqual(codigos, {'143505', '220505'})
        # Tercero real resuelto via la cadena RecepcionCompraItem->recepcion->orden_compra->proveedor.
        tercero_nits = {m.tercero_nit for m in movs_contables}
        self.assertEqual(tercero_nits, {'F22-PROV-1'})

    def test_ejecutar_extractor_dos_veces_no_duplica_asiento(self):
        self._crear_y_confirmar_orden_recepcion(consecutivo=1, cantidad_ordenada="20", cantidad_recibida="20")

        r1 = self._extractor().contabilizar_pendientes()
        self.assertEqual(r1['contabilizados'], 1)

        r2 = self._extractor().contabilizar_pendientes()
        self.assertEqual(r2['contabilizados'], 0)
        self.assertEqual(r2['omitidos'], 0)  # ya no aparece en extraer_pendientes(), no hay nada que omitir
        self.assertEqual(
            AsientoContable.objects.filter(empresa=self.empresa, documento_origen_app='inventario').count(), 1,
        )

    # ---- Ajustes / bajas / consumo / devolucion ----

    def test_entrada_ajuste_genera_asiento(self):
        self._crear_movimiento(MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, "5", "12.00")
        resultado = self._extractor().contabilizar_pendientes()
        self.assertEqual(resultado['contabilizados'], 1)
        asiento = AsientoContable.objects.get(empresa=self.empresa)
        self.assertEqual(asiento.debe_total, Decimal('60.00'))

    def test_salida_baja_y_salida_consumo_usan_cuentas_de_gasto_distintas(self):
        self._crear_movimiento(MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, "10", "10.00")
        self._extractor().contabilizar_pendientes()  # deja stock disponible para las salidas

        self._crear_movimiento(MovimientoInventario.TipoMovimiento.SALIDA_BAJA, "2", "10.00")
        self._crear_movimiento(MovimientoInventario.TipoMovimiento.SALIDA_CONSUMO, "1", "10.00")
        resultado = self._extractor().contabilizar_pendientes()
        self.assertEqual(resultado['contabilizados'], 2)

        cuentas_debe = set(
            AsientoContable.objects.filter(empresa=self.empresa)
            .exclude(documento_origen_id=MovimientoInventario.objects.get(tipo='ENTRADA_AJUSTE').id)
            .values_list('movimientos__cuenta_codigo', flat=True)
        )
        self.assertIn('529901', cuentas_debe)  # SALIDA_BAJA
        self.assertIn('519595', cuentas_debe)  # SALIDA_CONSUMO

    # ---- Validaciones ----

    def test_periodo_cerrado_impide_asiento_y_queda_en_errores(self):
        self._crear_movimiento(MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, "3", "10.00")
        self.periodo.estado = 'CERRADO'
        self.periodo.save(update_fields=['estado'])

        resultado = self._extractor().contabilizar_pendientes()
        self.assertEqual(resultado['contabilizados'], 0)
        self.assertEqual(len(resultado['errores']), 1)
        self.assertEqual(AsientoContable.objects.filter(empresa=self.empresa).count(), 0)

    def test_regla_contable_faltante_aisla_el_error_sin_tumbar_el_batch(self):
        ReglaContable.objects.filter(empresa=self.empresa, concepto='PASIVO_COMPRA_INVENTARIO').delete()

        self._crear_y_confirmar_orden_recepcion(consecutivo=1, cantidad_ordenada="5", cantidad_recibida="5")
        self._crear_movimiento(MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, "2", "10.00")

        resultado = self._extractor().contabilizar_pendientes()
        self.assertEqual(resultado['contabilizados'], 1)  # el ajuste si tiene todas sus reglas
        self.assertEqual(len(resultado['errores']), 1)    # la entrada por compra falla por regla faltante
        self.assertIn('COMPRA_INVENTARIO', resultado['errores'][0]['error'])
        self.assertIn('MovimientoInventario', resultado['errores'][0]['ref'])

    def test_movimiento_costo_cero_aisla_asiento_vacio_sin_tumbar_el_batch(self):
        # KardexService.registrar_movimiento() permite costo_unitario=0 (default) -- riesgo de
        # dato real documentado en F22_INVENTARIO_BASELINE.md S1.
        self._crear_movimiento(MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, "5", "0")
        self._crear_movimiento(MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, "3", "10.00")

        resultado = self._extractor().contabilizar_pendientes()
        self.assertEqual(resultado['contabilizados'], 1)
        self.assertEqual(len(resultado['errores']), 1)

    def test_traslado_no_genera_asiento(self):
        barranquilla = Sede.objects.create(empresa=self.empresa, nombre="Barranquilla F22")
        self._crear_movimiento(MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, "50", "10.00", sede_id=self.sede.id)
        self._extractor().contabilizar_pendientes()  # contabiliza el ajuste inicial, no es el foco del test

        traslado = TrasladoInventarioService.solicitar(
            empresa_id=self.empresa.id, producto_id=self.producto.id, cantidad=Decimal("10"),
            sede_origen_id=self.sede.id, sede_destino_id=barranquilla.id, usuario_id=self.perfil.id,
        )
        traslado = TrasladoInventarioService.aprobar(
            traslado_uuid=traslado.uuid, empresa_id=self.empresa.id, usuario_id=self.perfil.id,
        )
        TrasladoInventarioService.enviar(traslado_uuid=traslado.uuid, empresa_id=self.empresa.id)
        TrasladoInventarioService.recibir(
            traslado_uuid=traslado.uuid, empresa_id=self.empresa.id, usuario_id=self.perfil.id,
        )

        asientos_antes = AsientoContable.objects.filter(empresa=self.empresa).count()
        extractor = self._extractor()
        pendientes = extractor.extraer_pendientes()

        # Ni TRASLADO_SALIDA ni TRASLADO_ENTRADA deben aparecer entre los pendientes.
        self.assertFalse(
            MovimientoInventario.objects.filter(
                empresa=self.empresa,
                tipo__in=['TRASLADO_SALIDA', 'TRASLADO_ENTRADA'],
                id__in=[dto.documento_origen.id for dto in pendientes],
            ).exists()
        )
        extractor.contabilizar_pendientes()
        self.assertEqual(
            AsientoContable.objects.filter(empresa=self.empresa).count(), asientos_antes,
        )

    # ---- Multi-tenant / aislamiento se cubre en test_f22_extractor_inventario_multitenant.py ----

    # ---- E2E ----

    def test_e2e_compra_parcial_60_mas_40_no_duplica_primer_asiento(self):
        """S22.23 del prompt maestro F22: orden de 100, recepcion de 60, extraer
        (1 asiento), reextraer (sigue 1), recibir 40 restantes, extraer (2
        asientos totales, el primero no se duplica)."""
        from apps.tenant.compras.models import ItemOrdenCompra, OrdenCompra

        orden = OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede, proveedor=self.proveedor, plantilla=self.plantilla,
            fecha="2026-06-01", consecutivo=1, numero_documento="F22-OC-E2E", estado="APROBADA",
        )
        item = ItemOrdenCompra.objects.create(
            empresa=self.empresa, orden_compra=orden, descripcion="Item E2E",
            item_inventario_uuid=self.producto.uuid,
            cantidad=Decimal("100"), valor_unitario=Decimal("10.00"),
            subtotal=Decimal("1000.00"), total=Decimal("1000.00"),
        )

        def _recibir(cantidad):
            data = {"orden_compra": orden, "fecha": "2026-06-05"}
            items_data = [{"item_orden_compra": item, "cantidad_recibida": Decimal(cantidad)}]
            ok, recepcion, _ = RecepcionCompraBusinessService.crear_recepcion(
                data, items_data, self.empresa, self.sede, self.perfil,
            )
            assert ok, recepcion
            ok, recepcion, _ = RecepcionCompraBusinessService.confirmar_recepcion(recepcion.uuid, self.empresa.id)
            assert ok, recepcion

        _recibir("60")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, Decimal("60.000"))

        r1 = self._extractor().contabilizar_pendientes()
        self.assertEqual(r1['contabilizados'], 1)
        self.assertEqual(AsientoContable.objects.filter(empresa=self.empresa).count(), 1)

        r2 = self._extractor().contabilizar_pendientes()
        self.assertEqual(r2['contabilizados'], 0)
        self.assertEqual(AsientoContable.objects.filter(empresa=self.empresa).count(), 1)

        _recibir("40")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, Decimal("100.000"))

        r3 = self._extractor().contabilizar_pendientes()
        self.assertEqual(r3['contabilizados'], 1)
        self.assertEqual(AsientoContable.objects.filter(empresa=self.empresa).count(), 2)

        total_debe = sum(
            (a.debe_total for a in AsientoContable.objects.filter(empresa=self.empresa)), Decimal('0'),
        )
        self.assertEqual(total_debe, Decimal('1000.00'))  # 100 unidades * 10.00

    def test_e2e_traslado_bogota_barranquilla_sin_asiento_economico(self):
        """S22.24 del prompt maestro F22."""
        barranquilla = Sede.objects.create(empresa=self.empresa, nombre="Barranquilla E2E F22")
        self._crear_movimiento(MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, "100", "5.00", sede_id=self.sede.id)
        self._crear_movimiento(MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, "20", "5.00", sede_id=barranquilla.id)
        self._extractor().contabilizar_pendientes()
        asientos_antes = AsientoContable.objects.filter(empresa=self.empresa).count()

        traslado = TrasladoInventarioService.solicitar(
            empresa_id=self.empresa.id, producto_id=self.producto.id, cantidad=Decimal("30"),
            sede_origen_id=self.sede.id, sede_destino_id=barranquilla.id, usuario_id=self.perfil.id,
        )
        traslado = TrasladoInventarioService.aprobar(
            traslado_uuid=traslado.uuid, empresa_id=self.empresa.id, usuario_id=self.perfil.id,
        )
        TrasladoInventarioService.enviar(traslado_uuid=traslado.uuid, empresa_id=self.empresa.id)
        TrasladoInventarioService.recibir(
            traslado_uuid=traslado.uuid, empresa_id=self.empresa.id, usuario_id=self.perfil.id,
        )

        resultado = self._extractor().contabilizar_pendientes()
        self.assertEqual(resultado['contabilizados'], 0)
        self.assertEqual(
            AsientoContable.objects.filter(empresa=self.empresa).count(), asientos_antes,
        )
