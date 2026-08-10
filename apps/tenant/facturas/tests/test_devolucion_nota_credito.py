"""
v3.27: Devoluciones reales via NotaCredito -> ItemNotaCredito -> ENTRADA_DEVOLUCION.

Cierra la brecha DEFERRED desde F23 (`F23_FACTURAS_BASELINE.md` S3):
`NotaCredito` era documento de solo cabecera; ahora `guardar_desde_dto()`
consume los items ya presentes en el DTO del pipeline universal (dto["items"],
poblado por apps/services/document_parser/xml_parser/parser.py para
CreditNoteLine) y dispara KardexService.registrar_movimiento(ENTRADA_DEVOLUCION)
por cada item con Producto resoluble por codigo -- sin tocar
ExtractorInventario/ReglaContable (ya estaban completos desde F22).
"""
from decimal import Decimal

from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.facturas.models import Factura, ItemNotaCredito, NotaCredito
from apps.tenant.facturas.services.business_service import FacturaBusinessService
from apps.tenant.inventario.models import MovimientoInventario, Producto
from apps.tenant.inventario.services.business_service import KardexService
from tests.tenant.base_test import SintelTenantTestCase


class DevolucionNotaCreditoTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa NC", nit="900555111", direccion="Calle NC",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede NC")
        self.producto = Producto.objects.create(
            empresa=self.empresa, codigo="PROD-NC-1", nombre="Producto NC",
            stock_actual=Decimal("0"), costo_promedio=Decimal("50.00"),
        )
        KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=self.producto.id,
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
            cantidad=Decimal("100"), costo_unitario=Decimal("50.00"), sede_id=self.sede.id,
        )
        self.cliente_nit = "900999888"
        self.factura_original = Factura.objects.create(
            empresa=self.empresa, sede=self.sede, numero="FV-NC-1", prefijo="FV", consecutivo=1,
            tipo=Factura.TipoFactura.FE, estado=Factura.Estado.ACEPTADA, naturaleza=Factura.Naturaleza.VENTA,
            fecha_emision="2026-06-01T10:00:00Z",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit=self.cliente_nit, receptor_razon_social="Cliente NC SAS",
            subtotal=Decimal("1000.00"), impuestos=Decimal("190.00"), total=Decimal("1190.00"),
            cufe="CUFE-ORIGINAL-NC-1",
        )

    def _dto(self, items, cude="CUDE-NC-1", numero="NC-1", ref_cufe="CUFE-ORIGINAL-NC-1"):
        return {
            "document_type": "creditnote.ubl21",
            "tipo": "NC",
            "numero": numero,
            "emisor": {"nit": self.empresa.nit, "razon_social": self.empresa.razon_social},
            "receptor": {
                "nit": self.cliente_nit, "razon_social": "Cliente NC SAS", "email": "cliente@nc.test",
            },
            "identificadores": {"cufe": cude},
            "referencia": {"cufe": ref_cufe},
            "totales": {"subtotal": "450.00", "impuestos": "85.50", "total": "535.50", "moneda": "COP"},
            "fecha_emision": "2026-06-10T10:00:00Z",
            "motivo": "Devolucion de mercancia",
            "items": items,
        }

    def _item(self, codigo, cantidad="3", linea_id="1"):
        return {
            "linea_id": linea_id, "codigo": codigo, "descripcion": f"Item {codigo}",
            "cantidad": cantidad, "unidad_medida": "UND", "valor_unitario": "150.00",
            "porcentaje_iva": "19", "subtotal": "450.00", "total": "535.50",
        }

    # ---- Camino real: item con producto resoluble ----

    def test_nc_con_item_resoluble_genera_entrada_devolucion(self):
        dto = self._dto(items=[self._item("PROD-NC-1")])
        resultado, code = FacturaBusinessService.guardar_desde_dto(dto, xml_text="<xml/>", empresa_id=self.empresa.id)
        self.assertEqual(code, 201, resultado)

        nota = NotaCredito.objects.get(cude="CUDE-NC-1")
        self.assertEqual(nota.factura_id, self.factura_original.id)
        self.assertEqual(nota.items.count(), 1)
        item = nota.items.first()
        self.assertEqual(item.item_inventario_uuid, self.producto.uuid)
        self.assertEqual(item.cantidad, Decimal("3.00"))

        mov = MovimientoInventario.objects.get(
            empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.ENTRADA_DEVOLUCION,
        )
        self.assertEqual(mov.cantidad, Decimal("3.000"))
        self.assertEqual(mov.costo_unitario, Decimal("50.00"))  # costo_promedio, NUNCA valor_unitario (150.00)
        self.assertEqual(mov.documento_origen_app, "facturas")
        self.assertEqual(mov.documento_origen_modelo, "ItemNotaCredito")
        self.assertEqual(mov.documento_origen_id, item.id)
        self.assertEqual(mov.sede_id, self.sede.id)  # heredado de factura_original.sede

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, Decimal("103.000"))  # 100 inicial + 3 devueltas

    # ---- Item sin match de codigo: se omite el movimiento, no bloquea la NC ----

    def test_nc_con_item_sin_match_de_codigo_omite_movimiento_sin_fallar(self):
        dto = self._dto(items=[self._item("CODIGO-INEXISTENTE")])
        resultado, code = FacturaBusinessService.guardar_desde_dto(dto, xml_text="<xml/>", empresa_id=self.empresa.id)
        self.assertEqual(code, 201, resultado)

        nota = NotaCredito.objects.get(cude="CUDE-NC-1")
        self.assertEqual(nota.items.count(), 1)
        item = nota.items.first()
        self.assertIsNone(item.item_inventario_uuid)

        self.assertEqual(
            MovimientoInventario.objects.filter(
                empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.ENTRADA_DEVOLUCION,
            ).count(),
            0,
        )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, Decimal("100.000"))  # sin cambios

    # ---- Multi-item: 2 productos + 1 sin match ----

    def test_nc_multi_item_genera_un_movimiento_por_producto_resoluble(self):
        producto_b = Producto.objects.create(
            empresa=self.empresa, codigo="PROD-NC-2", nombre="Producto NC B",
            stock_actual=Decimal("0"), costo_promedio=Decimal("20.00"),
        )
        KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=producto_b.id,
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
            cantidad=Decimal("50"), costo_unitario=Decimal("20.00"), sede_id=self.sede.id,
        )
        dto = self._dto(items=[
            self._item("PROD-NC-1", cantidad="2", linea_id="1"),
            self._item("PROD-NC-2", cantidad="4", linea_id="2"),
            self._item("SIN-MATCH", cantidad="1", linea_id="3"),
        ])
        resultado, code = FacturaBusinessService.guardar_desde_dto(dto, xml_text="<xml/>", empresa_id=self.empresa.id)
        self.assertEqual(code, 201, resultado)

        nota = NotaCredito.objects.get(cude="CUDE-NC-1")
        self.assertEqual(nota.items.count(), 3)
        self.assertEqual(
            MovimientoInventario.objects.filter(
                empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.ENTRADA_DEVOLUCION,
            ).count(),
            2,
        )

    # ---- Idempotencia: re-importar el mismo CUDE no duplica NC ni movimientos ----

    def test_reimportar_mismo_cude_no_duplica_nc_ni_movimiento(self):
        dto = self._dto(items=[self._item("PROD-NC-1")])
        resultado1, code1 = FacturaBusinessService.guardar_desde_dto(dto, xml_text="<xml/>", empresa_id=self.empresa.id)
        self.assertEqual(code1, 201, resultado1)

        resultado2, code2 = FacturaBusinessService.guardar_desde_dto(dto, xml_text="<xml/>", empresa_id=self.empresa.id)
        # Idempotencia por CUDE (mismo mecanismo ya existente para Factura, sin
        # cambios de esta feature): NotaCredito ya existe -> 200, created=False,
        # sin volver a crear items ni movimientos.
        self.assertEqual(code2, 200, resultado2)
        self.assertFalse(resultado2.get("created"))

        self.assertEqual(NotaCredito.objects.filter(cude="CUDE-NC-1").count(), 1)
        self.assertEqual(ItemNotaCredito.objects.count(), 1)
        self.assertEqual(
            MovimientoInventario.objects.filter(
                empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.ENTRADA_DEVOLUCION,
            ).count(),
            1,
        )

    # ---- Servicio (es_servicio) sigue sin generar movimiento (contrato F23 preservado) ----

    def test_nc_sin_items_no_falla_comportamiento_previo_preservado(self):
        """Regresion: una NC sin dto['items'] (XML legacy sin CreditNoteLine parseado,
        o import manual antiguo) se sigue creando exactamente igual que antes de v3.27."""
        dto = self._dto(items=[])
        resultado, code = FacturaBusinessService.guardar_desde_dto(dto, xml_text="<xml/>", empresa_id=self.empresa.id)
        self.assertEqual(code, 201, resultado)
        nota = NotaCredito.objects.get(cude="CUDE-NC-1")
        self.assertEqual(nota.items.count(), 0)
        self.assertEqual(
            MovimientoInventario.objects.filter(
                empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.ENTRADA_DEVOLUCION,
            ).count(),
            0,
        )
