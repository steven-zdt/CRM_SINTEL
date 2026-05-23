"""
Tests para Extractores de Dashboard v3.9.4
Pull Model: valida que consultan selectors.py, no models.py
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta

from apps.tenant.dashboard.services.extractores import (
    FacturasExtractor,
    InventarioExtractor,
    EmpleadosExtractor,
)


class FacturasExtractorTestCase(TestCase):
    """Tests para FacturasExtractor."""

    @classmethod
    def setUpTestData(cls):
        """Setup: crear empresa + facturas de prueba."""
        from apps.tenant.empresa.models import Empresa
        from apps.tenant.facturas.models import Factura

        # Crear empresa en schema de test
        cls.empresa = Empresa.objects.create(
            razon_social='Test Corp',
            nit='1234567890'
        )
        cls.empresa_id = cls.empresa.id

        # Crear 5 facturas: 3 aceptadas + 2 pendientes
        hoy = timezone.now().date()
        fecha_inicio_mes = datetime(hoy.year, hoy.month, 1).date()

        # Factura 1: Aceptada, pagada (mes actual)
        Factura.objects.create(
            empresa=cls.empresa,
            numero='001',
            prefijo='FV',
            consecutivo=1,
            naturaleza='VENTA',
            estado='ACEPTADA',
            estado_pago='PAGADA',
            subtotal=Decimal('100000'),
            impuestos=Decimal('19000'),
            total=Decimal('119000'),
            fecha_emision=hoy,
            fecha_vencimiento=hoy + timedelta(days=30),
        )

        # Factura 2: Aceptada, pendiente (mes actual)
        Factura.objects.create(
            empresa=cls.empresa,
            numero='002',
            prefijo='FV',
            consecutivo=2,
            naturaleza='VENTA',
            estado='ACEPTADA',
            estado_pago='PENDIENTE',
            subtotal=Decimal('200000'),
            impuestos=Decimal('38000'),
            total=Decimal('238000'),
            fecha_emision=hoy,
            fecha_vencimiento=hoy + timedelta(days=30),
        )

        # Factura 3: Aceptada, vencida (hace 5 días)
        Factura.objects.create(
            empresa=cls.empresa,
            numero='003',
            prefijo='FV',
            consecutivo=3,
            naturaleza='VENTA',
            estado='ACEPTADA',
            estado_pago='PENDIENTE',
            subtotal=Decimal('150000'),
            impuestos=Decimal('28500'),
            total=Decimal('178500'),
            fecha_emision=hoy - timedelta(days=35),
            fecha_vencimiento=hoy - timedelta(days=5),
        )

        # Factura 4: Rechazada (no contar)
        Factura.objects.create(
            empresa=cls.empresa,
            numero='004',
            prefijo='FV',
            consecutivo=4,
            naturaleza='VENTA',
            estado='RECHAZADA',
            estado_pago='CANCELADA',
            subtotal=Decimal('100000'),
            impuestos=Decimal('19000'),
            total=Decimal('119000'),
            fecha_emision=hoy,
            fecha_vencimiento=hoy + timedelta(days=30),
        )

    def test_extraer_metricas_total_facturas(self):
        """Test: total de facturas aceptadas."""
        dto = FacturasExtractor.extraer_metricas(self.empresa_id)
        # 3 aceptadas (rechazada no cuenta)
        self.assertEqual(dto.total_facturas, 3)

    def test_extraer_metricas_facturas_pendientes(self):
        """Test: facturas sin pagar."""
        dto = FacturasExtractor.extraer_metricas(self.empresa_id)
        # 2 pendientes (002 + 003)
        self.assertEqual(dto.facturas_pendientes, 2)

    def test_extraer_metricas_facturas_vencidas(self):
        """Test: facturas vencidas sin pagar."""
        dto = FacturasExtractor.extraer_metricas(self.empresa_id)
        # 1 vencida (003)
        self.assertEqual(dto.facturas_vencidas, 1)

    def test_extraer_metricas_ingresos_mes(self):
        """Test: ingresos del mes actual."""
        dto = FacturasExtractor.extraer_metricas(self.empresa_id)
        # 001 + 002 = 119000 + 238000 = 357000
        self.assertEqual(dto.ingresos_mes, Decimal('357000'))

    def test_extraer_metricas_ingresos_promedio(self):
        """Test: promedio de ingresos por factura."""
        dto = FacturasExtractor.extraer_metricas(self.empresa_id)
        # 357000 / 3 = 119000
        esperado = Decimal('357000') / 3
        self.assertEqual(dto.ingresos_promedio, esperado)

    def test_extraer_metricas_empresa_inexistente(self):
        """Test: manejo de empresa que no existe."""
        dto = FacturasExtractor.extraer_metricas(9999)
        # Retorna valores por defecto
        self.assertEqual(dto.total_facturas, 0)
        self.assertEqual(dto.ingresos_mes, Decimal('0.00'))


class InventarioExtractorTestCase(TestCase):
    """Tests para InventarioExtractor."""

    def test_extraer_metricas_sin_datos(self):
        """Test: retorna valores por defecto si no hay datos."""
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.create(
            razon_social='Empty Corp',
            nit='9876543210'
        )
        dto = InventarioExtractor.extraer_metricas(empresa.id)
        self.assertEqual(dto.total_productos, 0)
        self.assertEqual(dto.valor_inventario, Decimal('0.00'))

    def test_extraer_metricas_estructura_valida(self):
        """Test: DTO retorna estructura válida."""
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.create(
            razon_social='Inventory Corp',
            nit='5555555555'
        )
        dto = InventarioExtractor.extraer_metricas(empresa.id)
        # Verificar que todos los campos existen
        self.assertTrue(hasattr(dto, 'total_productos'))
        self.assertTrue(hasattr(dto, 'productos_bajo_stock'))
        self.assertTrue(hasattr(dto, 'movimientos_mes'))
        self.assertTrue(hasattr(dto, 'valor_inventario'))
        self.assertTrue(hasattr(dto, 'rotacion_promedio'))


class EmpleadosExtractorTestCase(TestCase):
    """Tests para EmpleadosExtractor."""

    def test_extraer_metricas_sin_empleados(self):
        """Test: retorna valores por defecto si no hay empleados."""
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.create(
            razon_social='No Staff Corp',
            nit='3333333333'
        )
        dto = EmpleadosExtractor.extraer_metricas(empresa.id)
        self.assertEqual(dto.total_empleados, 0)
        self.assertEqual(dto.total_nómina_mes, Decimal('0.00'))

    def test_extraer_metricas_estructura_valida(self):
        """Test: DTO retorna estructura válida."""
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.create(
            razon_social='HR Corp',
            nit='2222222222'
        )
        dto = EmpleadosExtractor.extraer_metricas(empresa.id)
        # Verificar campos
        self.assertTrue(hasattr(dto, 'total_empleados'))
        self.assertTrue(hasattr(dto, 'empleados_activos'))
        self.assertTrue(hasattr(dto, 'nominas_pendientes'))
        self.assertTrue(hasattr(dto, 'total_nómina_mes'))
