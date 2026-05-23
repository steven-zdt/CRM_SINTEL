"""
Extractor de Facturas para Dashboard v3.9.4
Pull Model: Consulta selectors.py de facturas, nunca importa models.py
Zero-Waste: Usa .aggregate() y .annotate() para métricas.
"""
from datetime import datetime
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.tenant.dashboard.services.dtos import WidgetFacturasDTO


class FacturasExtractor:
    """Extrae métricas de Facturas sin acoplamiento."""

    @staticmethod
    def extraer_metricas(empresa_id: int) -> WidgetFacturasDTO:
        """
        Extrae métricas de Facturas usando selectors.py
        Consulta optimizada con .aggregate() — sin N+1.

        Args:
            empresa_id: ID de la empresa (Double Semantic Verification)

        Returns:
            WidgetFacturasDTO con métricas consolidadas
        """
        try:
            # Importar solo el selector, no el modelo
            from apps.tenant.facturas.services.selectors import FacturaSelectors

            # Obtener queryset base filtrado por empresa_id (Zero-Trust)
            qs = FacturaSelectors.qs_por_empresa(empresa_id)

            # Métrica 1: Total de Facturas
            total_facturas = qs.count()

            # Métrica 2: Facturas Pendientes (estado != PAGADA)
            facturas_pendientes = qs.exclude(estado_pago='PAGADA').count()

            # Métrica 3: Facturas Vencidas (fecha_vencimiento < hoy)
            hoy = timezone.now().date()
            facturas_vencidas = qs.filter(
                fecha_vencimiento__lt=hoy,
                estado_pago__in=['PENDIENTE', 'PARCIAL']
            ).count()

            # Métrica 4 & 5: Ingresos totales del mes
            fecha_inicio_mes = datetime(hoy.year, hoy.month, 1).date()
            ingresos_mes = qs.filter(
                fecha_emision__gte=fecha_inicio_mes,
                fecha_emision__lte=hoy,
                estado='ACEPTADA'
            ).aggregate(total=Sum('total', output_field=Decimal('0.00')))['total'] or Decimal('0.00')

            # Promedio de ingresos por factura
            ingresos_promedio = ingresos_mes / max(total_facturas, 1)

            return WidgetFacturasDTO(
                total_facturas=total_facturas,
                facturas_pendientes=facturas_pendientes,
                facturas_vencidas=facturas_vencidas,
                ingresos_mes=ingresos_mes,
                ingresos_promedio=ingresos_promedio
            )

        except Exception as e:
            # Retornar valores por defecto si hay error
            return WidgetFacturasDTO(
                total_facturas=0,
                facturas_pendientes=0,
                facturas_vencidas=0,
                ingresos_mes=Decimal('0.00'),
                ingresos_promedio=Decimal('0.00')
            )

    @staticmethod
    def qs_por_empresa(empresa_id: int):
        """Helper para obtener queryset base."""
        try:
            from apps.tenant.facturas.services.selectors import FacturaSelectors
            return FacturaSelectors.qs_por_empresa(empresa_id)
        except (AttributeError, ImportError):
            # Fallback: si el selector no existe, retornar empty queryset
            from django.db.models import QuerySet
            return QuerySet().none()
