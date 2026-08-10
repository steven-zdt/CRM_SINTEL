"""
F24.17/F24.41: confirmar_recepcion() procesa varios RecepcionCompraItem en un
loop dentro de un unico @transaction.atomic. Antes de esta correccion, si el
item N fallaba validacion (ValidationError) DESPUES de que el item N-1 ya
hubiera escrito su ItemOrdenCompra.cantidad_recibida y su MovimientoInventario
(ENTRADA_COMPRA) real, el except capturaba la excepcion y retornaba
(False, ..., 400) SIN volver a lanzarla y SIN transaction.set_rollback(True) --
Django nunca revierte un atomic() cuando la excepcion no escapa de la funcion
decorada, asi que el item N-1 quedaba comprometido (commit) pese a que la
operacion completa reportaba ok=False.

Mismo bug de atomicidad que F23 encontro y corrigio en
VentaBusinessService.procesar_y_facturar_venta() (ver F23_FINAL_REPORT.md #3),
detectado aqui via escaneo AST de F24 sobre los @transaction.atomic de
compras/inventario/ventas/facturas y confirmado con reproduccion real.
"""
from decimal import Decimal

from apps.tenant.compras.models import ItemOrdenCompra, OrdenCompra, PlantillaOrdenCompra, RecepcionCompra
from apps.tenant.compras.services.business_service import RecepcionCompraBusinessService
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.inventario.models import MovimientoInventario, Producto
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class ConfirmarRecepcionAtomicidadF24Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa F24", nit="900000524", direccion="Calle F24",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede F24")
        self.perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor F24", numero_documento="F24-1", tipo_documento="NIT",
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa, nombre="Plantilla F24", prefijo="F24",
            rango_desde=1, rango_hasta=1000, consecutivo_actual=1, vigente=True,
        )
        self.producto_a = Producto.objects.create(
            empresa=self.empresa, codigo="PROD-F24-A", nombre="Producto F24 A", stock_actual=Decimal("0"),
        )
        self.producto_b = Producto.objects.create(
            empresa=self.empresa, codigo="PROD-F24-B", nombre="Producto F24 B", stock_actual=Decimal("0"),
        )
        self.orden = OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede, proveedor=self.proveedor, plantilla=self.plantilla,
            fecha="2026-06-01", consecutivo=1, numero_documento="F24-OC-1", estado="APROBADA",
        )
        self.item_a = ItemOrdenCompra.objects.create(
            empresa=self.empresa, orden_compra=self.orden, descripcion="Item F24 A",
            item_inventario_uuid=self.producto_a.uuid,
            cantidad=Decimal("100"), valor_unitario=Decimal("10.00"),
            subtotal=Decimal("1000.00"), total=Decimal("1000.00"),
        )
        self.item_b = ItemOrdenCompra.objects.create(
            empresa=self.empresa, orden_compra=self.orden, descripcion="Item F24 B",
            item_inventario_uuid=self.producto_b.uuid,
            cantidad=Decimal("50"), valor_unitario=Decimal("5.00"),
            subtotal=Decimal("250.00"), total=Decimal("250.00"),
        )

    def test_fallo_en_segundo_item_revierte_por_completo_el_primero(self):
        """
        Reproduce la condicion de carrera: la recepcion se crea cuando ambos
        items todavia tienen espacio, pero ANTES de confirmarla, otra
        recepcion concurrente ya confirmo casi todo el item B (simulado con
        un .update() directo, sin pasar por el Service Layer, exactamente
        como lo haria una segunda transaccion real que ya hizo commit). Al
        confirmar esta recepcion, el item A (primero en el loop, id menor)
        se procesa con exito -- ItemOrdenCompra.cantidad_recibida actualizado
        y MovimientoInventario(ENTRADA_COMPRA) creado -- y luego el item B
        excede lo pendiente y lanza ValidationError. La operacion completa
        debe fallar SIN dejar rastro del item A.
        """
        data = {"orden_compra": self.orden, "fecha": "2026-06-05"}
        items_data = [
            {"item_orden_compra": self.item_a, "cantidad_recibida": Decimal("20")},
            {"item_orden_compra": self.item_b, "cantidad_recibida": Decimal("10")},
        ]
        ok, recepcion, code = RecepcionCompraBusinessService.crear_recepcion(
            data, items_data, self.empresa, self.sede, self.perfil,
        )
        self.assertTrue(ok, recepcion)

        # Simula la recepcion concurrente que ya confirmo 45/50 del item B
        # antes de que esta recepcion llegue a confirmarse.
        ItemOrdenCompra.objects.filter(pk=self.item_b.pk).update(cantidad_recibida=Decimal("45.00"))

        ok, resultado, code = RecepcionCompraBusinessService.confirmar_recepcion(
            recepcion.uuid, self.empresa.id,
        )
        self.assertFalse(ok, resultado)
        self.assertEqual(code, 400)

        self.item_a.refresh_from_db()
        self.item_b.refresh_from_db()
        self.producto_a.refresh_from_db()
        recepcion.refresh_from_db()

        # El item A NO debe quedar actualizado: si el rollback fallara,
        # cantidad_recibida seria 20.00 en vez de 0.
        self.assertEqual(self.item_a.cantidad_recibida, Decimal("0.00"))
        # El item B conserva el valor simulado de la "otra" transaccion (no
        # se le suma el 10 de esta recepcion fallida).
        self.assertEqual(self.item_b.cantidad_recibida, Decimal("45.00"))
        # Sin stock movido para A: si el rollback fallara, stock_actual seria 20.
        self.assertEqual(self.producto_a.stock_actual, Decimal("0"))
        self.assertEqual(
            MovimientoInventario.objects.filter(
                empresa=self.empresa, producto=self.producto_a,
                tipo=MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
            ).count(),
            0,
        )
        # La recepcion en si tampoco debe quedar CONFIRMADA.
        self.assertEqual(recepcion.estado, RecepcionCompra.Estado.BORRADOR)

    def test_confirmacion_normal_sin_conflicto_sigue_funcionando(self):
        """Regresion: el camino feliz (sin race) no se ve afectado por el fix."""
        data = {"orden_compra": self.orden, "fecha": "2026-06-05"}
        items_data = [
            {"item_orden_compra": self.item_a, "cantidad_recibida": Decimal("20")},
            {"item_orden_compra": self.item_b, "cantidad_recibida": Decimal("10")},
        ]
        ok, recepcion, code = RecepcionCompraBusinessService.crear_recepcion(
            data, items_data, self.empresa, self.sede, self.perfil,
        )
        self.assertTrue(ok, recepcion)

        ok, recepcion, code = RecepcionCompraBusinessService.confirmar_recepcion(
            recepcion.uuid, self.empresa.id,
        )
        self.assertTrue(ok, recepcion)
        self.assertEqual(recepcion.estado, RecepcionCompra.Estado.CONFIRMADA)

        self.item_a.refresh_from_db()
        self.item_b.refresh_from_db()
        self.assertEqual(self.item_a.cantidad_recibida, Decimal("20.00"))
        self.assertEqual(self.item_b.cantidad_recibida, Decimal("10.00"))
        self.assertEqual(
            MovimientoInventario.objects.filter(
                empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
            ).count(),
            2,
        )
