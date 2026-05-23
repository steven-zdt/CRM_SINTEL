"""
Tests simplificados para Dashboard v3.9.4
Valida lógica sin depender de la estructura multi-tenant completa
"""
from decimal import Decimal
from django.test import TestCase
from apps.tenant.dashboard.services.dtos import (
    WidgetFacturasDTO,
    WidgetInventarioDTO,
    WidgetEmpleadosDTO,
    WidgetGastosDTO,
    DashboardMetricasDTO,
)
from apps.tenant.dashboard.api.serializers import DashboardMetricasSerializer


class DTOTests(TestCase):
    """Tests para DTOs — validar estructura de datos."""

    def test_widget_facturas_dto_creacion(self):
        """Test: crear WidgetFacturasDTO correctamente."""
        dto = WidgetFacturasDTO(
            total_facturas=10,
            facturas_pendientes=3,
            facturas_vencidas=1,
            ingresos_mes=Decimal('500000.00'),
            ingresos_promedio=Decimal('50000.00')
        )
        self.assertEqual(dto.total_facturas, 10)
        self.assertEqual(dto.facturas_pendientes, 3)
        self.assertEqual(dto.ingresos_mes, Decimal('500000.00'))

    def test_widget_inventario_dto_creacion(self):
        """Test: crear WidgetInventarioDTO correctamente."""
        dto = WidgetInventarioDTO(
            total_productos=50,
            productos_bajo_stock=5,
            movimientos_mes=100,
            valor_inventario=Decimal('1000000.00'),
            rotacion_promedio=Decimal('2.0')
        )
        self.assertEqual(dto.total_productos, 50)
        self.assertEqual(dto.productos_bajo_stock, 5)

    def test_widget_empleados_dto_creacion(self):
        """Test: crear WidgetEmpleadosDTO correctamente."""
        dto = WidgetEmpleadosDTO(
            total_empleados=20,
            empleados_activos=18,
            nominas_pendientes=2,
            total_nómina_mes=Decimal('5000000.00')
        )
        self.assertEqual(dto.total_empleados, 20)
        self.assertEqual(dto.empleados_activos, 18)

    def test_widget_gastos_dto_creacion(self):
        """Test: crear WidgetGastosDTO correctamente."""
        dto = WidgetGastosDTO(
            total_gastos_mes=Decimal('100000.00'),
            gastos_pendientes=5,
            gastos_vencidos=1,
            gasto_promedio=Decimal('20000.00')
        )
        self.assertEqual(dto.total_gastos_mes, Decimal('100000.00'))
        self.assertEqual(dto.gastos_pendientes, 5)

    def test_dashboard_metricas_dto_completo(self):
        """Test: crear DashboardMetricasDTO completo."""
        facturas = WidgetFacturasDTO(
            total_facturas=10, facturas_pendientes=3, facturas_vencidas=1,
            ingresos_mes=Decimal('500000'), ingresos_promedio=Decimal('50000')
        )
        inventario = WidgetInventarioDTO(
            total_productos=50, productos_bajo_stock=5, movimientos_mes=100,
            valor_inventario=Decimal('1000000'), rotacion_promedio=Decimal('2.0')
        )
        empleados = WidgetEmpleadosDTO(
            total_empleados=20, empleados_activos=18, nominas_pendientes=2,
            total_nómina_mes=Decimal('5000000')
        )

        dto = DashboardMetricasDTO(
            empresa_nombre='Test Corp',
            empresa_nit='1234567890',
            fecha_actualizacion='2026-05-23T10:00:00',
            facturas=facturas,
            inventario=inventario,
            empleados=empleados
        )

        self.assertEqual(dto.empresa_nombre, 'Test Corp')
        self.assertEqual(dto.facturas.total_facturas, 10)
        self.assertIsNone(dto.gastos)
        self.assertIsNone(dto.proyectos)

    def test_dashboard_metricas_dto_con_gastos(self):
        """Test: DashboardMetricasDTO con gastos incluidos."""
        facturas = WidgetFacturasDTO(
            total_facturas=10, facturas_pendientes=3, facturas_vencidas=1,
            ingresos_mes=Decimal('500000'), ingresos_promedio=Decimal('50000')
        )
        inventario = WidgetInventarioDTO(
            total_productos=50, productos_bajo_stock=5, movimientos_mes=100,
            valor_inventario=Decimal('1000000'), rotacion_promedio=Decimal('2.0')
        )
        empleados = WidgetEmpleadosDTO(
            total_empleados=20, empleados_activos=18, nominas_pendientes=2,
            total_nómina_mes=Decimal('5000000')
        )
        gastos = WidgetGastosDTO(
            total_gastos_mes=Decimal('100000'), gastos_pendientes=5,
            gastos_vencidos=1, gasto_promedio=Decimal('20000')
        )

        dto = DashboardMetricasDTO(
            empresa_nombre='Test Corp',
            empresa_nit='1234567890',
            fecha_actualizacion='2026-05-23T10:00:00',
            facturas=facturas,
            inventario=inventario,
            empleados=empleados,
            gastos=gastos
        )

        self.assertIsNotNone(dto.gastos)
        self.assertEqual(dto.gastos.total_gastos_mes, Decimal('100000'))


