"""
F27: Regresion del bug cuenta (FK legacy) vs cuenta_codigo (string real).

Contabilizador._construir_asiento() (camino real de todos los extractores)
solo llena MovimientoContable.cuenta_codigo, nunca el FK legacy `cuenta`.
Antes de este fix, balance_prueba_selector/estado_resultados_selector
filtraban/agrupaban por `cuenta__codigo` (ORM Coalesce sobre un JOIN
opcional que nunca resuelve) y quedaban vacios para CUALQUIER tenant usando
la integracion actual; get_documentos_enriquecidos() de los extractores leia
`m.cuenta.codigo` y mostraba 'SIN_CUENTA' en cada linea.

Reutiliza el patron de setUp de F24 (compra E2E via ExtractorInventario) y
verifica extremo a extremo con datos reales -- no mocks -- que ambos
selectores devuelven los valores correctos una vez el asiento esta APROBADO.

Nota: get_libro_diario_periodo() solo agrega ExtractorFacturas/Gastos/Nomina
(no ExtractorInventario usado aqui para generar datos) -- gap documentado por
separado en la auditoria (.agent/AUDITORIA_COMPLETA_CONTABILIDAD.md), no
cubierto por este archivo.
"""
from datetime import date
from decimal import Decimal

from django.utils import timezone

from apps.tenant.compras.models import ItemOrdenCompra, OrdenCompra, PlantillaOrdenCompra
from apps.tenant.compras.services.business_service import RecepcionCompraBusinessService
from apps.tenant.contabilidad.integracion.extractores.inventario import ExtractorInventario
from apps.tenant.contabilidad.models import (
    AsientoContable,
    MovimientoContable,
    PeriodoContable,
    ReglaContable,
)
from apps.tenant.contabilidad.services.selectors import (
    balance_prueba_selector,
    estado_resultados_selector,
)
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.inventario.models import Producto
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase

_REGLAS_INVENTARIO = (
    ("COMPRA_INVENTARIO", "INVENTARIO_PRODUCTO", "143505"),
    ("COMPRA_INVENTARIO", "PASIVO_COMPRA_INVENTARIO", "220505"),
)


class CuentaCodigoReportesBugfixTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa F27", nit="900000927", direccion="Calle F27",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede F27")
        self.perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor F27", numero_documento="F27-PROV-1", tipo_documento="NIT",
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa, nombre="Plantilla F27", prefijo="F27",
            rango_desde=1, rango_hasta=1000, consecutivo_actual=1, vigente=True,
        )
        self.hoy = timezone.localdate()
        self.periodo = PeriodoContable.objects.create(
            empresa=self.empresa, periodo=self.hoy.strftime("%Y-%m"),
            fecha_inicio=date(self.hoy.year, 1, 1), fecha_fin=date(self.hoy.year, 12, 31), estado="ABIERTO",
        )
        for tipo_tx, concepto, cuenta in _REGLAS_INVENTARIO:
            ReglaContable.objects.create(
                empresa=self.empresa, tipo_transaccion=tipo_tx, concepto=concepto,
                cuenta_codigo=cuenta, activo=True,
            )

    def _comprar_y_contabilizar(self):
        producto = Producto.objects.create(
            empresa=self.empresa, codigo="F27-A", nombre="Producto F27 A", stock_actual=Decimal("0"),
        )
        orden = OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede, proveedor=self.proveedor, plantilla=self.plantilla,
            fecha="2026-06-01", consecutivo=self.plantilla.consecutivo_actual, numero_documento="F27-OC-1",
            estado="APROBADA",
        )
        item = ItemOrdenCompra.objects.create(
            empresa=self.empresa, orden_compra=orden, descripcion="Compra F27-A",
            item_inventario_uuid=producto.uuid, cantidad=Decimal("10"), valor_unitario=Decimal("100.00"),
            subtotal=Decimal("1000.00"), total=Decimal("1000.00"),
        )
        data = {"orden_compra": orden, "fecha": "2026-06-02"}
        items_data = [{"item_orden_compra": item, "cantidad_recibida": Decimal("10")}]
        ok, recepcion, code = RecepcionCompraBusinessService.crear_recepcion(
            data, items_data, self.empresa, self.sede, self.perfil,
        )
        assert ok, recepcion
        ok, recepcion, code = RecepcionCompraBusinessService.confirmar_recepcion(recepcion.uuid, self.empresa.id)
        assert ok, recepcion

        resultado = ExtractorInventario(empresa_id=self.empresa.id).contabilizar_pendientes()
        assert resultado["contabilizados"] == 1, resultado

        asiento = AsientoContable.objects.get(empresa=self.empresa, documento_origen_app="inventario")
        return asiento

    def test_contabilizador_solo_llena_cuenta_codigo_nunca_el_fk_legacy(self):
        """Precondicion del bug: confirma que el camino real nunca usa el FK `cuenta`."""
        asiento = self._comprar_y_contabilizar()
        movimientos = MovimientoContable.objects.filter(asiento=asiento)
        self.assertGreater(movimientos.count(), 0)
        for mov in movimientos:
            self.assertIsNone(mov.cuenta_id)
            self.assertTrue(mov.cuenta_codigo)


    def test_balance_prueba_y_estado_resultados_incluyen_asiento_aprobado(self):
        asiento = self._comprar_y_contabilizar()
        # Los reportes solo consideran asientos APROBADO por diseno -- se aprueba
        # explicitamente aqui para ejercitar el filtro real, no solo el fix.
        asiento.estado = "APROBADO"
        asiento.save(update_fields=["estado"])

        fecha_inicio = date(self.hoy.year, 1, 1)
        fecha_fin = date(self.hoy.year, 12, 31)

        filas = balance_prueba_selector(self.empresa.id, fecha_inicio, fecha_fin)
        codigos = {f["codigo"] for f in filas}
        self.assertEqual(codigos, {"143505", "220505"})

        fila_inventario = next(f for f in filas if f["codigo"] == "143505")
        self.assertEqual(fila_inventario["debito"], Decimal("1000.00"))
        self.assertEqual(fila_inventario["nuevo_saldo"], Decimal("1000.00"))

        fila_pasivo = next(f for f in filas if f["codigo"] == "220505")
        self.assertEqual(fila_pasivo["credito"], Decimal("1000.00"))

        # Cuentas 1xx/2xx no son P&G -- estado_resultados_selector debe quedar vacio,
        # pero SIN levantar excepcion (regresion de la reescritura a agregacion Python).
        reporte = estado_resultados_selector(self.empresa.id, fecha_inicio, fecha_fin)
        self.assertEqual(reporte["ingresos"], [])
        self.assertEqual(reporte["gastos"], [])
        self.assertEqual(reporte["totales"]["utilidad_neta"], Decimal("0"))

    def test_balance_prueba_excluye_asientos_en_borrador(self):
        """No-regresion: el filtro estado='APROBADO' sigue siendo respetado."""
        self._comprar_y_contabilizar()  # queda en BORRADOR (default del Contabilizador)
        filas = balance_prueba_selector(
            self.empresa.id, date(self.hoy.year, 1, 1), date(self.hoy.year, 12, 31),
        )
        self.assertEqual(filas, [])
