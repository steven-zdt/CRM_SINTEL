"""
F21: Traslado de Inventario entre Sedes. SOLICITADO -> APROBADO -> EN_TRANSITO
-> RECIBIDO, generando TRASLADO_SALIDA/TRASLADO_ENTRADA via KardexService
(nunca modificando MovimientoInventario.sede directamente).
"""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django_tenants.utils import schema_context

from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.inventario.models import MovimientoInventario, Producto, TrasladoInventario
from apps.tenant.inventario.services.business_service import (
    KardexService,
    TrasladoInventarioService,
)
from apps.tenant.inventario.services.selectors import StockPorSedeSelector
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class TrasladoInventarioF21TestsBase(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa F21 Traslado", nit="900000701", direccion="Calle T1",
        )
        self.bogota = Sede.objects.create(empresa=self.empresa, nombre="Bogota F21")
        self.barranquilla = Sede.objects.create(empresa=self.empresa, nombre="Barranquilla F21")
        self.perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa, codigo="PROD-TRASLADO", nombre="Producto Traslado", stock_actual=Decimal("0"),
        )
        # Stock inicial: Bogota=100, Barranquilla=20 (via entradas de ajuste directas).
        KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=self.producto.id,
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, cantidad=Decimal("100"),
            sede_id=self.bogota.id,
        )
        KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=self.producto.id,
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, cantidad=Decimal("20"),
            sede_id=self.barranquilla.id,
        )

    def _stock(self, sede):
        return StockPorSedeSelector.calcular_stock_sede(self.empresa.id, self.producto.id, sede.id)


class TrasladoHappyPathTests(TrasladoInventarioF21TestsBase):
    def test_flujo_completo_bogota_a_barranquilla_30_unidades(self):
        self.assertEqual(self._stock(self.bogota), Decimal("100"))
        self.assertEqual(self._stock(self.barranquilla), Decimal("20"))
        self.assertEqual(self.producto.stock_actual, Decimal("0"))  # aun no recalculado en memoria

        traslado = TrasladoInventarioService.solicitar(
            empresa_id=self.empresa.id, producto_id=self.producto.id, cantidad=Decimal("30"),
            sede_origen_id=self.bogota.id, sede_destino_id=self.barranquilla.id,
            usuario_id=self.perfil.id, motivo="Reabastecimiento",
        )
        self.assertEqual(traslado.estado, TrasladoInventario.Estado.SOLICITADO)

        traslado = TrasladoInventarioService.aprobar(
            traslado_uuid=traslado.uuid, empresa_id=self.empresa.id, usuario_id=self.perfil.id,
        )
        self.assertEqual(traslado.estado, TrasladoInventario.Estado.APROBADO)

        traslado = TrasladoInventarioService.enviar(traslado_uuid=traslado.uuid, empresa_id=self.empresa.id)
        self.assertEqual(traslado.estado, TrasladoInventario.Estado.EN_TRANSITO)

        # Durante el transito: Bogota=70, en_transito=30, Barranquilla=20 (total=120, sin doble conteo).
        self.assertEqual(self._stock(self.bogota), Decimal("70"))
        self.assertEqual(self._stock(self.barranquilla), Decimal("20"))
        en_transito = StockPorSedeSelector.calcular_en_transito(self.empresa.id, self.producto.id)
        self.assertEqual(en_transito, Decimal("30"))

        self.producto.refresh_from_db()
        # empresa-wide (100+20 de las entradas de ajuste del setUp) no cambia por el traslado interno.
        self.assertEqual(self.producto.stock_actual, Decimal("120"))

        traslado = TrasladoInventarioService.recibir(
            traslado_uuid=traslado.uuid, empresa_id=self.empresa.id, usuario_id=self.perfil.id,
        )
        self.assertEqual(traslado.estado, TrasladoInventario.Estado.RECIBIDO)

        # Despues de la recepcion: Bogota=70, Barranquilla=50.
        self.assertEqual(self._stock(self.bogota), Decimal("70"))
        self.assertEqual(self._stock(self.barranquilla), Decimal("50"))
        en_transito = StockPorSedeSelector.calcular_en_transito(self.empresa.id, self.producto.id)
        self.assertEqual(en_transito, Decimal("0"))

        salidas = MovimientoInventario.objects.filter(
            empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.TRASLADO_SALIDA,
        )
        entradas = MovimientoInventario.objects.filter(
            empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.TRASLADO_ENTRADA,
        )
        self.assertEqual(salidas.count(), 1)
        self.assertEqual(entradas.count(), 1)
        self.assertEqual(salidas.first().documento_origen_id, traslado.id)
        self.assertEqual(entradas.first().documento_origen_id, traslado.id)


