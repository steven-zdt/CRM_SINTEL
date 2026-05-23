"""
Data Transfer Objects (DTOs) para Dashboard v3.9.4
Contratos inmutables entre dashboard y apps de dominio (Pull Model).
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional


@dataclass(frozen=True)
class MetricaSimpleDTO:
    """DTO para una métrica simple (valor + etiqueta)."""
    label: str
    value: float
    delta: Optional[float] = None
    unit: str = ""


@dataclass(frozen=True)
class WidgetFacturasDTO:
    """DTO para métricas de Facturas."""
    total_facturas: int
    facturas_pendientes: int
    facturas_vencidas: int
    ingresos_mes: Decimal
    ingresos_promedio: Decimal


@dataclass(frozen=True)
class WidgetInventarioDTO:
    """DTO para métricas de Inventario (Kardex)."""
    total_productos: int
    productos_bajo_stock: int
    movimientos_mes: int
    valor_inventario: Decimal
    rotacion_promedio: Decimal


@dataclass(frozen=True)
class WidgetEmpleadosDTO:
    """DTO para métricas de Empleados."""
    total_empleados: int
    empleados_activos: int
    nominas_pendientes: int
    total_nómina_mes: Decimal


@dataclass(frozen=True)
class WidgetGastosDTO:
    """DTO para métricas de Gastos."""
    total_gastos_mes: Decimal
    gastos_pendientes: int
    gastos_vencidos: int
    gasto_promedio: Decimal


@dataclass(frozen=True)
class WidgetProyectosDTO:
    """DTO para métricas de Proyectos."""
    total_proyectos: int
    proyectos_activos: int
    tareas_pendientes: int
    tareas_vencidas: int


@dataclass(frozen=True)
class DashboardMetricasDTO:
    """DTO principal que consolida todas las métricas del dashboard."""
    empresa_nombre: str
    empresa_nit: str
    fecha_actualizacion: str
    facturas: WidgetFacturasDTO
    inventario: WidgetInventarioDTO
    empleados: WidgetEmpleadosDTO
    gastos: Optional[WidgetGastosDTO] = None
    proyectos: Optional[WidgetProyectosDTO] = None
