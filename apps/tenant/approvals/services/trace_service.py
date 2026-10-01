"""
ApprovalTraceService -- Fase 6 de PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md
(#16): servicio de SOLO LECTURA que construye la ruta visual (grafo +
timeline + resumen financiero) de una SolicitudAprobacion.

    Solicitud
      -> resolver documentos relacionados
      -> construir nodos
      -> construir relaciones
      -> calcular resumen
      -> retornar DTO

Nunca escribe en dominios ajenos -- solo resuelve, agrega y retorna un dict
plano (JSON-serializable) con el contrato exacto del plan:
{request, origin, nodes, relations, timeline, financial_summary, alerts}.

Unico tipo_documento soportado hoy: REQUISICION (el unico que existe en el
registry de ApprovalBusinessService). Agregar COTIZACION/ORDEN_COMPRA en el
futuro es una rama nueva en `construir_trazabilidad()`, sin tocar el
contrato del DTO.

Sin API/UI todavia -- el grafo visual interactivo (nodos clicables que
abren cada documento via Offcanvas) es Fase 9, DEFERRED.
"""

from apps.tenant.approvals.models import SolicitudAprobacion


def _serializar_solicitud(solicitud) -> dict:
    return {
        "uuid": str(solicitud.uuid),
        "tipo_documento": solicitud.tipo_documento,
        "estado": solicitud.estado,
        "prioridad": solicitud.prioridad,
        "solicitante": str(solicitud.solicitante) if solicitud.solicitante_id else None,
        "aprobador": str(solicitud.aprobador) if solicitud.aprobador_id else None,
        "fecha_envio": solicitud.fecha_envio.isoformat() if solicitud.fecha_envio else None,
        "fecha_decision": solicitud.fecha_decision.isoformat()
        if solicitud.fecha_decision
        else None,
        "motivo_rechazo": solicitud.motivo_rechazo,
        "observaciones": solicitud.observaciones,
    }


def _dto_vacio(solicitud) -> dict:
    return {
        "request": _serializar_solicitud(solicitud),
        "origin": None,
        "nodes": [],
        "relations": [],
        "timeline": [],
        "financial_summary": {},
        "alerts": [],
    }


