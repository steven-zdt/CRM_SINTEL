"""
PLAN_REESTRUCTURACION_FASE_3_EJECUCION_FASE_4_CIERRE: orquestacion del
dominio de Fase 4 (Cierre) -- "consolidado final + rentabilidad + tiempos +
documentos" (Seccion 1/69 del plan: "FASE 4 = CONSOLIDAR Y FORMALIZAR").

Agrupa 2 responsabilidades estrechamente relacionadas, mismo criterio ya
usado en inicio_service.py/cotizacion_planeacion_service.py:

- ProyectoCierreGateService    -- bloqueos/gate duro EJECUCION -> CIERRE
                                  (Seccion 22/44 del plan)
- ProyectoCierreResumenService -- "Closure Summary" de solo lectura que
                                  consolida Fases 1-3 (Seccion 27/45: no
                                  duplica datos, solo los agrega)

Decision de diseno (Seccion 53 del plan): NO se crea un modelo
`CierreProyecto` que replique datos de fases anteriores -- este servicio es
un read model puro, calculado on-demand desde las fuentes SSoT ya
existentes (ProyectoInicioResumenService, ProyectoCotizacionPlaneacionService,
TareasDiariasSelector, GastosProyectoService, calcular_ejecucion_tiempo).
"""

from decimal import Decimal

from rest_framework.exceptions import ValidationError

_TWO = Decimal("0.01")


def _q(value) -> Decimal:
    return (value or Decimal("0.00")).quantize(_TWO)


def _margen_pct(base: Decimal, costo: Decimal):
    """None si base==0 (division por cero protegida, mismo criterio que inicio_service._margen_pct)."""
    if not base:
        return None
    return _q((base - costo) / base * Decimal("100"))


class ProyectoCierreGateService:
    """Regla de Oro de Cierre (Seccion 22/44/57 del plan): "No se puede
    cerrar el proyecto con ejecucion incompleta." Gate real en Service
    Layer -- se evalua desde `cambiar_fase_proyecto()` (cubre PATCH generico
    y la accion dedicada avanzar-fase por igual, Seccion 41) y se expone
    tambien de forma anticipada (antes de intentar la transicion) via
    `bloqueos()` para que la UI muestre el checklist en Fase 3 (Seccion 52)."""

    @staticmethod
    def bloqueos(proyecto) -> list[str]:
        """
        Lista de razones por las que el proyecto NO puede cerrarse todavia.
        Lista vacia = listo para cerrar. Evalua el estado ACTUAL del
        proyecto (independiente de en que fase se encuentre) para que el
        checklist de Fase 3 pueda mostrarse en vivo mientras el usuario aun
        esta completando la ejecucion.
        """
        from ..models import TareaDiariaProyecto

        razones = []

        if proyecto.estado_tarea != "COMPLETADO":
            razones.append(
                f"El estado operativo debe ser 'Completado' (actual: {proyecto.get_estado_tarea_display()})."
            )

        if (proyecto.porcentaje_avance or 0) < 100:
            razones.append(f"El avance debe llegar a 100% (actual: {proyecto.porcentaje_avance}%).")

        tareas_abiertas = TareaDiariaProyecto.objects.filter(
            empresa_id=proyecto.empresa_id,
            proyecto=proyecto,
            estado__in=[TareaDiariaProyecto.Estado.PENDIENTE, TareaDiariaProyecto.Estado.EN_PROCESO],
        ).count()
        if tareas_abiertas:
            razones.append(
                f"Existen {tareas_abiertas} tarea(s) pendientes de finalizar."
            )

        if not proyecto.acta_entrega_archivo:
            razones.append("Falta cargar el Acta de Entrega.")

        if not proyecto.informe_final_archivo:
            razones.append("Falta cargar el Informe Final del Proyecto.")

        return razones

    @staticmethod
    def puede_cerrar(proyecto) -> bool:
        return not ProyectoCierreGateService.bloqueos(proyecto)

    @staticmethod
    def validar_o_fallar(proyecto):
        """Invocado desde `business_service.cambiar_fase_proyecto()` en la
        transicion EJECUCION -> CIERRE. Nunca confiar solo en el frontend
        (Seccion 44: 'conceptual, debe implementarse en Service Layer')."""
        bloqueos = ProyectoCierreGateService.bloqueos(proyecto)
        if bloqueos:
            raise ValidationError(
                {
                    "detail": "No se puede cerrar el proyecto: la ejecucion aun no esta completa.",
                    "error": "cierre_bloqueado",
                    "bloqueos_cierre": bloqueos,
                }
            )


