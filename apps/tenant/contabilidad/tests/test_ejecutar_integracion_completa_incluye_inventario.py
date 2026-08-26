"""
Regresion real (mision REL, hallazgo CRITICAL-3 de
docs/integration/CROSS_APP_FINDINGS.md): ExtractorInventario existia,
estaba probado (F22) y registrado en extractores/__init__.py, pero
ContabilidadBusinessService.ejecutar_integracion_completa() -- el unico
metodo que invoca el Celery task periodico real (contabilidad/tasks.py) --
no lo incluia en su lista de extractores, pese a que el propio docstring
de esa tarea promete sincronizar "Facturas, Gastos e Inventario". El costo
de venta/compra de Inventario nunca llegaba al libro mayor por el pipeline
automatico -- solo via el management command manual backfill_contabilidad.py.
"""
from datetime import date
from decimal import Decimal

from django.utils import timezone

from apps.tenant.contabilidad.models import AsientoContable, PeriodoContable, ReglaContable
from apps.tenant.contabilidad.services.business_service import ContabilidadBusinessService
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.inventario.models import MovimientoInventario, Producto
from apps.tenant.inventario.services.business_service import KardexService
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class EjecutarIntegracionCompletaIncluyeInventarioTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa REL Inventario", nit="900000941", direccion="Calle REL",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede REL Inventario")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")
        self.producto = Producto.objects.create(
            empresa=self.empresa, codigo="PROD-REL-1", nombre="Producto REL", stock_actual=Decimal("0"),
        )
        hoy = timezone.localdate()
        PeriodoContable.objects.create(
            empresa=self.empresa, periodo=hoy.strftime('%Y-%m'),
            fecha_inicio=date(hoy.year, 1, 1), fecha_fin=date(hoy.year, 12, 31), estado="ABIERTO",
        )
        ReglaContable.objects.create(
            empresa=self.empresa, tipo_transaccion="AJUSTE_INVENTARIO",
            concepto="INVENTARIO_PRODUCTO", cuenta_codigo="143505", activo=True,
        )
        ReglaContable.objects.create(
            empresa=self.empresa, tipo_transaccion="AJUSTE_INVENTARIO",
            concepto="INGRESO_AJUSTE_INVENTARIO", cuenta_codigo="425050", activo=True,
        )
        KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=self.producto.id,
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
            cantidad=Decimal("5"), costo_unitario=Decimal("20.00"),
        )

    def test_ejecutar_integracion_completa_contabiliza_inventario(self):
        resultado = ContabilidadBusinessService().ejecutar_integracion_completa(self.empresa.id)

        self.assertIn("ExtractorInventario", resultado["extractores"])
        stats = resultado["extractores"]["ExtractorInventario"]
        self.assertNotIn("error", stats)
        self.assertEqual(stats["contabilizados"], 1)
        self.assertEqual(stats["errores"], [])

        self.assertTrue(
            AsientoContable.objects.filter(empresa=self.empresa, documento_origen_app="inventario").exists()
        )
