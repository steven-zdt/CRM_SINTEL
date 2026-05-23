"""
Extractor de Proyectos para Dashboard v3.9.4
Pull Model: Consulta selectors.py de proyectos, nunca importa models.py
Zero-Waste: Usa .aggregate() para métricas.
"""
from django.db.models import Count, Q
from django.utils import timezone

from apps.tenant.dashboard.services.dtos import WidgetProyectosDTO


class ProyectosExtractor:
    """Extrae métricas de Proyectos sin acoplamiento."""

    @staticmethod
    def extraer_metricas(empresa_id: int) -> WidgetProyectosDTO:
        """
        Extrae métricas de Proyectos usando selectors.py
        Incluye estado de proyectos y tareas.

        Args:
            empresa_id: ID de la empresa (Double Semantic Verification)

        Returns:
            WidgetProyectosDTO con métricas consolidadas
        """
        try:
            from apps.tenant.proyectos.services.selectors import ProyectosSelectors

            # Obtener queryset base (Proyectos)
            qs_proyectos = ProyectosSelectors.qs_por_empresa(empresa_id)

            # Métrica 1: Total de proyectos
            total_proyectos = qs_proyectos.count()

            # Métrica 2: Proyectos activos (estado != COMPLETADO)
            proyectos_activos = qs_proyectos.exclude(
                estado__in=['COMPLETADO', 'CANCELADO']
            ).count()

            # Métrica 3 & 4: Tareas pendientes y vencidas
            try:
                qs_tareas = ProyectosSelectors.qs_tareas_por_empresa(empresa_id)
                hoy = timezone.now().date()

                tareas_pendientes = qs_tareas.filter(
                    estado__in=['PENDIENTE', 'EN_PROGRESO']
                ).count()

                tareas_vencidas = qs_tareas.filter(
                    estado__in=['PENDIENTE', 'EN_PROGRESO'],
                    fecha_fin__lt=hoy
                ).count()
            except:
                tareas_pendientes = 0
                tareas_vencidas = 0

            return WidgetProyectosDTO(
                total_proyectos=total_proyectos,
                proyectos_activos=proyectos_activos,
                tareas_pendientes=tareas_pendientes,
                tareas_vencidas=tareas_vencidas
            )

        except Exception as e:
            # Retornar valores por defecto si hay error
            return WidgetProyectosDTO(
                total_proyectos=0,
                proyectos_activos=0,
                tareas_pendientes=0,
                tareas_vencidas=0
            )