class ProyectoCierreResumenService:
    """'Closure Summary' (Seccion 45 del plan): una sola respuesta que
    consolida Fases 1-3 para que Fase 4 sea puramente de lectura (Seccion
    27: 'Cierre solamente consolida'). El frontend NUNCA recalcula estos
    valores (Seccion 36: 'no usar JavaScript como motor financiero')."""

    @staticmethod
    def calcular_resumen(proyecto) -> dict:
        from .cotizacion_planeacion_service import ProyectoCotizacionPlaneacionService
        from .gastos_proyecto_service import GastosProyectoService
        from .inicio_service import ProyectoInicioResumenService
        from .tareas_service import TareasDiariasBusinessService, TareasDiariasSelector
        from . import calcular_ejecucion_tiempo

        inicio = ProyectoInicioResumenService.calcular_resumen(proyecto)
        valor_vendido = Decimal(inicio["facturas_venta"]["valor_vendido_subtotal"])

        cotizacion_resumen = ProyectoCotizacionPlaneacionService.obtener_resumen_cotizacion(proyecto)
        costo_planeado = proyecto.costo_planeado_total or Decimal("0.00")

        # --- Fase 3: tareas (conteos + atraso) ---
        tareas_counts = TareasDiariasSelector.qs_resumen_proyecto(proyecto.empresa_id, proyecto.uuid)
        total_tareas = sum(tareas_counts.values())
        completadas = tareas_counts.get("COMPLETADA", 0)
        atrasadas = sum(
            1
            for t in TareasDiariasSelector.qs_por_proyecto(proyecto.empresa_id, proyecto.uuid)
            if TareasDiariasBusinessService.esta_atrasada(t)
        )
        pct_completitud = round((completadas / total_tareas * 100), 2) if total_tareas else 0

        tiempo = calcular_ejecucion_tiempo(proyecto)
        gastos_nf = GastosProyectoService.get_resumen_gastos_no_facturables(proyecto)

        # --- Rentabilidad final (SSoT: valor vendido real de Fase 1, no el
        # valor_contrato_proyectado aspiracional -- Seccion 35/54 del plan) ---
        costo_real_total = _q(
            (proyecto.costo_mano_obra_real or 0)
            + (proyecto.costo_materiales_real or 0)
            + (proyecto.costo_gastos_real or 0)
        )
        resultado_final = _q(valor_vendido - costo_real_total)
        margen_final = _margen_pct(valor_vendido, costo_real_total)

        # --- Desglose administrativo (Seccion 37: contadores, no otra pantalla) ---
        from apps.tenant.gastos.services.selectors import DocumentoSelector

        try:
            from apps.tenant.compras.services.selectors import OrdenCompraSelector

            ordenes_resumen = OrdenCompraSelector.get_resumen_proyecto(
                proyecto.empresa_id, str(proyecto.uuid)
            )
        except ImportError:
            ordenes_resumen = None

        gastos_count_total = DocumentoSelector.get_by_proyecto(
            proyecto.empresa_id, proyecto.uuid
        ).count()

        bloqueos = ProyectoCierreGateService.bloqueos(proyecto)

        return {
            "inicio": inicio,
            "planeacion": {
                "cotizacion": cotizacion_resumen["cotizacion"] if cotizacion_resumen else None,
                "presupuesto_planeado_total": str(_q(costo_planeado)),
            },
            "ejecucion": {
                "porcentaje_avance": proyecto.porcentaje_avance,
                "estado_tarea": proyecto.estado_tarea,
                "estado_tarea_display": proyecto.get_estado_tarea_display(),
                "tareas": {
                    "total": total_tareas,
                    "pendientes": tareas_counts.get("PENDIENTE", 0),
                    "en_proceso": tareas_counts.get("EN_PROCESO", 0),
                    "completadas": completadas,
                    "canceladas": tareas_counts.get("CANCELADA", 0),
                    "atrasadas": atrasadas,
                    "porcentaje_completitud": pct_completitud,
                },
                "tiempo": tiempo,
                "gastos_no_facturables": gastos_nf,
            },
            "rentabilidad_final": {
                "valor_vendido": str(_q(valor_vendido)),
                "costo_planeado": str(_q(costo_planeado)),
                "costo_real": str(costo_real_total),
                "resultado": str(resultado_final),
                "margen_pct": str(margen_final) if margen_final is not None else None,
            },
            "administrativo": {
                "facturas_venta_count": inicio["facturas_venta"]["count"],
                "ordenes_compra": ordenes_resumen,
                "gastos_count": gastos_count_total,
            },
            "documentos": {
                "contrato": bool(proyecto.contrato_archivo),
                "acta_inicio": bool(proyecto.acta_inicio_archivo),
                "cronograma": bool(proyecto.cronograma_archivo),
                "acta_entrega": bool(proyecto.acta_entrega_archivo),
                "informe_final": bool(proyecto.informe_final_archivo),
            },
            "bloqueos_cierre": bloqueos,
            "puede_cerrar": not bloqueos,
        }
