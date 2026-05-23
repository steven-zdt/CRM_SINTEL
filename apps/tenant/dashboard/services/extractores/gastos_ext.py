"""
Extractor de Gastos para Dashboard v3.9.4
Pull Model: Consulta selectors.py de gastos, nunca importa models.py
Zero-Waste: Usa .aggregate() para métricas.
"""
from decimal import Decimal
from datetime import datetime

from django.db.models import Sum, Count
from django.utils import timezone

from apps.tenant.dashboard.services.dtos import WidgetGastosDTO


class GastosExtractor:
    """Extrae métricas de Gastos sin acoplamiento."""

    @staticmethod
    def extraer_metricas(empresa_id: int) -> WidgetGastosDTO:
        """
        Extrae métricas de Gastos usando selectors.py
        Consulta optimizada con .aggregate() — sin N+1.

        Args:
            empresa_id: ID de la empresa (Double Semantic Verification)

        Returns:
            WidgetGastosDTO con métricas consolidadas
        """
        try:
            from apps.tenant.gastos.services.selectors import GastosSelectors

            # Obtener queryset base filtrado por empresa_id (Zero-Trust)
            qs = GastosSelectors.qs_por_empresa(empresa_id)

            hoy = timezone.now().date()
            fecha_inicio_mes = datetime(hoy.year, hoy.month, 1).date()

            # Métrica 1: Total de gastos del mes actual
            gastos_mes = qs.filter(
                fecha__gte=fecha_inicio_mes,
                fecha__lte=hoy,
                estado__in=['APROBADO', 'PAGADO']
            ).aggregate(
                total=Sum('total', output_field=Decimal('0.00'))
            )['total'] or Decimal('0.00')

            # Métrica 2: Gastos pendientes de aprobación
            gastos_pendientes = qs.filter(
                estado='PENDIENTE'
            ).count()

            # Métrica 3: Gastos vencidos (fecha de aprobación pasada)
            gastos_vencidos = qs.filter(
                estado='PENDIENTE',
                fecha__lt=hoy - timezone.timedelta(days=15)
            ).count()

            # Métrica 4: Gasto promedio del mes
            cantidad_gastos = qs.filter(
                fecha__gte=fecha_inicio_mes,
                fecha__lte=hoy,
                estado__in=['APROBADO', 'PAGADO']
            ).count()
            gasto_promedio = gastos_mes / max(cantidad_gastos, 1)

            return WidgetGastosDTO(
                total_gastos_mes=gastos_mes,
                gastos_pendientes=gastos_pendientes,
                gastos_vencidos=gastos_vencidos,
                gasto_promedio=gasto_promedio
            )

        except Exception as e:
            # Retornar valores por defecto si hay error
            return WidgetGastosDTO(
                total_gastos_mes=Decimal('0.00'),
                gastos_pendientes=0,
                gastos_vencidos=0,
                gasto_promedio=Decimal('0.00')
            )