class TrasladoValidacionesTests(TrasladoInventarioF21TestsBase):
    def test_sede_origen_igual_destino_es_rechazado(self):
        with self.assertRaises(ValidationError):
            TrasladoInventarioService.solicitar(
                empresa_id=self.empresa.id, producto_id=self.producto.id, cantidad=Decimal("10"),
                sede_origen_id=self.bogota.id, sede_destino_id=self.bogota.id, usuario_id=self.perfil.id,
            )

    def test_cantidad_mayor_a_stock_disponible_en_origen_es_rechazado_al_enviar(self):
        traslado = TrasladoInventarioService.solicitar(
            empresa_id=self.empresa.id, producto_id=self.producto.id, cantidad=Decimal("500"),
            sede_origen_id=self.bogota.id, sede_destino_id=self.barranquilla.id, usuario_id=self.perfil.id,
        )
        traslado = TrasladoInventarioService.aprobar(
            traslado_uuid=traslado.uuid, empresa_id=self.empresa.id, usuario_id=self.perfil.id,
        )
        with self.assertRaises(ValidationError):
            TrasladoInventarioService.enviar(traslado_uuid=traslado.uuid, empresa_id=self.empresa.id)

        # No debe haber generado ningun movimiento de salida.
        self.assertEqual(
            MovimientoInventario.objects.filter(
                empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.TRASLADO_SALIDA,
            ).count(),
            0,
        )

    # test_sede_de_otra_empresa_es_rechazada: movido a un test de 2 tenants
    # reales al final de este archivo (Empresa es singleton por schema -
    # ver TrasladoMultiTenantTests mas abajo, no se puede simular "otra
    # empresa" creando una segunda Empresa dentro del mismo schema).

    def test_enviar_sin_aprobar_es_rechazado(self):
        traslado = TrasladoInventarioService.solicitar(
            empresa_id=self.empresa.id, producto_id=self.producto.id, cantidad=Decimal("10"),
            sede_origen_id=self.bogota.id, sede_destino_id=self.barranquilla.id, usuario_id=self.perfil.id,
        )
        with self.assertRaises(ValidationError):
            TrasladoInventarioService.enviar(traslado_uuid=traslado.uuid, empresa_id=self.empresa.id)

    def test_cancelar_en_transito_es_rechazado(self):
        traslado = TrasladoInventarioService.solicitar(
            empresa_id=self.empresa.id, producto_id=self.producto.id, cantidad=Decimal("10"),
            sede_origen_id=self.bogota.id, sede_destino_id=self.barranquilla.id, usuario_id=self.perfil.id,
        )
        traslado = TrasladoInventarioService.aprobar(
            traslado_uuid=traslado.uuid, empresa_id=self.empresa.id, usuario_id=self.perfil.id,
        )
        traslado = TrasladoInventarioService.enviar(traslado_uuid=traslado.uuid, empresa_id=self.empresa.id)
        with self.assertRaises(ValidationError):
            TrasladoInventarioService.cancelar(traslado_uuid=traslado.uuid, empresa_id=self.empresa.id)

    def test_cancelar_en_solicitado_es_permitido(self):
        traslado = TrasladoInventarioService.solicitar(
            empresa_id=self.empresa.id, producto_id=self.producto.id, cantidad=Decimal("10"),
            sede_origen_id=self.bogota.id, sede_destino_id=self.barranquilla.id, usuario_id=self.perfil.id,
        )
        traslado = TrasladoInventarioService.cancelar(traslado_uuid=traslado.uuid, empresa_id=self.empresa.id)
        self.assertEqual(traslado.estado, TrasladoInventario.Estado.CANCELADO)


