"""
F23: Venta -> Inventario (SALIDA_VENTA real). Cubre el disparo desde
VentaBusinessService.procesar_y_facturar_venta(), multi-item, servicios
excluidos, stock insuficiente (rollback atomico completo), costo desde
Producto.costo_promedio (no precio_unitario), idempotencia, sede, y que
anular_venta() rechaza estructuralmente una venta ya facturada (por lo que
no existe un escenario real de reverso de inventario por anulacion).

Una sola clase con setUp compartido (costo de schema aprendido en F21/F22).
"""
from datetime import date
from decimal import Decimal

from django.utils import timezone

from apps.tenant.clientes.models import Cliente
from apps.tenant.contabilidad.integracion.extractores.inventario import ExtractorInventario
from apps.tenant.contabilidad.models import AsientoContable, PeriodoContable, ReglaContable
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.facturas.models import Factura
from apps.tenant.inventario.models import MovimientoInventario, Producto, Servicio
from apps.tenant.ventas.models import Venta
from apps.tenant.ventas.services.business_service import VentaBusinessService
from tests.tenant.base_test import SintelTenantTestCase


class VentaInventarioF23Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa F23", nit="900000901", direccion="Calle F23",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede F23")
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="F23-CLI-1", razon_social="Cliente F23 SAS",
            regimen_tributario="ORDINARIO",
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa, codigo="PROD-F23", nombre="Producto F23",
            stock_actual=Decimal("0"), costo_promedio=Decimal("15.00"), precio_venta=Decimal("50.00"),
        )
        self.servicio = Servicio.objects.create(
            empresa=self.empresa, codigo="SERV-F23", nombre="Servicio F23", precio_venta=Decimal("30.00"),
        )
        # Stock inicial real via KardexService (mismo mecanismo ya probado en F21/F22).
        from apps.tenant.inventario.services.business_service import KardexService
        KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=self.producto.id,
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
            cantidad=Decimal("100"), costo_unitario=Decimal("15.00"), sede_id=self.sede.id,
        )
        self.producto.refresh_from_db()

    def _payload(self, cantidad_producto="5", incluir_servicio=False, cantidad_servicio="1"):
        items = [{
            "descripcion": "Venta Producto F23",
            "cantidad": cantidad_producto,
            "precio_unitario": "50.00",
            "porcentaje_iva": "19",
            "producto_id": str(self.producto.uuid),
        }]
        if incluir_servicio:
            items.append({
                "descripcion": "Venta Servicio F23",
                "cantidad": cantidad_servicio,
                "precio_unitario": "30.00",
                "porcentaje_iva": "0",
                "servicio_id": str(self.servicio.uuid),
            })
        return {
            "cliente": str(self.cliente.uuid),
            "fecha_emision": "2026-06-05",
            "items": items,
        }

    def _facturar(self, **payload_kwargs):
        payload = self._payload(**payload_kwargs)
        return VentaBusinessService.procesar_y_facturar_venta(
            empresa=self.empresa, payload=payload, sede_id=self.sede.id,
        )

    # ---- Movimiento real ----

    def test_venta_facturada_genera_movimiento_salida_venta(self):
        ok, venta, code = self._facturar(cantidad_producto="5")
        self.assertTrue(ok, venta)
        self.assertEqual(code, 201)
        self.assertEqual(venta.estado, Venta.Estado.FACTURADA_DIAN)
        self.assertIsNotNone(venta.factura_asociada_id)

        item = venta.items.get(producto=self.producto)
        mov = MovimientoInventario.objects.get(
            empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
        )
        self.assertEqual(mov.cantidad, Decimal("5.000"))
        self.assertEqual(mov.documento_origen_app, "ventas")
        self.assertEqual(mov.documento_origen_modelo, "ItemVenta")
        self.assertEqual(mov.documento_origen_id, item.id)
        self.assertEqual(mov.sede_id, self.sede.id)

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, Decimal("95.000"))

    def test_costo_del_movimiento_usa_costo_promedio_no_precio_unitario(self):
        ok, venta, code = self._facturar(cantidad_producto="2")
        self.assertTrue(ok, venta)
        mov = MovimientoInventario.objects.get(
            empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
        )
        # costo_promedio=15.00, NO precio_unitario=50.00 ni precio_venta=50.00
        self.assertEqual(mov.costo_unitario, Decimal("15.00"))

    def test_item_servicio_no_genera_movimiento_inventario(self):
        ok, venta, code = self._facturar(cantidad_producto="3", incluir_servicio=True)
        self.assertTrue(ok, venta)
        self.assertEqual(venta.items.count(), 2)
        # Filtrado por tipo=SALIDA_VENTA: setUp() ya genero 1 ENTRADA_AJUSTE
        # (stock inicial) antes de este test -- solo el item de producto debe
        # generar SALIDA_VENTA, el de servicio ninguno.
        self.assertEqual(
            MovimientoInventario.objects.filter(
                empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
            ).count(),
            1,
        )

    # ---- Stock insuficiente: rollback atomico completo ----

    def test_stock_insuficiente_revierte_venta_y_factura_completas(self):
        ventas_antes = Venta.objects.count()
        facturas_antes = Factura.objects.count()
        movimientos_antes = MovimientoInventario.objects.count()

        ok, result, code = self._facturar(cantidad_producto="500")  # stock real = 100

        self.assertFalse(ok)
        self.assertIn(code, (400, 422, 500))
        # Rollback atomico real: ni la Venta, ni la Factura, ni ningun movimiento quedan creados.
        self.assertEqual(Venta.objects.count(), ventas_antes)
        self.assertEqual(Factura.objects.count(), facturas_antes)
        self.assertEqual(MovimientoInventario.objects.count(), movimientos_antes)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, Decimal("100.000"))

    # ---- Multi-item ----

    def test_multi_item_genera_un_movimiento_por_cada_producto_y_ninguno_para_servicio(self):
        producto_b = Producto.objects.create(
            empresa=self.empresa, codigo="PROD-F23-B", nombre="Producto F23 B",
            stock_actual=Decimal("0"), costo_promedio=Decimal("8.00"),
        )
        from apps.tenant.inventario.services.business_service import KardexService
        KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=producto_b.id,
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
            cantidad=Decimal("50"), costo_unitario=Decimal("8.00"),
        )

        payload = self._payload(cantidad_producto="4", incluir_servicio=True)
        payload["items"].append({
            "descripcion": "Producto B", "cantidad": "6", "precio_unitario": "20.00",
            "porcentaje_iva": "19", "producto_id": str(producto_b.uuid),
        })
        ok, venta, code = VentaBusinessService.procesar_y_facturar_venta(
            empresa=self.empresa, payload=payload, sede_id=self.sede.id,
        )
        self.assertTrue(ok, venta)
        self.assertEqual(venta.items.count(), 3)  # producto A, servicio, producto B
        self.assertEqual(
            MovimientoInventario.objects.filter(
                empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
            ).count(),
            2,
        )

    # ---- Idempotencia (mecanismo subyacente, mismo UniqueConstraint de F21) ----

    def test_reintentar_generar_salida_no_duplica_movimiento(self):
        ok, venta, code = self._facturar(cantidad_producto="3")
        self.assertTrue(ok, venta)
        qs_salida = MovimientoInventario.objects.filter(
            empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
        )
        self.assertEqual(qs_salida.count(), 1)
        # Reintento directo del paso interno (simula timeout/retry/reprocesamiento
        # sobre la misma Venta ya facturada) -- no debe duplicar el movimiento.
        VentaBusinessService._generar_salida_inventario(
            venta=venta, empresa_id=self.empresa.id, sede_id=self.sede.id,
        )
        self.assertEqual(qs_salida.count(), 1)

    # ---- Anulacion: confirma que no hay reverso que implementar ----

    def test_anular_venta_ya_facturada_es_rechazado_estructuralmente(self):
        ok, venta, code = self._facturar(cantidad_producto="1")
        self.assertTrue(ok, venta)
        movimientos_antes = MovimientoInventario.objects.filter(empresa=self.empresa).count()

        ok, result, code = VentaBusinessService.anular_venta(str(venta.uuid), self.empresa.id)
        self.assertFalse(ok)
        self.assertEqual(code, 400)
        venta.refresh_from_db()
        self.assertEqual(venta.estado, Venta.Estado.FACTURADA_DIAN)  # no cambio a ANULADA
        self.assertEqual(
            MovimientoInventario.objects.filter(empresa=self.empresa).count(), movimientos_antes,
        )  # ningun movimiento compensatorio se genero (no hay mecanismo, y no debe haberlo)

    # ---- E2E: Venta -> SALIDA_VENTA -> ExtractorInventario (F22) -> AsientoContable ----

    def test_e2e_venta_facturada_hasta_asiento_contable_via_extractor_f22(self):
        hoy = timezone.localdate()
        PeriodoContable.objects.create(
            empresa=self.empresa, periodo=hoy.strftime("%Y-%m"),
            fecha_inicio=date(hoy.year, 1, 1), fecha_fin=date(hoy.year, 12, 31), estado="ABIERTO",
        )
        # Reglas para SALIDA_INVENTARIO_VENTA (lo que este test ejercita) y
        # tambien para AJUSTE_INVENTARIO (el ENTRADA_AJUSTE que setUp() ya
        # genero como stock inicial) -- sin esta segunda regla,
        # contabilizar_pendientes() reportaria ese movimiento en 'errores'
        # (comportamiento correcto del extractor, no un bug: simplemente no
        # es el foco de este test, asi que se seedea igual que un tenant real
        # lo tendria via seed_reglas_contables).
        for tipo_tx, concepto, cuenta in (
            ("SALIDA_INVENTARIO_VENTA", "COSTO_VENTA_PRODUCTO", "613501"),
            ("SALIDA_INVENTARIO_VENTA", "INVENTARIO_PRODUCTO", "143505"),
            ("AJUSTE_INVENTARIO", "INVENTARIO_PRODUCTO", "143505"),
            ("AJUSTE_INVENTARIO", "INGRESO_AJUSTE_INVENTARIO", "425050"),
        ):
            ReglaContable.objects.create(
                empresa=self.empresa, tipo_transaccion=tipo_tx, concepto=concepto,
                cuenta_codigo=cuenta, activo=True,
            )

        ok, venta, code = self._facturar(cantidad_producto="4")
        self.assertTrue(ok, venta)

        # F22, sin cambios: el extractor detecta el MovimientoInventario nuevo por su cuenta,
        # junto con el ENTRADA_AJUSTE de setUp() (2 movimientos pendientes en total).
        resultado = ExtractorInventario(empresa_id=self.empresa.id).contabilizar_pendientes()
        self.assertEqual(resultado["contabilizados"], 2)
        self.assertEqual(resultado["errores"], [])

        asiento = AsientoContable.objects.get(
            empresa=self.empresa, documento_origen_app="inventario",
            documento_origen_id=MovimientoInventario.objects.get(
                empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
            ).id,
        )
        self.assertEqual(asiento.documento_origen_modelo, "MovimientoInventario")
        self.assertEqual(asiento.debe_total, asiento.haber_total)
        self.assertEqual(asiento.debe_total, Decimal("60.00"))  # 4 unidades * costo_promedio 15.00

        mov = MovimientoInventario.objects.get(
            empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
        )
        self.assertEqual(asiento.documento_origen_id, mov.id)
