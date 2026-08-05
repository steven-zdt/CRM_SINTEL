"""
Tests para Extractores de Dashboard v3.9.4
Pull Model: valida que consultan selectors.py, no models.py
"""
from decimal import Decimal
from django_tenants.test.cases import TenantTestCase as TestCase
from django.utils import timezone
from datetime import datetime, timedelta

from apps.tenant.dashboard.services.extractores import (
    FacturasExtractor,
    InventarioExtractor,
    EmpleadosExtractor,
    ProveedoresExtractor,
)


class FacturasExtractorTestCase(TestCase):
    """Tests para FacturasExtractor."""

    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa
        from apps.tenant.facturas.models import Factura

        # Limpiar empresas previas
        Empresa.objects.all().delete()

        # Crear empresa en schema de test
        self.empresa = Empresa.objects.create(
            razon_social='Test Corp',
            nit='1234567890',
            direccion='Calle Test 123'
        )
        self.empresa_id = self.empresa.id

        # Crear 5 facturas: 3 aceptadas + 2 pendientes
        hoy = timezone.now().date()
        fecha_inicio_mes = datetime(hoy.year, hoy.month, 1).date()

        # Factura 1: Aceptada, pagada (mes actual)
        Factura.objects.create(
            empresa=self.empresa,
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
            empresa=self.empresa,
            numero='002',
            prefijo='FV',
            consecutivo=2,
            naturaleza='VENTA',
            estado='ACEPTADA',
            estado_pago='NO_PAGADA',
            subtotal=Decimal('200000'),
            impuestos=Decimal('38000'),
            total=Decimal('238000'),
            fecha_emision=hoy,
            fecha_vencimiento=hoy + timedelta(days=30),
        )

        # Factura 3: Aceptada, vencida (hace 5 días)
        Factura.objects.create(
            empresa=self.empresa,
            numero='003',
            prefijo='FV',
            consecutivo=3,
            naturaleza='VENTA',
            estado='ACEPTADA',
            estado_pago='NO_PAGADA',
            subtotal=Decimal('150000'),
            impuestos=Decimal('28500'),
            total=Decimal('178500'),
            fecha_emision=hoy - timedelta(days=35),
            fecha_vencimiento=hoy - timedelta(days=5),
        )

        # Factura 4: Rechazada (no contar)
        Factura.objects.create(
            empresa=self.empresa,
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
        Empresa.objects.all().delete()
        empresa = Empresa.objects.create(
            razon_social='Empty Corp',
            nit='9876543210',
            direccion='Calle Test 123'
        )
        dto = InventarioExtractor.extraer_metricas(empresa.id)
        self.assertEqual(dto.total_productos, 0)
        self.assertEqual(dto.valor_inventario, Decimal('0.00'))

    def test_extraer_metricas_estructura_valida(self):
        """Test: DTO retorna estructura válida."""
        from apps.tenant.empresa.models import Empresa
        Empresa.objects.all().delete()
        empresa = Empresa.objects.create(
            razon_social='Inventory Corp',
            nit='5555555555',
            direccion='Calle Test 123'
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
        Empresa.objects.all().delete()
        empresa = Empresa.objects.create(
            razon_social='No Staff Corp',
            nit='3333333333',
            direccion='Calle Test 123'
        )
        dto = EmpleadosExtractor.extraer_metricas(empresa.id)
        self.assertEqual(dto.total_empleados, 0)
        self.assertEqual(dto.total_nómina_mes, Decimal('0.00'))

    def test_extraer_metricas_estructura_valida(self):
        """Test: DTO retorna estructura válida."""
        from apps.tenant.empresa.models import Empresa
        Empresa.objects.all().delete()
        empresa = Empresa.objects.create(
            razon_social='HR Corp',
            nit='2222222222',
            direccion='Calle Test 123'
        )
        dto = EmpleadosExtractor.extraer_metricas(empresa.id)
        # Verificar campos
        self.assertTrue(hasattr(dto, 'total_empleados'))
        self.assertTrue(hasattr(dto, 'empleados_activos'))
        self.assertTrue(hasattr(dto, 'nominas_pendientes'))
        self.assertTrue(hasattr(dto, 'total_nómina_mes'))


class ProveedoresExtractorTestCase(TestCase):
    """Tests para ProveedoresExtractor."""

    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa
        from apps.tenant.proveedores.models import Proveedor, CuentasPagar

        # Limpiar empresas previas
        Empresa.objects.all().delete()

        # Crear empresa en schema de test
        self.empresa = Empresa.objects.create(
            razon_social='Providers Corp',
            nit='987654321',
            direccion='Calle Test 123'
        )
        self.empresa_id = self.empresa.id

        # Crear proveedores
        self.prov1 = Proveedor.objects.create(
            empresa=self.empresa,
            numero_documento='111',
            razon_social='Proveedor Uno',
            activo=True
        )
        self.prov2 = Proveedor.objects.create(
            empresa=self.empresa,
            numero_documento='222',
            razon_social='Proveedor Dos',
            activo=True
        )
        self.prov_inactivo = Proveedor.objects.create(
            empresa=self.empresa,
            numero_documento='333',
            razon_social='Proveedor Inactivo',
            activo=False
        )

        hoy = timezone.now().date()

        # Crear cuentas por pagar
        # Cuenta 1: Total 500.000, pagado 200.000 (saldo 300.000)
        CuentasPagar.objects.create(
            empresa=self.empresa,
            proveedor=self.prov1,
            numero_factura='FAC-001',
            fecha_emision=hoy,
            fecha_vencimiento=hoy + timedelta(days=30),
            valor_total=Decimal('500000.00'),
            valor_pagado=Decimal('200000.00')
        )
        # Cuenta 2: Total 300.000, pagado 0 (saldo 300.000)
        CuentasPagar.objects.create(
            empresa=self.empresa,
            proveedor=self.prov2,
            numero_factura='FAC-002',
            fecha_emision=hoy,
            fecha_vencimiento=hoy + timedelta(days=15),
            valor_total=Decimal('300000.00'),
            valor_pagado=Decimal('0.00')
        )

    def test_extraer_metricas_total_proveedores(self):
        """Test: total de proveedores activos."""
        dto = ProveedoresExtractor.extraer_metricas(self.empresa_id)
        # Solo prov1 y prov2 son activos. prov_inactivo es inactivo.
        self.assertEqual(dto.total_provedores, 2)

    def test_extraer_metricas_financieras(self):
        """Test: total_gastos y cartera_pendiente."""
        dto = ProveedoresExtractor.extraer_metricas(self.empresa_id)
        # total_gastos = suma de (cartera_pendiente + total_pagado) = 600.000 + 200.000 = 800.000
        # cartera_pendiente = 300.000 + 300.000 = 600.000
        self.assertEqual(dto.cartera_pendiente, Decimal('600000.00'))
        self.assertEqual(dto.total_gastos, Decimal('800000.00'))

    def test_extraer_metricas_sin_datos(self):
        """Test: manejo de empresa sin proveedores."""
        from apps.tenant.proveedores.models import CuentasPagar, Proveedor
        from apps.tenant.empresa.models import Empresa
        CuentasPagar.objects.all().delete()
        Proveedor.objects.all().delete()
        Empresa.objects.all().delete()
        empty_empresa = Empresa.objects.create(
            razon_social='Empty Corp',
            nit='111111111',
            direccion='Calle Falsa 123'
        )
        dto = ProveedoresExtractor.extraer_metricas(empty_empresa.id)
        self.assertEqual(dto.total_provedores, 0)
        self.assertEqual(dto.total_gastos, Decimal('0.00'))
        self.assertEqual(dto.cartera_pendiente, Decimal('0.00'))
