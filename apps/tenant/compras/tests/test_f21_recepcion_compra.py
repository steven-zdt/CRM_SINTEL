"""
F21: Recepcion de Compras. OrdenCompra -> RecepcionCompra -> RecepcionCompraItem
-> MovimientoInventario (via KardexService), con idempotencia y validacion de
cantidades pendientes.
"""
from decimal import Decimal

import pytest
from django_tenants.utils import schema_context

from apps.tenant.compras.models import (
    ItemOrdenCompra,
    OrdenCompra,
    PlantillaOrdenCompra,
    RecepcionCompra,
)
from apps.tenant.compras.services.business_service import RecepcionCompraBusinessService
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.inventario.models import MovimientoInventario, Producto
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class RecepcionCompraF21TestsBase(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa F21", nit="900000521", direccion="Calle F21",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede F21")
        self.perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor F21", numero_documento="F21-1", tipo_documento="NIT",
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa, nombre="Plantilla F21", prefijo="F21",
            rango_desde=1, rango_hasta=1000, consecutivo_actual=1, vigente=True,
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa, codigo="PROD-F21", nombre="Producto F21", stock_actual=Decimal("0"),
        )
        self.orden = OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede, proveedor=self.proveedor, plantilla=self.plantilla,
            fecha="2026-06-01", consecutivo=1, numero_documento="F21-OC-1", estado="APROBADA",
        )
        self.item = ItemOrdenCompra.objects.create(
            empresa=self.empresa, orden_compra=self.orden, descripcion="Item F21",
            item_inventario_uuid=self.producto.uuid,
            cantidad=Decimal("100"), valor_unitario=Decimal("10.00"),
            subtotal=Decimal("1000.00"), total=Decimal("1000.00"),
        )

    def _crear_y_confirmar(self, cantidad):
        data = {"orden_compra": self.orden, "fecha": "2026-06-05"}
        items_data = [{"item_orden_compra": self.item, "cantidad_recibida": cantidad}]
        ok, recepcion, code = RecepcionCompraBusinessService.crear_recepcion(
            data, items_data, self.empresa, self.sede, self.perfil,
        )
        assert ok, recepcion
        ok, recepcion, code = RecepcionCompraBusinessService.confirmar_recepcion(
            recepcion.uuid, self.empresa.id,
        )
        assert ok, recepcion
        return recepcion


class RecepcionTotalTests(RecepcionCompraF21TestsBase):
    def test_recepcion_total_genera_movimiento_y_marca_orden_recibida(self):
        recepcion = self._crear_y_confirmar(Decimal("100"))

        self.item.refresh_from_db()
        self.orden.refresh_from_db()
        self.producto.refresh_from_db()

        self.assertEqual(self.item.cantidad_recibida, Decimal("100.00"))
        self.assertEqual(self.orden.estado, "RECIBIDA")
        self.assertEqual(self.producto.stock_actual, Decimal("100.000"))
        self.assertEqual(recepcion.estado, RecepcionCompra.Estado.CONFIRMADA)

        movimientos = MovimientoInventario.objects.filter(
            empresa=self.empresa, producto=self.producto, tipo=MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
        )
        self.assertEqual(movimientos.count(), 1)
        mov = movimientos.first()
        self.assertEqual(mov.cantidad, Decimal("100.000"))
        self.assertEqual(mov.sede_id, self.sede.id)
        self.assertEqual(mov.documento_origen_app, 'compras')
        self.assertEqual(mov.documento_origen_modelo, 'RecepcionCompraItem')


class RecepcionParcialTests(RecepcionCompraF21TestsBase):
    def test_dos_recepciones_parciales_completan_la_orden_y_tercer_exceso_se_rechaza(self):
        self._crear_y_confirmar(Decimal("60"))
        self.orden.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(self.orden.estado, "PARCIAL")
        self.assertEqual(self.item.cantidad_recibida, Decimal("60.00"))

        self._crear_y_confirmar(Decimal("40"))
        self.orden.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(self.orden.estado, "RECIBIDA")
        self.assertEqual(self.item.cantidad_recibida, Decimal("100.00"))

        movimientos = MovimientoInventario.objects.filter(
            empresa=self.empresa, producto=self.producto, tipo=MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
        )
        self.assertEqual(movimientos.count(), 2)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, Decimal("100.000"))

        # Un tercer intento de recibir 10 mas: la orden ya esta RECIBIDA (100%
        # completa), por lo que se rechaza en el guard de estado (mas
        # temprano/mas especifico que el de cantidad pendiente, pero el mismo
        # resultado de negocio: la recepcion NO se crea).
        data = {"orden_compra": self.orden, "fecha": "2026-06-06"}
        items_data = [{"item_orden_compra": self.item, "cantidad_recibida": Decimal("10")}]
        ok, result, code = RecepcionCompraBusinessService.crear_recepcion(
            data, items_data, self.empresa, self.sede, self.perfil,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 422)
        self.assertEqual(result.get("error"), "estado_invalido")
        # No debe haberse creado una tercera recepcion ni un tercer movimiento.
        self.assertEqual(RecepcionCompra.objects.filter(orden_compra=self.orden).count(), 2)
        self.assertEqual(movimientos.count(), 2)

    def test_recibir_mas_de_lo_pendiente_mientras_orden_sigue_parcial_es_rechazado(self):
        """Mismo guard, pero disparado por el guard de cantidad (no el de
        estado): la orden queda PARCIAL (60/100) y se intenta recibir 50 mas
        (excede el pendiente real de 40)."""
        self._crear_y_confirmar(Decimal("60"))
        self.orden.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(self.orden.estado, "PARCIAL")

        data = {"orden_compra": self.orden, "fecha": "2026-06-06"}
        items_data = [{"item_orden_compra": self.item, "cantidad_recibida": Decimal("50")}]
        ok, result, code = RecepcionCompraBusinessService.crear_recepcion(
            data, items_data, self.empresa, self.sede, self.perfil,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 422)
        self.assertEqual(result.get("error"), "cantidad_excede_pendiente")
        self.assertEqual(RecepcionCompra.objects.filter(orden_compra=self.orden).count(), 1)


