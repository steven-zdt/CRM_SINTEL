"""
REM P1-05 (docs/remediation/REM-P1-05.md): cerrar_periodo() solo verificaba
que el periodo no estuviera ya CERRADO, sin checklist de pendientes ni
descuadres. Se agrego pre_close_validation() (asientos descuadrados +
documentos sin contabilizar por app, filtrados por fecha del periodo) como
gate real antes de cerrar.
"""
from datetime import date
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.contabilidad.models import AsientoContable, MovimientoContable, PeriodoContable
from apps.tenant.contabilidad.services.business_service import ContabilidadBusinessService
from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import MovimientoInventario, Producto


class CierrePeriodoChecklistP1_05Tests(TenantAPITestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            nombre='Empresa P1-05', nit='900000799',
        )
        self.periodo = PeriodoContable.objects.create(
            empresa=self.empresa, periodo='2026-06',
            fecha_inicio=date(2026, 6, 1), fecha_fin=date(2026, 6, 30), estado='ABIERTO',
        )
        self.service = ContabilidadBusinessService()

    def test_periodo_sin_pendientes_ni_descuadres_puede_cerrarse(self):
        resultado = self.service.pre_close_validation(self.periodo)
        self.assertTrue(resultado['puede_cerrar'], resultado['bloqueos'])
        self.assertEqual(resultado['bloqueos'], [])

        cierre = self.service.cerrar_periodo(self.periodo.id, {})
        self.assertEqual(cierre['status'], 'cerrado')
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.estado, 'CERRADO')

    def test_asiento_descuadrado_en_el_periodo_bloquea_el_cierre(self):
        asiento = AsientoContable.objects.create(
            empresa=self.empresa, fecha=date(2026, 6, 15), numero='TEST-P105-1',
            descripcion='Asiento descuadrado de prueba', periodo_contable=self.periodo,
            estado='BORRADOR', debe_total=Decimal('100.00'), haber_total=Decimal('50.00'),
        )
        resultado = self.service.pre_close_validation(self.periodo)
        self.assertFalse(resultado['puede_cerrar'])
        tipos = [b['tipo'] for b in resultado['bloqueos']]
        self.assertIn('asientos_descuadrados', tipos)

        with self.assertRaises(ValidationError):
            self.service.cerrar_periodo(self.periodo.id, {})
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.estado, 'ABIERTO')

    def test_movimiento_inventario_sin_contabilizar_en_el_periodo_bloquea_el_cierre(self):
        producto = Producto.objects.create(
            empresa=self.empresa, codigo='P105-PROD', nombre='Producto P1-05',
        )
        from django.utils import timezone
        mov = MovimientoInventario.objects.create(
            empresa=self.empresa, producto=producto, tipo='ENTRADA_COMPRA',
            cantidad=Decimal('10'), costo_unitario=Decimal('100.00'),
        )
        mov.created_at = timezone.make_aware(timezone.datetime(2026, 6, 15))
        mov.save(update_fields=['created_at'])

        resultado = self.service.pre_close_validation(self.periodo)
        self.assertFalse(resultado['puede_cerrar'])
        tipos_por_app = {b['app']: b['tipo'] for b in resultado['bloqueos']}
        self.assertEqual(tipos_por_app.get('inventario'), 'documentos_sin_contabilizar')

    def test_documento_fuera_del_periodo_no_bloquea(self):
        """Un movimiento pendiente con fecha FUERA del periodo que se
        quiere cerrar no debe bloquear ese cierre."""
        producto = Producto.objects.create(
            empresa=self.empresa, codigo='P105-PROD-2', nombre='Producto P1-05 B',
        )
        from django.utils import timezone
        mov = MovimientoInventario.objects.create(
            empresa=self.empresa, producto=producto, tipo='ENTRADA_COMPRA',
            cantidad=Decimal('5'), costo_unitario=Decimal('50.00'),
        )
        mov.created_at = timezone.make_aware(timezone.datetime(2026, 8, 1))  # fuera de junio
        mov.save(update_fields=['created_at'])

        resultado = self.service.pre_close_validation(self.periodo)
        self.assertTrue(resultado['puede_cerrar'], resultado['bloqueos'])

    def test_cerrar_periodo_ya_cerrado_sigue_rechazado(self):
        """No regresionar el guard original (mas simple) ya existente."""
        self.periodo.estado = 'CERRADO'
        self.periodo.save(update_fields=['estado'])
        with self.assertRaises(ValidationError):
            self.service.cerrar_periodo(self.periodo.id, {})