class ApprovalTraceService:
    @staticmethod
    def construir_trazabilidad(solicitud: SolicitudAprobacion, empresa_id: int) -> dict:
        if solicitud.tipo_documento == SolicitudAprobacion.TipoDocumento.REQUISICION:
            return ApprovalTraceService._trazabilidad_requisicion(solicitud, empresa_id)
        return _dto_vacio(solicitud)

    @staticmethod
    def _trazabilidad_requisicion(solicitud: SolicitudAprobacion, empresa_id: int) -> dict:
        from apps.tenant.compras.models import OrdenCompraRequisicion
        from apps.tenant.compras.requisiciones.models import RequisicionCompra
        from apps.tenant.compras.services.budget_control_service import (
            ProcurementBudgetControlService,
        )

        dto = _dto_vacio(solicitud)

        requisicion = (
            RequisicionCompra.objects.filter(
                uuid=solicitud.objeto_uuid,
                empresa_id=empresa_id,
            )
            .select_related("proyecto")
            .first()
        )
        if not requisicion:
            return dto

        nodo_requisicion = {
            "tipo": "REQUISICION",
            "uuid": str(requisicion.uuid),
            "numero": requisicion.numero_documento,
            "estado": requisicion.estado,
            "valor": str(requisicion.total_estimado),
            "fecha": requisicion.fecha_solicitud.isoformat()
            if requisicion.fecha_solicitud
            else None,
        }
        dto["nodes"].append(nodo_requisicion)
        dto["origin"] = nodo_requisicion

        # Cotizacion de origen (ver RequisicionCotizacion, tipo_relacion='ORIGEN').
        cotizacion = None
        vinculo_origen = (
            requisicion.cotizaciones_vinculadas.filter(tipo_relacion="ORIGEN")
            .select_related("cotizacion")
            .first()
        )
        if vinculo_origen:
            cotizacion = vinculo_origen.cotizacion
            nodo_cotizacion = {
                "tipo": "COTIZACION",
                "uuid": str(cotizacion.uuid),
                "numero": cotizacion.numero_cotizacion,
                "estado": cotizacion.estado,
                "valor": str(cotizacion.total_con_impuestos),
                "fecha": None,
            }
            dto["nodes"].append(nodo_cotizacion)
            dto["relations"].append(
                {"from": nodo_cotizacion["uuid"], "to": nodo_requisicion["uuid"], "tipo": "ORIGEN"}
            )

        # Proyecto (contexto, opcional).
        if requisicion.proyecto_id:
            proyecto = requisicion.proyecto
            nodo_proyecto = {
                "tipo": "PROYECTO",
                "uuid": str(proyecto.uuid),
                "numero": proyecto.nombre,
                "estado": proyecto.fase_actual,
                "valor": str(proyecto.valor_contrato_proyectado),
                "fecha": None,
            }
            dto["nodes"].append(nodo_proyecto)
            dto["relations"].append(
                {"from": nodo_proyecto["uuid"], "to": nodo_requisicion["uuid"], "tipo": "CONTEXTO"}
            )

        # Ordenes de Compra generadas (N:N, ver OrdenCompraRequisicion).
        for vinculo_oc in OrdenCompraRequisicion.objects.filter(
            empresa_id=empresa_id,
            requisicion=requisicion,
        ).select_related("orden_compra"):
            oc = vinculo_oc.orden_compra
            nodo_oc = {
                "tipo": "ORDEN_COMPRA",
                "uuid": str(oc.uuid),
                "numero": oc.numero_documento,
                "estado": oc.estado,
                "valor": str(vinculo_oc.monto_asignado),
                "fecha": oc.fecha.isoformat() if oc.fecha else None,
            }
            dto["nodes"].append(nodo_oc)
            dto["relations"].append(
                {"from": nodo_requisicion["uuid"], "to": nodo_oc["uuid"], "tipo": "GENERA"}
            )

        # Timeline: merge de 2 fuentes reales de historial append-only, sin
        # inventar un tercer modelo de eventos.
        eventos = []
        for h in solicitud.historial.all():
            eventos.append(
                {
                    "fuente": "SOLICITUD",
                    "evento": h.evento,
                    "estado_anterior": h.estado_anterior,
                    "estado_nuevo": h.estado_nuevo,
                    "usuario": str(h.usuario) if h.usuario_id else None,
                    "fecha": h.created_at.isoformat(),
                    "observacion": h.observacion,
                }
            )
        for h in requisicion.historial_estados.all():
            eventos.append(
                {
                    "fuente": "REQUISICION",
                    "evento": h.estado_nuevo,
                    "estado_anterior": h.estado_anterior,
                    "estado_nuevo": h.estado_nuevo,
                    "usuario": str(h.usuario) if h.usuario_id else None,
                    "fecha": h.created_at.isoformat(),
                    "observacion": h.comentario,
                }
            )
        dto["timeline"] = sorted(eventos, key=lambda e: e["fecha"])

        # Resumen financiero (#17 del plan) -- unica fuente de calculo real:
        # ProcurementBudgetControlService, nunca reimplementado aqui.
        saldo_requisicion = ProcurementBudgetControlService.obtener_saldo_requisicion(requisicion)
        resumen = {
            "valor_requisicion": str(requisicion.total_estimado),
            "comprometido_requisicion": str(requisicion.total_estimado - saldo_requisicion),
            "saldo_requisicion": str(saldo_requisicion),
        }
        alerts = []
        if saldo_requisicion < 0:
            alerts.append(
                {
                    "nivel": "ROJO",
                    "mensaje": f"Las ordenes de compra generadas superan el valor estimado de la requisicion en ${-saldo_requisicion:,.2f}.",
                }
            )
        if cotizacion:
            saldo_cotizacion = ProcurementBudgetControlService.obtener_saldo_cotizacion(cotizacion)
            resumen["valor_cotizacion"] = str(cotizacion.total_con_impuestos)
            resumen["saldo_cotizacion"] = str(saldo_cotizacion)
            if saldo_cotizacion < 0:
                alerts.append(
                    {
                        "nivel": "ROJO",
                        "mensaje": f"Las requisiciones de la cotizacion {cotizacion.numero_cotizacion} superan el valor autorizado en ${-saldo_cotizacion:,.2f}.",
                    }
                )
        dto["financial_summary"] = resumen
        dto["alerts"] = alerts

        return dto