class SerializerTests(TestCase):
    """Tests para Serializers — validar serialización correcta."""

    def test_serializer_dashboard_metricas(self):
        """Test: serializar DashboardMetricasDTO correctamente."""
        facturas = WidgetFacturasDTO(
            total_facturas=10, facturas_pendientes=3, facturas_vencidas=1,
            ingresos_mes=Decimal('500000'), ingresos_promedio=Decimal('50000')
        )
        inventario = WidgetInventarioDTO(
            total_productos=50, productos_bajo_stock=5, movimientos_mes=100,
            valor_inventario=Decimal('1000000'), rotacion_promedio=Decimal('2.0')
        )
        empleados = WidgetEmpleadosDTO(
            total_empleados=20, empleados_activos=18, nominas_pendientes=2,
            total_nómina_mes=Decimal('5000000')
        )

        dto = DashboardMetricasDTO(
            empresa_nombre='Test Corp',
            empresa_nit='1234567890',
            fecha_actualizacion='2026-05-23T10:00:00',
            facturas=facturas,
            inventario=inventario,
            empleados=empleados
        )

        serializer = DashboardMetricasSerializer(dto)
        data = serializer.data

        self.assertEqual(data['empresa_nombre'], 'Test Corp')
        self.assertEqual(data['empresa_nit'], '1234567890')
        self.assertEqual(data['facturas']['total_facturas'], 10)
        self.assertEqual(data['inventario']['total_productos'], 50)
        self.assertEqual(data['empleados']['total_empleados'], 20)

    def test_serializer_decimal_formatting(self):
        """Test: serializer formatea decimales correctamente."""
        facturas = WidgetFacturasDTO(
            total_facturas=1, facturas_pendientes=0, facturas_vencidas=0,
            ingresos_mes=Decimal('1234567.89'), ingresos_promedio=Decimal('1234567.89')
        )
        inventario = WidgetInventarioDTO(
            total_productos=0, productos_bajo_stock=0, movimientos_mes=0,
            valor_inventario=Decimal('0.00'), rotacion_promedio=Decimal('0.00')
        )
        empleados = WidgetEmpleadosDTO(
            total_empleados=0, empleados_activos=0, nominas_pendientes=0,
            total_nómina_mes=Decimal('0.00')
        )

        dto = DashboardMetricasDTO(
            empresa_nombre='Test',
            empresa_nit='123',
            fecha_actualizacion='2026-05-23T10:00:00',
            facturas=facturas,
            inventario=inventario,
            empleados=empleados
        )

        serializer = DashboardMetricasSerializer(dto)
        data = serializer.data

        # Verificar que los decimales se serializan como strings con 2 decimales
        self.assertIsInstance(data['facturas']['ingresos_mes'], str)
        self.assertEqual(data['facturas']['ingresos_mes'], '1234567.89')
