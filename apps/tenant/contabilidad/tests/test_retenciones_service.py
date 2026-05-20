"""
Tests para RetencionesService (v3.7.1).

Cubre:
- obtener_retenciones_desde_tercero() con NIT específico y defaults
- calcular_monto_retencion() con precisión Decimal
- crear_retencion() y crear_retenciones_desde_dict()
- listar_retenciones_por_documento()
- total_retenciones_por_documento()
- reversar_retencion()
- obtener_retencion_por_uuid()
"""

from decimal import Decimal
from django.test import TestCase
from django.db import transaction

from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.contabilidad.models import (
    ConfiguracionRetenciones, Retencion, CuentaContable, AsientoContable
)
from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
from apps.tenant.empresa.models import Empresa


class RetencionesServiceTestCase(TenantAPITestCase):
    """Tests para RetencionesService (Pull Model)."""

    def setUp(self):
        super().setUp()

        # Crear empresa SSoT
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            nombre='Test Corp',
            nit='900123456',
            razon_social='Test Corp S.A.',
        )

        # Crear cuenta contable para retenciones
        self.cuenta = CuentaContable.objects.create(
            empresa=self.empresa,
            codigo='2365',
            nombre='Retención en la Fuente',
            nivel=6,
            tipo='PASIVO',
            activa=True,
        )

    def test_obtener_retenciones_desde_tercero_con_nit_especifico(self):
        """Test: Obtener retenciones configuradas para un NIT específico."""
        nit = '123456789'

        # Crear configuración específica para este NIT
        config = ConfiguracionRetenciones.objects.create(
            empresa=self.empresa,
            tipo_tercero='CLIENTE',
            nit_tercero=nit,
            tipo_retencion='RETEFUENTE',
            porcentaje_por_defecto=Decimal('2.50'),
            naturaleza='VENTA',
            cuenta_retencion=self.cuenta,
            activa=True,
        )

        resultado = RetencionesService.obtener_retenciones_desde_tercero(
            nit=nit,
            tipo_tercero='CLIENTE',
            naturaleza='VENTA',
        )

        self.assertTrue(resultado['aplica_retefuente'])
        self.assertEqual(resultado['retefuente_porcentaje'], Decimal('2.50'))

    def test_obtener_retenciones_desde_tercero_fallback_a_defaults(self):
        """Test: Fallback a defaults cuando no existe config específica."""
        nit = '999888777'

        # Crear config default (sin NIT específico)
        ConfiguracionRetenciones.objects.create(
            empresa=self.empresa,
            tipo_tercero='CLIENTE',
            nit_tercero=None,
            tipo_retencion='RETEFUENTE',
            porcentaje_por_defecto=Decimal('1.00'),
            naturaleza='VENTA',
            cuenta_retencion=self.cuenta,
            activa=True,
        )

        resultado = RetencionesService.obtener_retenciones_desde_tercero(
            nit=nit,
            tipo_tercero='CLIENTE',
            naturaleza='VENTA',
        )

        self.assertTrue(resultado['aplica_retefuente'])
        self.assertEqual(resultado['retefuente_porcentaje'], Decimal('1.00'))

    def test_obtener_retenciones_nit_normalization(self):
        """Test: Los NITs se normalizan (sin puntos, guiones)."""
        nit_denormalizado = '123.456.789-1'
        nit_normalizado = '1234567891'

        ConfiguracionRetenciones.objects.create(
            empresa=self.empresa,
            tipo_tercero='PROVEEDOR',
            nit_tercero=nit_normalizado,
            tipo_retencion='RETEICA',
            porcentaje_por_defecto=Decimal('0.50'),
            naturaleza='COMPRA',
            cuenta_retencion=self.cuenta,
            activa=True,
        )

        # Debe encontrar el registro aunque pasemos NIT denormalizado
        resultado = RetencionesService.obtener_retenciones_desde_tercero(
            nit=nit_denormalizado,
            tipo_tercero='PROVEEDOR',
            naturaleza='COMPRA',
        )

        self.assertTrue(resultado['aplica_reteica'])
        self.assertEqual(resultado['reteica_porcentaje'], Decimal('0.50'))

    def test_calcular_monto_retencion_precision_decimal(self):
        """Test: El cálculo de monto preserva precisión Decimal."""
        base = Decimal('10000.00')
        porcentaje = Decimal('2.50')

        monto = RetencionesService.calcular_monto_retencion(
            tipo='RETEFUENTE',
            porcentaje=porcentaje,
            base=base,
        )

        # (10000 × 2.50) / 100 = 250.00
        self.assertEqual(monto, Decimal('250.00'))
        self.assertIsInstance(monto, Decimal)

    def test_calcular_monto_retencion_con_decimales(self):
        """Test: El cálculo funciona con valores decimales complejos."""
        base = Decimal('15750.55')
        porcentaje = Decimal('3.25')

        monto = RetencionesService.calcular_monto_retencion(
            tipo='RETEIVA',
            porcentaje=porcentaje,
            base=base,
        )

        # (15750.55 × 3.25) / 100 = 511.89
        expected = (base * porcentaje) / Decimal('100')
        self.assertEqual(monto, expected)

    def test_crear_retencion_single(self):
        """Test: Crear un registro individual de retención."""
        retencion = RetencionesService.crear_retencion(
            empresa=self.empresa,
            tipo='RETEFUENTE',
            porcentaje=Decimal('2.50'),
            base=Decimal('5000.00'),
            monto=Decimal('125.00'),
            documento_origen_app='facturas',
            documento_origen_modelo='Factura',
            documento_origen_id=1,
            notas='Test retencion',
        )

        self.assertIsNotNone(retencion.uuid)
        self.assertEqual(retencion.tipo, 'RETEFUENTE')
        self.assertEqual(retencion.monto, Decimal('125.00'))
        self.assertFalse(retencion.reversada)

    def test_crear_retenciones_desde_dict_con_montos(self):
        """Test: Crear múltiples retenciones desde dict con montos ya calculados."""
        ret_dict = {
            'aplica_retefuente': True,
            'retefuente_porcentaje': Decimal('2.50'),
            'aplica_reteica': True,
            'reteica_porcentaje': Decimal('0.50'),
            'aplica_reteiva': False,
            'reteiva_porcentaje': Decimal('0.00'),
        }

        retenciones = RetencionesService.crear_retenciones_desde_dict(
            empresa=self.empresa,
            ret_dict=ret_dict,
            documento_origen_app='facturas',
            documento_origen_modelo='ItemFactura',
            documento_origen_id=5,
            porcentaje_retefuente=Decimal('2.50'),
            base_retefuente=Decimal('1000.00'),
        )

        self.assertEqual(len(retenciones), 2)  # 2 activas (no RETEIVA)
        self.assertEqual(retenciones[0].tipo, 'RETEFUENTE')
        self.assertEqual(retenciones[0].monto, Decimal('25.00'))

    def test_listar_retenciones_por_documento(self):
        """Test: Listar todas las retenciones de un documento."""
        doc_id = 42

        # Crear 3 retenciones para el mismo documento
        for tipo in ['RETEFUENTE', 'RETEICA', 'RETEIVA']:
            RetencionesService.crear_retencion(
                empresa=self.empresa,
                tipo=tipo,
                porcentaje=Decimal('1.00'),
                base=Decimal('1000.00'),
                monto=Decimal('10.00'),
                documento_origen_app='facturas',
                documento_origen_modelo='Factura',
                documento_origen_id=doc_id,
            )

        retenciones = RetencionesService.listar_retenciones_por_documento(
            documento_origen_app='facturas',
            documento_origen_modelo='Factura',
            documento_origen_id=doc_id,
        )

        self.assertEqual(len(retenciones), 3)
        tipos = {r.tipo for r in retenciones}
        self.assertEqual(tipos, {'RETEFUENTE', 'RETEICA', 'RETEIVA'})

    def test_total_retenciones_por_documento(self):
        """Test: Calcular suma de retenciones para un documento."""
        doc_id = 100

        # Crear retenciones con montos diferentes
        RetencionesService.crear_retencion(
            empresa=self.empresa,
            tipo='RETEFUENTE',
            porcentaje=Decimal('2.50'),
            base=Decimal('5000.00'),
            monto=Decimal('125.00'),
            documento_origen_app='facturas',
            documento_origen_modelo='Factura',
            documento_origen_id=doc_id,
        )

        RetencionesService.crear_retencion(
            empresa=self.empresa,
            tipo='RETEICA',
            porcentaje=Decimal('0.50'),
            base=Decimal('5000.00'),
            monto=Decimal('25.00'),
            documento_origen_app='facturas',
            documento_origen_modelo='Factura',
            documento_origen_id=doc_id,
        )

        total = RetencionesService.total_retenciones_por_documento(
            documento_origen_app='facturas',
            documento_origen_modelo='Factura',
            documento_origen_id=doc_id,
        )

        self.assertEqual(total, Decimal('150.00'))

    def test_total_retenciones_con_filtro_tipo(self):
        """Test: Suma de retenciones filtrada por tipo específico."""
        doc_id = 200

        RetencionesService.crear_retencion(
            empresa=self.empresa,
            tipo='RETEFUENTE',
            monto=Decimal('100.00'),
            documento_origen_app='facturas',
            documento_origen_modelo='Factura',
            documento_origen_id=doc_id,
        )

        RetencionesService.crear_retencion(
            empresa=self.empresa,
            tipo='RETEICA',
            monto=Decimal('50.00'),
            documento_origen_app='facturas',
            documento_origen_modelo='Factura',
            documento_origen_id=doc_id,
        )

        total_retefuente = RetencionesService.total_retenciones_por_documento(
            documento_origen_app='facturas',
            documento_origen_modelo='Factura',
            documento_origen_id=doc_id,
            tipo='RETEFUENTE',
        )

        self.assertEqual(total_retefuente, Decimal('100.00'))

    def test_reversar_retencion(self):
        """Test: Crear reversal de una retención existente."""
        ret_original = RetencionesService.crear_retencion(
            empresa=self.empresa,
            tipo='RETEFUENTE',
            monto=Decimal('150.00'),
            documento_origen_app='facturas',
            documento_origen_modelo='Factura',
            documento_origen_id=50,
        )

        ret_reversal = RetencionesService.reversar_retencion(
            retencion=ret_original,
            empresa=self.empresa,
            documento_reversada_app='facturas',
            documento_reversada_modelo='NotaCredito',
            documento_reversada_id=1,
        )

        # Verificar que el original está marcado como reversado
        ret_original.refresh_from_db()
        self.assertTrue(ret_original.reversada)

        # Verificar que el reversal es negativo
        self.assertEqual(ret_reversal.monto, Decimal('-150.00'))
        self.assertEqual(ret_reversal.retencion_reversada_por.id, ret_original.id)

    def test_obtener_retencion_por_uuid(self):
        """Test: Buscar retención por UUID."""
        retencion = RetencionesService.crear_retencion(
            empresa=self.empresa,
            tipo='RETEIVA',
            monto=Decimal('75.00'),
            documento_origen_app='facturas',
            documento_origen_modelo='Factura',
            documento_origen_id=60,
        )

        encontrada = RetencionesService.obtener_retencion_por_uuid(
            uuid=retencion.uuid
        )

        self.assertEqual(encontrada.id, retencion.id)
        self.assertEqual(encontrada.tipo, 'RETEIVA')

    def test_obtener_retencion_por_uuid_no_existe(self):
        """Test: Retorna None si el UUID no existe."""
        import uuid as uuid_module
        inexistente_uuid = uuid_module.uuid4()

        encontrada = RetencionesService.obtener_retencion_por_uuid(
            uuid=inexistente_uuid
        )

        self.assertIsNone(encontrada)

    def test_atomicidad_crear_retenciones_desde_dict(self):
        """Test: Si una retención falla, toda la operación se revierte."""
        with self.assertRaises(Exception):
            RetencionesService.crear_retenciones_desde_dict(
                empresa=self.empresa,
                ret_dict={'invalid': 'dict'},
                documento_origen_app='facturas',
                documento_origen_modelo='Factura',
                documento_origen_id=999,
            )

        # Verificar que no se creó ningún registro
        retenciones = Retencion.objects.filter(
            documento_origen_id=999
        )
        self.assertEqual(retenciones.count(), 0)
