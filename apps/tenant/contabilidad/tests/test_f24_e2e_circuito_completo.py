"""
F24: Auditoria E2E Enterprise del circuito F21+F22+F23.

Cubre los escenarios E2E que F21/F22/F23 NO ejercitaron juntos en una sola
corrida: Compra hasta Asiento, Venta hasta Asiento (costo vs precio), Compra+
Venta con reconciliacion de stock, multi-item mixto, multi-sede, idempotencia
del lado contable (extractor+contabilizador corridos dos veces), periodo
cerrado, y que los traslados internos permanecen fuera de la contabilizacion
economica (decision ya documentada en F22).

No reimplementa nada de F21/F22/F23: reutiliza RecepcionCompraBusinessService,
KardexService, VentaBusinessService, ExtractorInventario y Contabilizador tal
como quedaron. Una sola clase con setUp compartido (costo de schema aprendido
en F21/F22/F23).
"""
from datetime import date
from decimal import Decimal

from django.utils import timezone

from apps.tenant.clientes.models import Cliente
from apps.tenant.compras.models import ItemOrdenCompra, OrdenCompra, PlantillaOrdenCompra, RecepcionCompra
from apps.tenant.compras.services.business_service import RecepcionCompraBusinessService
from apps.tenant.contabilidad.integracion.extractores.inventario import ExtractorInventario
from apps.tenant.contabilidad.models import AsientoContable, PeriodoContable, ReglaContable
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.inventario.models import MovimientoInventario, Producto, Servicio, TrasladoInventario
from apps.tenant.inventario.services.business_service import KardexService, TrasladoInventarioService
from apps.tenant.inventario.services.selectors import StockPorSedeSelector
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from apps.tenant.ventas.models import Venta
from apps.tenant.ventas.services.business_service import VentaBusinessService
from tests.tenant.base_test import SintelTenantTestCase

_REGLAS_INVENTARIO = (
    ("COMPRA_INVENTARIO", "INVENTARIO_PRODUCTO", "143505"),
    ("COMPRA_INVENTARIO", "PASIVO_COMPRA_INVENTARIO", "220505"),
    ("SALIDA_INVENTARIO_VENTA", "COSTO_VENTA_PRODUCTO", "613501"),
    ("SALIDA_INVENTARIO_VENTA", "INVENTARIO_PRODUCTO", "143505"),
    ("AJUSTE_INVENTARIO", "INVENTARIO_PRODUCTO", "143505"),
    ("AJUSTE_INVENTARIO", "INGRESO_AJUSTE_INVENTARIO", "425050"),
)


