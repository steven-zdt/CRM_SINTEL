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
