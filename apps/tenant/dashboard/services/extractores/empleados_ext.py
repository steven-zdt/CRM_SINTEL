"""
Extractor de Empleados para Dashboard v3.9.4
Pull Model: Consulta selectors.py de empleados, nunca importa models.py
Zero-Waste: Usa .aggregate() para nóminas y headcount.
"""
from decimal import Decimal
from datetime import datetime

from django.db.models import Count, Sum, Q
from django.utils import timezone

from apps.tenant.dashboard.services.dtos import WidgetEmpleadosDTO


class EmpleadosExtractor:
    """Extrae métricas de Empleados (Contratos + Nóminas)."""

    @staticmethod
    def extraer_metricas(empresa_id: int) -> WidgetEmpleadosDTO:
        """
        Extrae métricas de Empleados: headcount, nóminas pendientes, liquidación.

        Args:
            empresa_id: ID de la empresa (Double Semantic Verification)

        Returns:
            WidgetEmpleadosDTO con métricas consolidadas
        """
        try:
            from apps.tenant.empleados.services.selectors import EmpleadosSelectors

            # Métrica 1: Total de empleados registrados
            total_empleados = EmpleadosSelectors.qs_empleados(empresa_id).count()

            # Métrica 2: Empleados con contrato activo (ACTIVO no INACTIVO/HISTORICO)
            empleados_activos = EmpleadosSelectors.qs_empleados(empresa_id).filter(
                contrato__estado='ACTIVO'
            ).distinct().count()

            # Métrica 3: Nóminas pendientes (aquellas sin estado PAGADA)
            try:
                nominas_qs = EmpleadosSelectors.qs_devengos(empresa_id)
                nominas_pendientes = nominas_qs.exclude(estado='PAGADA').count()
            except:
                nominas_pendientes = 0

            # Métrica 4: Total de nómina del mes
            hoy = timezone.now().date()
            fecha_inicio_mes = datetime(hoy.year, hoy.month, 1).date()

            try:
                nominas_mes = EmpleadosSelectors.qs_devengos(empresa_id).filter(
                    fecha_liquidacion__gte=fecha_inicio_mes,
                    fecha_liquidacion__lte=hoy
                ).aggregate(
                    total=Sum('total_liquido', output_field=Decimal('0.00'))
                )['total'] or Decimal('0.00')
            except:
                nominas_mes = Decimal('0.00')

            return WidgetEmpleadosDTO(
                total_empleados=total_empleados,
                empleados_activos=empleados_activos,
                nominas_pendientes=nominas_pendientes,
                total_nómina_mes=nominas_mes
            )

        except Exception as e:
            return WidgetEmpleadosDTO(
                total_empleados=0,
                empleados_activos=0,
                nominas_pendientes=0,
                total_nómina_mes=Decimal('0.00')
            )
