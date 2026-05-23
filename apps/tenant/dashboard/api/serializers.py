"""
Serializadores DRF para el dashboard de tenants.

WARNING: v2.30: API-First - Todos los datos del dashboard se exponen vía JSON.
"""
from rest_framework import serializers


class DashboardKPI(serializers.Serializer):
    """Serializer para un KPI del dashboard."""
    label = serializers.CharField()
    value = serializers.FloatField()
    delta = serializers.FloatField(required=False, allow_null=True)


class DashboardSeriesPoint(serializers.Serializer):
    """Serializer para un punto de una serie."""
    x = serializers.CharField()  # o DateTimeField si hay fechas
    y = serializers.FloatField()


class DashboardSeries(serializers.Serializer):
    """Serializer para una serie de datos."""
    name = serializers.CharField()
    points = DashboardSeriesPoint(many=True)


class DashboardTableRow(serializers.Serializer):
    """Serializer para una fila de la tabla."""
    id = serializers.IntegerField()
    name = serializers.CharField()
    amount = serializers.FloatField()
    status = serializers.CharField()


class DashboardTable(serializers.Serializer):
    """Serializer para la tabla del dashboard."""
    columns = serializers.ListField(child=serializers.CharField())
    rows = DashboardTableRow(many=True)


class DashboardPayload(serializers.Serializer):
    """
    Contrato canónico para el payload completo del dashboard.
    
    WARNING: API-First: Este serializer define el contrato estable de datos del dashboard.
    Todos los datos se obtienen vía JSON desde este endpoint.
    """
    header = serializers.DictField(child=serializers.CharField(), required=False)
    kpis = DashboardKPI(many=True)
    series = DashboardSeries(many=True)
    table = DashboardTable()


# Serializers legacy (mantener por compatibilidad)
class DashboardSummarySerializer(serializers.Serializer):
    """
    Serializador para el resumen del dashboard (legacy).
    
    WARNING: DEPRECADO: Usar DashboardPayload en su lugar.
    """
    tenant = serializers.DictField(read_only=True)
    user = serializers.DictField(read_only=True)
    user_role = serializers.CharField(read_only=True)
    kpis = serializers.DictField(read_only=True)
    redirect_url = serializers.CharField(read_only=True)
    branding = serializers.DictField(read_only=True)


class KPISerializer(serializers.Serializer):
    """
    Serializador para KPIs del dashboard (legacy).
    
    WARNING: DEPRECADO: Usar DashboardPayload en su lugar.
    """
    total_facturas = serializers.IntegerField(read_only=True)
    facturas_pendientes = serializers.IntegerField(read_only=True)
    total_clientes = serializers.IntegerField(read_only=True)
    ingresos_mes = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)


class QuickActionSerializer(serializers.Serializer):
    """
    Serializador para acciones rápidas del dashboard (legacy).
    """
    id = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    url = serializers.CharField(read_only=True)
    icon = serializers.CharField(read_only=True, required=False)
    color = serializers.CharField(read_only=True, required=False)
    required_role = serializers.CharField(read_only=True, required=False)


# --- Serializers v3.9.4 --- Pull Model DTOs ---


class WidgetFacturasSerializer(serializers.Serializer):
    """Serializer para métricas de Facturas (WidgetFacturasDTO)."""
    total_facturas = serializers.IntegerField()
    facturas_pendientes = serializers.IntegerField()
    facturas_vencidas = serializers.IntegerField()
    ingresos_mes = serializers.DecimalField(max_digits=15, decimal_places=2)
    ingresos_promedio = serializers.DecimalField(max_digits=15, decimal_places=2)


class WidgetInventarioSerializer(serializers.Serializer):
    """Serializer para métricas de Inventario (WidgetInventarioDTO)."""
    total_productos = serializers.IntegerField()
    productos_bajo_stock = serializers.IntegerField()
    movimientos_mes = serializers.IntegerField()
    valor_inventario = serializers.DecimalField(max_digits=15, decimal_places=2)
    rotacion_promedio = serializers.DecimalField(max_digits=15, decimal_places=2)


class WidgetEmpleadosSerializer(serializers.Serializer):
    """Serializer para métricas de Empleados (WidgetEmpleadosDTO)."""
    total_empleados = serializers.IntegerField()
    empleados_activos = serializers.IntegerField()
    nominas_pendientes = serializers.IntegerField()
    total_nómina_mes = serializers.DecimalField(max_digits=15, decimal_places=2)


class WidgetGastosSerializer(serializers.Serializer):
    """Serializer para métricas de Gastos (WidgetGastosDTO)."""
    total_gastos_mes = serializers.DecimalField(max_digits=15, decimal_places=2)
    gastos_pendientes = serializers.IntegerField()
    gastos_vencidos = serializers.IntegerField()
    gasto_promedio = serializers.DecimalField(max_digits=15, decimal_places=2)


class WidgetProyectosSerializer(serializers.Serializer):
    """Serializer para métricas de Proyectos (WidgetProyectosDTO)."""
    total_proyectos = serializers.IntegerField()
    proyectos_activos = serializers.IntegerField()
    tareas_pendientes = serializers.IntegerField()
    tareas_vencidas = serializers.IntegerField()


class DashboardMetricasSerializer(serializers.Serializer):
    """
    Serializer principal para DashboardMetricasDTO v3.9.4.
    Contrato canónico para métricas consolidadas (Pull Model).
    """
    empresa_nombre = serializers.CharField()
    empresa_nit = serializers.CharField()
    fecha_actualizacion = serializers.DateTimeField()
    facturas = WidgetFacturasSerializer()
    inventario = WidgetInventarioSerializer()
    empleados = WidgetEmpleadosSerializer()
    gastos = WidgetGastosSerializer(required=False, allow_null=True)
    proyectos = WidgetProyectosSerializer(required=False, allow_null=True)
