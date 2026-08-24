"""
COMERCIAL-04: idempotencia real de procesar_y_facturar_venta() via
`venta_existente` -- ancla = Venta.uuid (el que ya viaja en el URL de
`POST /ventas/{uuid}/procesar-facturar/`), sin requerir un
Idempotency-Key nuevo del cliente.

Cubre el bug de diseno real encontrado en COMERCIAL-01/COMERCIAL-04
(docs/comercial/COMERCIAL_01_AUDITORIA.md §5-6): antes de este fix,
`procesar_facturar()` siempre creaba una Venta+Factura hermanas nuevas y
dejaba la Venta del URL huerfana en BORRADOR para siempre. Ahora:
- venta_existente en BORRADOR -> se PROMUEVE (misma fila, mismo id).
- venta_existente en FACTURADA_DIAN -> reintento/doble-click, se retorna
  la misma Venta sin re-ejecutar nada (200, no 201, sin duplicar Factura
  ni MovimientoInventario).
- venta_existente en ANULADA -> rechazado (400).
"""
from decimal import Decimal

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.facturas.models import Factura
from apps.tenant.inventario.models import MovimientoInventario, Producto
from apps.tenant.ventas.models import Venta
from apps.tenant.ventas.services.business_service import VentaBusinessService
from apps.tenant.ventas.services.crud_service import VentaCRUDService
from tests.tenant.base_test import SintelTenantTestCase


class VentaFacturaIdempotenciaComercial04Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Comercial-04", nit="900000902", direccion="Calle C04",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede C04")
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="C04-CLI-1", razon_social="Cliente C04 SAS",
            regimen_tributario="ORDINARIO",
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa, codigo="PROD-C04", nombre="Producto C04",
            stock_actual=Decimal("0"), costo_promedio=Decimal("10.00"), precio_venta=Decimal("40.00"),
        )
        from apps.tenant.inventario.services.business_service import KardexService
        KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=self.producto.id,
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
            cantidad=Decimal("50"), costo_unitario=Decimal("10.00"), sede_id=self.sede.id,
        )

    def _crear_venta_borrador(self, cantidad="3"):
        """Mismo camino que VentaBusinessService.crear_venta_borrador() /
        POST /ventas/ -- una Venta BORRADOR real con su ItemVenta persistido."""
        return VentaCRUDService.crear_venta(
            empresa=self.empresa,
            cliente=self.cliente,
            data={"fecha_emision": "2026-06-10"},
            items_data=[{
                "descripcion": "Producto C04",
                "cantidad": cantidad,
                "precio_unitario": "40.00",
                "porcentaje_iva": "19",
                "producto_id": self.producto.id,
            }],
        )

    def _payload_desde_venta(self, venta):
        """Misma reconstruccion de payload que VentaViewSet.procesar_facturar()
        hace a partir de la Venta existente (apps/tenant/ventas/api/viewsets.py)."""
        return {
            "cliente": str(venta.cliente.uuid),
            "fecha_emision": str(venta.fecha_emision),
            "items": [
                {
                    "descripcion": item.descripcion,
                    "cantidad": str(item.cantidad),
                    "precio_unitario": str(item.precio_unitario),
                    "porcentaje_iva": str(item.porcentaje_iva),
                    "producto_id": str(item.producto.uuid) if item.producto_id else None,
                    "servicio_id": str(item.servicio.uuid) if item.servicio_id else None,
                }
                for item in venta.items.select_related("producto", "servicio").all()
            ],
        }

    def test_promueve_la_misma_venta_en_vez_de_crear_una_hermana(self):
        venta_borrador = self._crear_venta_borrador()
        venta_id_original = venta_borrador.id

        ok, venta_resultado, code = VentaBusinessService.procesar_y_facturar_venta(
            empresa=self.empresa,
            payload=self._payload_desde_venta(venta_borrador),
            sede_id=self.sede.id,
            venta_existente=venta_borrador,
        )

        self.assertTrue(ok, venta_resultado)
        self.assertEqual(code, 201)
        self.assertEqual(venta_resultado.id, venta_id_original, "debe ser la MISMA fila, no una nueva")
        self.assertEqual(venta_resultado.estado, Venta.Estado.FACTURADA_DIAN)
        self.assertIsNotNone(venta_resultado.factura_asociada_id)
        self.assertEqual(Venta.objects.filter(empresa=self.empresa).count(), 1, "no debe quedar una segunda Venta huerfana")
        self.assertEqual(Factura.objects.filter(empresa=self.empresa).count(), 1)

    def test_reintento_sobre_venta_ya_facturada_es_idempotente(self):
        venta_borrador = self._crear_venta_borrador()
        ok1, venta1, code1 = VentaBusinessService.procesar_y_facturar_venta(
            empresa=self.empresa,
            payload=self._payload_desde_venta(venta_borrador),
            sede_id=self.sede.id,
            venta_existente=venta_borrador,
        )
        self.assertTrue(ok1)
        self.assertEqual(code1, 201)

        # Reintento (doble-click / retry de red) sobre la MISMA Venta, ya FACTURADA_DIAN.
        venta1.refresh_from_db()
        ok2, venta2, code2 = VentaBusinessService.procesar_y_facturar_venta(
            empresa=self.empresa,
            payload=self._payload_desde_venta(venta_borrador),
            sede_id=self.sede.id,
            venta_existente=venta1,
        )

        self.assertTrue(ok2)
        self.assertEqual(code2, 200, "reintento debe responder 200 (replay), no 201 (creacion)")
        self.assertEqual(venta2.id, venta1.id)
        self.assertEqual(Venta.objects.filter(empresa=self.empresa).count(), 1)
        self.assertEqual(Factura.objects.filter(empresa=self.empresa).count(), 1, "no debe crear una segunda Factura")
        self.assertEqual(
            MovimientoInventario.objects.filter(
                empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
            ).count(),
            1,
            "no debe generar un segundo movimiento de salida de inventario",
        )

    def test_venta_anulada_no_puede_facturarse(self):
        venta_borrador = self._crear_venta_borrador()
        venta_anulada = VentaCRUDService.anular_venta(venta_borrador)

        ok, result, code = VentaBusinessService.procesar_y_facturar_venta(
            empresa=self.empresa,
            payload=self._payload_desde_venta(venta_anulada),
            sede_id=self.sede.id,
            venta_existente=venta_anulada,
        )

        self.assertFalse(ok)
        self.assertEqual(code, 400)
        self.assertIn("anulada", result["detail"].lower())