class CircuitoE2EF24Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa F24", nit="900000924", direccion="Calle F24",
        )
        self.sede_bogota = Sede.objects.create(empresa=self.empresa, nombre="Bogota F24")
        self.sede_barranquilla = Sede.objects.create(empresa=self.empresa, nombre="Barranquilla F24")
        self.perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor F24", numero_documento="F24-PROV-1", tipo_documento="NIT",
        )
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="F24-CLI-1", razon_social="Cliente F24 SAS", regimen_tributario="ORDINARIO",
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa, nombre="Plantilla F24", prefijo="F24",
            rango_desde=1, rango_hasta=1000, consecutivo_actual=1, vigente=True,
        )

        hoy = timezone.localdate()
        self.periodo = PeriodoContable.objects.create(
            empresa=self.empresa, periodo=hoy.strftime("%Y-%m"),
            fecha_inicio=date(hoy.year, 1, 1), fecha_fin=date(hoy.year, 12, 31), estado="ABIERTO",
        )
        for tipo_tx, concepto, cuenta in _REGLAS_INVENTARIO:
            ReglaContable.objects.create(
                empresa=self.empresa, tipo_transaccion=tipo_tx, concepto=concepto,
                cuenta_codigo=cuenta, activo=True,
            )

    # ---- helpers ----

    def _crear_orden(self, sede, numero="F24-OC-1"):
        return OrdenCompra.objects.create(
            empresa=self.empresa, sede=sede, proveedor=self.proveedor, plantilla=self.plantilla,
            fecha="2026-06-01", consecutivo=self.plantilla.consecutivo_actual, numero_documento=numero,
            estado="APROBADA",
        )

    def _comprar(self, producto, cantidad, valor_unitario, sede=None):
        sede = sede or self.sede_bogota
        orden = self._crear_orden(sede, numero=f"F24-OC-{producto.codigo}")
        item = ItemOrdenCompra.objects.create(
            empresa=self.empresa, orden_compra=orden, descripcion=f"Compra {producto.codigo}",
            item_inventario_uuid=producto.uuid, cantidad=Decimal(cantidad), valor_unitario=Decimal(valor_unitario),
            subtotal=Decimal(cantidad) * Decimal(valor_unitario), total=Decimal(cantidad) * Decimal(valor_unitario),
        )
        data = {"orden_compra": orden, "fecha": "2026-06-02"}
        items_data = [{"item_orden_compra": item, "cantidad_recibida": Decimal(cantidad)}]
        ok, recepcion, code = RecepcionCompraBusinessService.crear_recepcion(
            data, items_data, self.empresa, sede, self.perfil,
        )
        assert ok, recepcion
        ok, recepcion, code = RecepcionCompraBusinessService.confirmar_recepcion(recepcion.uuid, self.empresa.id)
        assert ok, recepcion
        return orden, item, recepcion

    def _vender(self, items_payload, sede=None):
        payload = {
            "cliente": str(self.cliente.uuid), "fecha_emision": "2026-06-05", "items": items_payload,
        }
        return VentaBusinessService.procesar_y_facturar_venta(
            empresa=self.empresa, payload=payload, sede_id=(sede or self.sede_bogota).id,
        )

    def _item_producto(self, producto, cantidad, precio="20.00"):
        return {
            "descripcion": f"Venta {producto.codigo}", "cantidad": str(cantidad), "precio_unitario": precio,
            "porcentaje_iva": "19", "producto_id": str(producto.uuid),
        }

    # ---- F24.6: Compra E2E hasta Asiento ----

    def test_f24_compra_e2e_hasta_asiento_contable(self):
        producto = Producto.objects.create(
            empresa=self.empresa, codigo="F24-A", nombre="Producto F24 A", stock_actual=Decimal("0"),
        )
        orden, item, recepcion = self._comprar(producto, "10", "100.00")

        producto.refresh_from_db()
        orden.refresh_from_db()
        self.assertEqual(producto.stock_actual, Decimal("10.000"))
        self.assertEqual(orden.estado, "RECIBIDA")

        mov = MovimientoInventario.objects.get(
            empresa=self.empresa, producto=producto, tipo=MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
        )
        self.assertEqual(mov.documento_origen_app, "compras")
        self.assertEqual(mov.documento_origen_modelo, "RecepcionCompraItem")
        self.assertEqual(mov.sede_id, self.sede_bogota.id)

        resultado = ExtractorInventario(empresa_id=self.empresa.id).contabilizar_pendientes()
        self.assertEqual(resultado["contabilizados"], 1)
        self.assertEqual(resultado["errores"], [])

        asiento = AsientoContable.objects.get(
            empresa=self.empresa, documento_origen_app="inventario", documento_origen_id=mov.id,
        )
        self.assertEqual(asiento.debe_total, asiento.haber_total)
        self.assertEqual(asiento.debe_total, Decimal("1000.00"))  # 10 * 100

    # ---- F24.7: Venta E2E -- costo = Q x costo_promedio, nunca Q x precio_venta ----

    def test_f24_venta_e2e_costo_promedio_no_precio_venta(self):
        producto = Producto.objects.create(
            empresa=self.empresa, codigo="F24-B", nombre="Producto F24 B",
            stock_actual=Decimal("0"), costo_promedio=Decimal("12.00"), precio_venta=Decimal("45.00"),
        )
        KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=producto.id,
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, cantidad=Decimal("50"),
            costo_unitario=Decimal("12.00"), sede_id=self.sede_bogota.id,
        )

        ok, venta, code = self._vender([self._item_producto(producto, "6", precio="45.00")])
        self.assertTrue(ok, venta)

        mov = MovimientoInventario.objects.get(
            empresa=self.empresa, producto=producto, tipo=MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
        )
        self.assertEqual(mov.costo_unitario, Decimal("12.00"))  # costo_promedio, NO precio_venta (45.00)

        resultado = ExtractorInventario(empresa_id=self.empresa.id).contabilizar_pendientes()
        # 2 pendientes: el ENTRADA_AJUSTE de este test + el SALIDA_VENTA.
        self.assertEqual(resultado["contabilizados"], 2)
        self.assertEqual(resultado["errores"], [])

        asiento = AsientoContable.objects.get(
            empresa=self.empresa, documento_origen_app="inventario", documento_origen_id=mov.id,
        )
        self.assertEqual(asiento.debe_total, asiento.haber_total)
        self.assertEqual(asiento.debe_total, Decimal("72.00"))  # 6 * 12.00, nunca 6 * 45.00

    # ---- F24.8: Compra + Venta -- reconciliacion de stock y costo ----

    def test_f24_compra_mas_venta_reconciliacion_stock(self):
        producto = Producto.objects.create(
            empresa=self.empresa, codigo="F24-C", nombre="Producto F24 C", stock_actual=Decimal("0"),
        )
        self._comprar(producto, "10", "100.00")
        producto.refresh_from_db()
        self.assertEqual(producto.stock_actual, Decimal("10.000"))
        # Producto.costo_promedio es estatico (F23_FINAL_REPORT.md #4): la
        # compra NO lo recalcula automaticamente. Se fija explicitamente aqui
        # para poder verificar la reconciliacion de costo_venta = Q x C.
        producto.costo_promedio = Decimal("100.00")
        producto.save(update_fields=["costo_promedio"])

        ok, venta, code = self._vender([self._item_producto(producto, "3", precio="150.00")])
        self.assertTrue(ok, venta)

        producto.refresh_from_db()
        # stock_inicial(0) + entrada(10) - salida(3) = stock_final(7)
        self.assertEqual(producto.stock_actual, Decimal("7.000"))

        mov_salida = MovimientoInventario.objects.get(
            empresa=self.empresa, producto=producto, tipo=MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
        )
        costo_venta = mov_salida.cantidad * mov_salida.costo_unitario
        self.assertEqual(costo_venta, Decimal("300.00"))  # 3 * 100

        resultado = ExtractorInventario(empresa_id=self.empresa.id).contabilizar_pendientes()
        self.assertEqual(resultado["contabilizados"], 2)  # ENTRADA_COMPRA + SALIDA_VENTA
        self.assertEqual(resultado["errores"], [])
        self.assertEqual(
            AsientoContable.objects.filter(empresa=self.empresa).count(), 2,
        )

    # ---- F24.9: Multi-item -- 3 productos + 1 servicio ----

    def test_f24_multi_item_tres_productos_y_servicio(self):
        productos = []
        for codigo, stock in (("F24-MI-A", "20"), ("F24-MI-B", "20"), ("F24-MI-C", "20")):
            p = Producto.objects.create(
                empresa=self.empresa, codigo=codigo, nombre=codigo, stock_actual=Decimal("0"),
                costo_promedio=Decimal("10.00"),
            )
            KardexService.registrar_movimiento(
                empresa_id=self.empresa.id, producto_id=p.id,
                tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, cantidad=Decimal(stock),
                costo_unitario=Decimal("10.00"), sede_id=self.sede_bogota.id,
            )
            productos.append(p)
        servicio = Servicio.objects.create(
            empresa=self.empresa, codigo="F24-MI-SERV", nombre="Servicio F24", precio_venta=Decimal("99.00"),
        )

        items_payload = [
            self._item_producto(productos[0], "2"),
            self._item_producto(productos[1], "3"),
            self._item_producto(productos[2], "5"),
            {
                "descripcion": "Servicio F24", "cantidad": "1", "precio_unitario": "99.00",
                "porcentaje_iva": "0", "servicio_id": str(servicio.uuid),
            },
        ]
        ok, venta, code = self._vender(items_payload)
        self.assertTrue(ok, venta)
        self.assertEqual(venta.items.count(), 4)

        esperado = {productos[0].id: Decimal("2.000"), productos[1].id: Decimal("3.000"), productos[2].id: Decimal("5.000")}
        for p in productos:
            mov = MovimientoInventario.objects.get(
                empresa=self.empresa, producto=p, tipo=MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
            )
            self.assertEqual(mov.cantidad, esperado[p.id])

        # El servicio no genera ningun MovimientoInventario -- solo 3 SALIDA_VENTA en total.
        self.assertEqual(
            MovimientoInventario.objects.filter(
                empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
            ).count(),
            3,
        )

    # ---- F24.10: Multi-sede -- ventas independientes por sede ----

    def test_f24_multi_sede_stock_independiente(self):
        producto = Producto.objects.create(
            empresa=self.empresa, codigo="F24-MS", nombre="Producto Multi-Sede", stock_actual=Decimal("0"),
        )
        KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=producto.id,
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, cantidad=Decimal("100"),
            costo_unitario=Decimal("5.00"), sede_id=self.sede_bogota.id,
        )
        KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=producto.id,
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, cantidad=Decimal("50"),
            costo_unitario=Decimal("5.00"), sede_id=self.sede_barranquilla.id,
        )
        self.assertEqual(StockPorSedeSelector.calcular_stock_sede(self.empresa.id, producto.id, self.sede_bogota.id), Decimal("100"))
        self.assertEqual(StockPorSedeSelector.calcular_stock_sede(self.empresa.id, producto.id, self.sede_barranquilla.id), Decimal("50"))

        ok, venta, code = self._vender([self._item_producto(producto, "20")], sede=self.sede_bogota)
        self.assertTrue(ok, venta)
        self.assertEqual(StockPorSedeSelector.calcular_stock_sede(self.empresa.id, producto.id, self.sede_bogota.id), Decimal("80"))
        self.assertEqual(StockPorSedeSelector.calcular_stock_sede(self.empresa.id, producto.id, self.sede_barranquilla.id), Decimal("50"))

        ok, venta, code = self._vender([self._item_producto(producto, "10")], sede=self.sede_barranquilla)
        self.assertTrue(ok, venta)
        self.assertEqual(StockPorSedeSelector.calcular_stock_sede(self.empresa.id, producto.id, self.sede_bogota.id), Decimal("80"))
        self.assertEqual(StockPorSedeSelector.calcular_stock_sede(self.empresa.id, producto.id, self.sede_barranquilla.id), Decimal("40"))

    # ---- F24.16: Idempotencia contable -- doble corrida extractor+contabilizador ----

    def test_f24_idempotencia_contable_doble_corrida(self):
        producto = Producto.objects.create(
            empresa=self.empresa, codigo="F24-IDEM", nombre="Producto Idempotencia", stock_actual=Decimal("0"),
        )
        self._comprar(producto, "5", "50.00")

        extractor = ExtractorInventario(empresa_id=self.empresa.id)
        primera = extractor.contabilizar_pendientes()
        self.assertEqual(primera["contabilizados"], 1)
        self.assertEqual(primera["errores"], [])

        segunda = extractor.contabilizar_pendientes()
        self.assertEqual(segunda["contabilizados"], 0)
        self.assertEqual(segunda["omitidos"], 0)  # ya no hay pendientes: extraer_pendientes() los excluye
        self.assertEqual(segunda["total"], 0)

        self.assertEqual(
            AsientoContable.objects.filter(
                empresa=self.empresa, documento_origen_app="inventario",
            ).count(),
            1,
        )

    # ---- F24.22: Periodo cerrado -- no crea asiento, no bypassea ----

    def test_f24_periodo_cerrado_rechaza_contabilizacion(self):
        self.periodo.estado = "CERRADO"
        self.periodo.save(update_fields=["estado"])

        producto = Producto.objects.create(
            empresa=self.empresa, codigo="F24-CERRADO", nombre="Producto Periodo Cerrado", stock_actual=Decimal("0"),
        )
        self._comprar(producto, "4", "25.00")

        resultado = ExtractorInventario(empresa_id=self.empresa.id).contabilizar_pendientes()
        self.assertEqual(resultado["contabilizados"], 0)
        self.assertEqual(len(resultado["errores"]), 1)
        self.assertIn("cerrado", resultado["errores"][0]["error"].lower())
        self.assertEqual(AsientoContable.objects.filter(empresa=self.empresa).count(), 0)

    # ---- F24.3/F24.4: Traslado permanece fuera de la contabilizacion economica ----

    def test_f24_traslado_no_genera_asiento_contable_externo(self):
        producto = Producto.objects.create(
            empresa=self.empresa, codigo="F24-TRAS", nombre="Producto Traslado F24", stock_actual=Decimal("0"),
        )
        KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=producto.id,
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, cantidad=Decimal("30"),
            costo_unitario=Decimal("7.00"), sede_id=self.sede_bogota.id,
        )
        traslado = TrasladoInventarioService.solicitar(
            empresa_id=self.empresa.id, producto_id=producto.id, cantidad=Decimal("10"),
            sede_origen_id=self.sede_bogota.id, sede_destino_id=self.sede_barranquilla.id,
            usuario_id=self.perfil.id, motivo="F24 E2E",
        )
        traslado = TrasladoInventarioService.aprobar(
            traslado_uuid=traslado.uuid, empresa_id=self.empresa.id, usuario_id=self.perfil.id,
        )
        traslado = TrasladoInventarioService.enviar(traslado_uuid=traslado.uuid, empresa_id=self.empresa.id)
        traslado = TrasladoInventarioService.recibir(
            traslado_uuid=traslado.uuid, empresa_id=self.empresa.id, usuario_id=self.perfil.id,
        )
        self.assertEqual(traslado.estado, TrasladoInventario.Estado.RECIBIDO)
        self.assertEqual(
            MovimientoInventario.objects.filter(
                empresa=self.empresa, producto=producto,
                tipo__in=[
                    MovimientoInventario.TipoMovimiento.TRASLADO_SALIDA,
                    MovimientoInventario.TipoMovimiento.TRASLADO_ENTRADA,
                ],
            ).count(),
            2,
        )

        # El ENTRADA_AJUSTE inicial si es contabilizable; los TRASLADO_* no lo son.
        resultado = ExtractorInventario(empresa_id=self.empresa.id).contabilizar_pendientes()
        self.assertEqual(resultado["contabilizados"], 1)
        self.assertEqual(resultado["errores"], [])
        self.assertEqual(
            AsientoContable.objects.filter(
                empresa=self.empresa, documento_origen_modelo="MovimientoInventario",
            ).count(),
            1,
        )