class RecepcionIdempotenciaTests(RecepcionCompraF21TestsBase):
    def test_confirmar_dos_veces_no_duplica_movimiento(self):
        recepcion = self._crear_y_confirmar(Decimal("30"))

        # Segunda llamada a confirmar_recepcion (ej. doble click / retry HTTP).
        ok, recepcion2, code = RecepcionCompraBusinessService.confirmar_recepcion(
            recepcion.uuid, self.empresa.id,
        )
        self.assertTrue(ok)
        self.assertEqual(code, 200)
        self.assertEqual(recepcion2.uuid, recepcion.uuid)

        movimientos = MovimientoInventario.objects.filter(
            empresa=self.empresa, producto=self.producto, tipo=MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
        )
        self.assertEqual(movimientos.count(), 1)

        self.item.refresh_from_db()
        self.assertEqual(self.item.cantidad_recibida, Decimal("30.00"))

    def test_anular_recepcion_confirmada_es_rechazado(self):
        recepcion = self._crear_y_confirmar(Decimal("10"))
        ok, result, code = RecepcionCompraBusinessService.anular_recepcion(recepcion.uuid, self.empresa.id)
        self.assertFalse(ok)
        self.assertEqual(code, 422)
        recepcion.refresh_from_db()
        self.assertEqual(recepcion.estado, RecepcionCompra.Estado.CONFIRMADA)


class RecepcionSinReferenciaCatalogoTests(RecepcionCompraF21TestsBase):
    def test_item_sin_producto_de_catalogo_no_genera_movimiento_pero_recepcion_es_valida(self):
        item_libre = ItemOrdenCompra.objects.create(
            empresa=self.empresa, orden_compra=self.orden, descripcion="Item sin catalogo",
            item_inventario_uuid=None,
            cantidad=Decimal("5"), valor_unitario=Decimal("20.00"),
            subtotal=Decimal("100.00"), total=Decimal("100.00"),
        )
        data = {"orden_compra": self.orden, "fecha": "2026-06-07"}
        items_data = [{"item_orden_compra": item_libre, "cantidad_recibida": Decimal("5")}]
        ok, recepcion, code = RecepcionCompraBusinessService.crear_recepcion(
            data, items_data, self.empresa, self.sede, self.perfil,
        )
        self.assertTrue(ok, recepcion)
        ok, recepcion, code = RecepcionCompraBusinessService.confirmar_recepcion(recepcion.uuid, self.empresa.id)
        self.assertTrue(ok, recepcion)
        self.assertEqual(recepcion.estado, RecepcionCompra.Estado.CONFIRMADA)

        item_libre.refresh_from_db()
        self.assertEqual(item_libre.cantidad_recibida, Decimal("5.00"))
        self.assertEqual(MovimientoInventario.objects.filter(empresa=self.empresa).count(), 0)


@pytest.mark.django_db
def test_orden_de_otro_tenant_no_se_puede_recibir(tenant1, tenant2):
    """Aislamiento multi-tenant real (2 schemas, no 2 Empresa en el mismo
    schema): Empresa es un singleton por schema (`singleton_key` unique),
    asi que "otra empresa" solo puede modelarse como "otro tenant". Se crea
    la OrdenCompra en tenant1; se intenta recibirla pasando su UUID (tal
    como llegaria de un cliente real) mientras se opera en el schema/Empresa
    de tenant2 - debe fallar por ausencia real de la fila en ese schema, no
    solo por un mismatch de empresa_id en memoria."""
    with schema_context(tenant1.schema_name):
        emp1 = Empresa.objects.first()
        sede1 = Sede.objects.create(empresa=emp1, nombre="Sede F21 T1")
        proveedor1 = Proveedor.objects.create(
            empresa=emp1, razon_social="Prov F21 T1", numero_documento="F21T1-1", tipo_documento="NIT",
        )
        plantilla1 = PlantillaOrdenCompra.objects.create(
            empresa=emp1, nombre="Plantilla F21 T1", prefijo="F21T1",
            rango_desde=1, rango_hasta=100, consecutivo_actual=1, vigente=True,
        )
        orden1 = OrdenCompra.objects.create(
            empresa=emp1, sede=sede1, proveedor=proveedor1, plantilla=plantilla1,
            fecha="2026-06-01", consecutivo=1, numero_documento="F21T1-OC-1", estado="APROBADA",
        )
        orden1_uuid = str(orden1.uuid)

    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        data = {"orden_compra": orden1_uuid, "fecha": "2026-06-05"}
        ok, result, code = RecepcionCompraBusinessService.crear_recepcion(
            data, [{"item_orden_compra": None, "cantidad_recibida": 1}], emp2, None, None,
        )
        assert ok is False
        assert code == 404
        assert result.get("error") == "orden_no_encontrada"