class TrasladoIdempotenciaTests(TrasladoInventarioF21TestsBase):
    def _traslado_en_transito(self):
        traslado = TrasladoInventarioService.solicitar(
            empresa_id=self.empresa.id, producto_id=self.producto.id, cantidad=Decimal("15"),
            sede_origen_id=self.bogota.id, sede_destino_id=self.barranquilla.id, usuario_id=self.perfil.id,
        )
        traslado = TrasladoInventarioService.aprobar(
            traslado_uuid=traslado.uuid, empresa_id=self.empresa.id, usuario_id=self.perfil.id,
        )
        return TrasladoInventarioService.enviar(traslado_uuid=traslado.uuid, empresa_id=self.empresa.id)

    def test_enviar_dos_veces_no_duplica_movimiento_salida(self):
        traslado = self._traslado_en_transito()
        traslado2 = TrasladoInventarioService.enviar(traslado_uuid=traslado.uuid, empresa_id=self.empresa.id)
        self.assertEqual(traslado2.estado, TrasladoInventario.Estado.EN_TRANSITO)
        self.assertEqual(
            MovimientoInventario.objects.filter(
                empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.TRASLADO_SALIDA,
            ).count(),
            1,
        )

    def test_recibir_dos_veces_no_duplica_movimiento_entrada(self):
        traslado = self._traslado_en_transito()
        traslado = TrasladoInventarioService.recibir(
            traslado_uuid=traslado.uuid, empresa_id=self.empresa.id, usuario_id=self.perfil.id,
        )
        traslado2 = TrasladoInventarioService.recibir(
            traslado_uuid=traslado.uuid, empresa_id=self.empresa.id, usuario_id=self.perfil.id,
        )
        self.assertEqual(traslado2.estado, TrasladoInventario.Estado.RECIBIDO)
        self.assertEqual(
            MovimientoInventario.objects.filter(
                empresa=self.empresa, tipo=MovimientoInventario.TipoMovimiento.TRASLADO_ENTRADA,
            ).count(),
            1,
        )


@pytest.mark.django_db
def test_no_se_puede_trasladar_a_sede_de_otro_tenant(tenant1, tenant2):
    """Aislamiento multi-tenant real (2 schemas): Empresa es singleton por
    schema (`singleton_key` unique) - "otra empresa" solo puede modelarse
    como "otro tenant", no como una segunda fila de Empresa en el mismo
    schema. Se crea una Sede en tenant2; se intenta usarla como destino de
    un traslado resuelto con el empresa_id/producto de tenant1 - debe
    fallar tanto porque la fila fisicamente no existe en el schema de
    tenant1 (Sede.objects.filter(..., empresa_id=empresa_id) no la
    encuentra desde ese schema) como porque, aunque existiera, pertenece a
    otra empresa."""
    with schema_context(tenant1.schema_name):
        emp1 = Empresa.objects.first()
        sede_origen = Sede.objects.create(empresa=emp1, nombre="Origen T1")
        producto1 = Producto.objects.create(empresa=emp1, codigo="F21T1-PROD", nombre="Producto T1")
        empresa1_id = emp1.id
        producto1_id = producto1.id
        sede_origen_id = sede_origen.id

    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        sede_destino_otro_tenant = Sede.objects.create(empresa=emp2, nombre="Destino T2")
        sede_destino_id = sede_destino_otro_tenant.id

    # usuario_id=None: la validacion de sede falla antes de llegar a
    # persistir el traslado (donde usuario_id se usaria de verdad).
    with schema_context(tenant1.schema_name), pytest.raises(ValidationError):
        TrasladoInventarioService.solicitar(
            empresa_id=empresa1_id, producto_id=producto1_id, cantidad=Decimal("5"),
            sede_origen_id=sede_origen_id, sede_destino_id=sede_destino_id, usuario_id=None,
        )
