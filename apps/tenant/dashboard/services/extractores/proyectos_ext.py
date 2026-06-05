"""
Extractor de Proyectos para Dashboard v3.9.5 — datos reales.
Pull Model: usa qs_list de proyectos. No importa models.py directamente.
Modelo Proyecto usa: fase_actual y estado_tarea (no campo 'estado').
"""
from django.utils import timezone

from apps.tenant.dashboard.services.dtos import WidgetProyectosDTO


class ProyectosExtractor:

    @staticmethod
    def extraer_metricas(empresa_id: int) -> WidgetProyectosDTO:
        try:
            from apps.tenant.proyectos.services.selectors import qs_list

            qs = qs_list(empresa_id)
            total_proyectos = qs.count()

            # Activos = estado_tarea no finalizado (FASES no tiene COMPLETADO ni CANCELADO)
            proyectos_activos = qs.exclude(estado_tarea='COMPLETADO').count()

            # Tareas en progreso/pendientes (campo estado_tarea en Proyecto)
            tareas_pendientes = qs.filter(
                estado_tarea__in=['PENDIENTE', 'EN_PROCESO']
            ).count()

            # Proyectos con fecha fin estimada vencida y aún activos
            hoy = timezone.now().date()
            tareas_vencidas = qs.filter(
                fecha_fin_estimada__lt=hoy,
                estado_tarea__in=['PENDIENTE', 'EN_PROCESO'],
            ).count()

            return WidgetProyectosDTO(
                total_proyectos=total_proyectos,
                proyectos_activos=proyectos_activos,
                tareas_pendientes=tareas_pendientes,
                tareas_vencidas=tareas_vencidas,
            )

        except Exception:
            return WidgetProyectosDTO(0, 0, 0, 0)
