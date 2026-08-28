"""
Data Transfer Objects (DTOs) para Dashboard v3.9.4
Contratos inmutables entre dashboard y apps de dominio (Pull Model).
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional


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
    # REM P3-03 (docs/remediation/REM-P3-03.md): antes se llamaba
    # gastos_vencidos pero el valor real era el conteo de gastos ANULADOS,
    # no de gastos vencidos (DocumentoSoporte no tiene fecha_vencimiento ni
    # estado_pago -- el concepto "vencido" no existe en el modelo de datos
    # real). Renombrado para reflejar lo que el dato realmente es.
    gastos_anulados: int
    gasto_promedio: Decimal


@dataclass(frozen=True)
class WidgetProveedoresDTO:
    """DTO para métricas de Proveedores."""
    total_provedores: int
    total_gastos: Decimal
    cartera_pendiente: Decimal


@dataclass(frozen=True)
class WidgetProyectosDTO:
    """DTO para métricas de Proyectos."""
    total_proyectos: int
    proyectos_activos: int
    tareas_pendientes: int
    tareas_vencidas: int


@dataclass(frozen=True)
class WidgetClientesDTO:
    """DTO para métricas de Clientes."""
    total_clientes: int
    clientes_activos: int
    nuevos_mes: int
    personas_juridicas: int
    retenedores: int


@dataclass(frozen=True)
class KpiSedeDTO:
    """DTO para indicadores transversales por sede."""
    sede_uuid: Optional[str]
    sede_nombre: str
    gastos_total: Decimal
    ingresos_total: Decimal
    proyectos_activos: int
    valor_proyectos: Decimal
    movimientos_inventario: int
    margen: Decimal


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
    proveedores: Optional[WidgetProveedoresDTO] = None
    proyectos: Optional[WidgetProyectosDTO] = None
    clientes: Optional[WidgetClientesDTO] = None
