"""
ApprovalBusinessService -- motor generico de Solicitudes de Aprobacion.

Fases 1-4 de PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md construyeron el
motor sin enganche real. **Fase 5 (2026-09-26)** lo conecta:
`RequisicionCompraBusinessService.enviar_a_aprobacion()` ahora crea la
`SolicitudAprobacion` real (ver ese metodo). Sin API/UI todavia (Fase 7/8).

Regla de oro (#26 del plan): NUNCA `objeto.estado = "APROBADA"` directo desde
aqui. Este servicio solo orquesta el ciclo de vida de la SolicitudAprobacion
en si misma y DELEGA la transicion real al BusinessService del dominio
correspondiente (resuelto via el registry).
"""

import logging
from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.tenant.approvals.models import SolicitudAprobacion, SolicitudAprobacionHistorial
from apps.tenant.approvals.services.crud_service import SolicitudAprobacionCRUDService

logger = logging.getLogger(__name__)

# Fase 8 del plan (banner/bandeja del Centro de Aprobaciones): umbrales de
# riesgo presupuestal, expresados como % de la Cotizacion de origen ya
# comprometido por Requisiciones activas AL MOMENTO DE ENVIAR a aprobacion
# (congelado en el snapshot, igual criterio que el resto de #13 -- revalidado
# en aprobar()). Constante de backend documentada, nunca hardcodeada en JS
# (#34 del plan).
RIESGO_UMBRAL_ALTO = Decimal("0.90")
RIESGO_UMBRAL_MEDIO = Decimal("0.60")


def _resolver_requisicion(objeto_uuid, empresa_id):
    from apps.tenant.compras.requisiciones.models import RequisicionCompra

    return RequisicionCompra.objects.filter(uuid=objeto_uuid, empresa_id=empresa_id).first()


def _aprobar_requisicion(objeto_uuid, empresa_id, usuario, observacion):
    from apps.tenant.compras.requisiciones.services.business_service import (
        RequisicionCompraBusinessService,
    )

    return RequisicionCompraBusinessService.aprobar_requisicion(
        str(objeto_uuid), empresa_id, usuario=usuario, comentario=observacion
    )


def _rechazar_requisicion(objeto_uuid, empresa_id, usuario, motivo):
    from apps.tenant.compras.requisiciones.services.business_service import (
        RequisicionCompraBusinessService,
    )

    return RequisicionCompraBusinessService.rechazar_requisicion(
        str(objeto_uuid), empresa_id, motivo, usuario=usuario
    )


def _calcular_riesgo_requisicion(requisicion) -> tuple[str, Decimal | None]:
    """Fase 8 (#34 del plan): prioridad/riesgo real, nunca inventado en el
    frontend. % = cuanto de la Cotizacion de origen ya esta comprometido por
    TODAS sus Requisiciones activas (incluyendo esta), en el momento del
    envio -- una Requisicion que satura el presupuesto de su Cotizacion es
    mas critica que una con margen amplio, independientemente de su propio
    valor absoluto. Sin Cotizacion de origen o Cotizacion sin total: BAJA
    (nada que medir), consistente con no inventar un heuristico distinto."""
    from apps.tenant.compras.services.budget_control_service import ProcurementBudgetControlService

    origen = (
        requisicion.cotizaciones_vinculadas.filter(tipo_relacion="ORIGEN")
        .select_related("cotizacion")
        .first()
    )
    if not origen or not origen.cotizacion.total_con_impuestos:
        return SolicitudAprobacion.Prioridad.BAJA, None

    cotizacion = origen.cotizacion
    saldo = ProcurementBudgetControlService.obtener_saldo_cotizacion(cotizacion)
    comprometido = cotizacion.total_con_impuestos - saldo
    pct = (comprometido / cotizacion.total_con_impuestos).quantize(Decimal("0.01"))

    if pct >= RIESGO_UMBRAL_ALTO:
        return SolicitudAprobacion.Prioridad.ALTA, pct
    if pct >= RIESGO_UMBRAL_MEDIO:
        return SolicitudAprobacion.Prioridad.MEDIA, pct
    return SolicitudAprobacion.Prioridad.BAJA, pct


def _snapshot_requisicion(requisicion) -> dict:
    """#13 del plan: "al enviar para aprobacion guardar resumen de control:
    valor, numero, tipo, documento origen, cotizacion, proyecto, cantidad de
    lineas, version/hash". Todos los valores como str/int planos (JSONField)
    -- se compara por igualdad de dict completo en vez de un hash separado
    (mismo efecto, sin una dependencia extra). Fase 8: agrega `riesgo_pct`
    (ver `_calcular_riesgo_requisicion`) -- consumido por la bandeja del
    Centro de Aprobaciones sin recalcular nada en el frontend."""
    origen = requisicion.cotizaciones_vinculadas.filter(tipo_relacion="ORIGEN").first()
    _, riesgo_pct = _calcular_riesgo_requisicion(requisicion)
    return {
        "valor": str(requisicion.total_estimado),
        "numero": requisicion.numero_documento,
        "tipo": requisicion.tipo,
        "documento_origen": "REQUISICION",
        "cotizacion_uuid": str(origen.cotizacion.uuid) if origen else None,
        "cotizacion_numero": origen.cotizacion.numero_cotizacion if origen else None,
        "proyecto_id": requisicion.proyecto_id,
        "proyecto_nombre": requisicion.proyecto.nombre if requisicion.proyecto_id else None,
        # PLAN_NUEVA_REQUISICION_NUMERACION_CLIENTE_COTIZACIONES.md #31: el
        # snapshot de aprobacion debe incluir cliente y plantilla (ahora
        # obligatorios, Fases B/C) -- se congelan aqui igual que
        # proyecto_id/proyecto_nombre; si cambian despues del envio,
        # ApprovalBusinessService.aprobar() ya revalida snapshot vs. estado
        # actual del documento (#13 del plan original) y bloquea.
        "cliente_id": requisicion.cliente_id,
        "cliente_nombre": requisicion.cliente.razon_social if requisicion.cliente_id else None,
        "plantilla_id": requisicion.plantilla_id,
        "plantilla_nombre": requisicion.plantilla.nombre if requisicion.plantilla_id else None,
        "cantidad_lineas": requisicion.items.count(),
        "riesgo_pct": str(riesgo_pct) if riesgo_pct is not None else None,
    }


def _calcular_prioridad_requisicion(requisicion) -> str:
    prioridad, _ = _calcular_riesgo_requisicion(requisicion)
    return prioridad


# Registry explicito (#9 del plan: "Preferir un registry explicito", nunca
# GenericForeignKey). Extensible a COTIZACION/ORDEN_COMPRA sin tocar el
# modelo SolicitudAprobacion ni el resto de este servicio -- solo se agrega
# una entrada nueva aqui.
TIPO_DOCUMENTO_REGISTRY = {
    SolicitudAprobacion.TipoDocumento.REQUISICION: {
        "resolver": _resolver_requisicion,
        "aprobar": _aprobar_requisicion,
        "rechazar": _rechazar_requisicion,
        "snapshot": _snapshot_requisicion,
        "prioridad": _calcular_prioridad_requisicion,
    },
}


class ApprovalBusinessService:
    @staticmethod
    @transaction.atomic
    def crear_solicitud(
        *,
        tipo_documento: str,
        objeto_uuid,
        empresa_id: int,
        solicitante,
        snapshot: dict | None = None,
        observaciones: str = "",
    ) -> tuple[bool, Any, int]:
        """Crea (o reutiliza, si ya hay una PENDIENTE) la solicitud de
        aprobacion de un documento real. DSV: el documento debe existir y
        pertenecer a la empresa antes de crear nada. `snapshot`: si no se
        provee explicito, se calcula via `entry['snapshot'](objeto)` del
        registry (#13 del plan) -- el caller real
        (RequisicionCompraBusinessService.enviar_a_aprobacion()) no necesita
        conocer el formato del snapshot de Approvals."""
        entry = TIPO_DOCUMENTO_REGISTRY.get(tipo_documento)
        if not entry:
            return (
                False,
                {
                    "error": "tipo_documento_invalido",
                    "message": f"Tipo de documento no soportado: {tipo_documento}.",
                },
                400,
            )

        objeto = entry["resolver"](objeto_uuid, empresa_id)
        if not objeto:
            return (
                False,
                {
                    "error": "documento_invalido",
                    "message": "El documento no existe o no pertenece a la empresa.",
                },
                400,
            )

        existente = (
            SolicitudAprobacion.objects.select_for_update()
            .filter(
                empresa_id=empresa_id,
                tipo_documento=tipo_documento,
                objeto_uuid=objeto_uuid,
                estado=SolicitudAprobacion.Estado.PENDIENTE,
            )
            .first()
        )
        if existente:
            return True, existente, 200

        if snapshot is None:
            snapshot_fn = entry.get("snapshot")
            snapshot = snapshot_fn(objeto) if snapshot_fn else {}

        prioridad_fn = entry.get("prioridad")
        prioridad = prioridad_fn(objeto) if prioridad_fn else SolicitudAprobacion.Prioridad.MEDIA

        solicitud = SolicitudAprobacionCRUDService.crear_solicitud(
            empresa_id=empresa_id,
            tipo_documento=tipo_documento,
            objeto_uuid=objeto_uuid,
            solicitante=solicitante,
            snapshot=snapshot,
            observaciones=observaciones,
            prioridad=prioridad,
        )
        return True, solicitud, 201

    @staticmethod
    @transaction.atomic
    def aprobar(
        solicitud_uuid: str, empresa_id: int, aprobador, observacion: str = ""
    ) -> tuple[bool, Any, int]:
        """Revalida estado PENDIENTE + snapshot vs. estado actual del
        documento real (#13: si cambio, bloquea) y delega la transicion real
        al BusinessService del dominio (#26) -- nunca escribe el estado
        directo. select_for_update() sobre la solicitud para idempotencia
        bajo concurrencia (#28: doble aprobacion nunca duplica efectos)."""
        solicitud = (
            SolicitudAprobacion.objects.select_for_update()
            .filter(
                uuid=solicitud_uuid,
                empresa_id=empresa_id,
            )
            .first()
        )
        if not solicitud:
            return (
                False,
                {"error": "solicitud_no_encontrada", "message": "La solicitud no existe."},
                404,
            )

        if solicitud.estado != SolicitudAprobacion.Estado.PENDIENTE:
            return True, solicitud, 200

        entry = TIPO_DOCUMENTO_REGISTRY.get(solicitud.tipo_documento)
        if not entry:
            return (
                False,
                {
                    "error": "tipo_documento_invalido",
                    "message": f"Tipo de documento no soportado: {solicitud.tipo_documento}.",
                },
                400,
            )

        # #13 del plan: revalidar snapshot antes de aprobar -- recarga el
        # documento real, recalcula, compara. Si cambio desde el envio,
        # BLOQUEA (nunca aprueba "a ciegas" un documento distinto al que se
        # reviso). Solo aplica si el snapshot fue capturado (dict no vacio) --
        # una solicitud creada sin snapshot explicito no tiene nada que
        # comparar.
        if solicitud.snapshot_financiero and entry.get("snapshot"):
            objeto_actual = entry["resolver"](solicitud.objeto_uuid, empresa_id)
            if not objeto_actual:
                return (
                    False,
                    {
                        "error": "documento_invalido",
                        "message": "El documento ya no existe o no pertenece a la empresa.",
                    },
                    400,
                )
            snapshot_actual = entry["snapshot"](objeto_actual)
            if snapshot_actual != solicitud.snapshot_financiero:
                return (
                    False,
                    {
                        "error": "documento_modificado",
                        "message": "El documento cambio despues de ser enviado a aprobacion. Debe revisarse y reenviarse.",
                    },
                    409,
                )

        ok, result, status_code = entry["aprobar"](
            solicitud.objeto_uuid, empresa_id, aprobador, observacion
        )
        if not ok:
            return False, result, status_code

        # El BusinessService del dominio (ej. RequisicionCompraBusinessService.
        # aprobar_requisicion()) ya cierra su propia SolicitudAprobacion
        # PENDIENTE como parte de la transicion real -- se re-verifica en vez
        # de volver a escribir siempre, para nunca duplicar el historial. Si
        # el dominio todavia no implementa ese cierre (fallback), se cierra
        # aqui.
        solicitud.refresh_from_db()
        if solicitud.estado == SolicitudAprobacion.Estado.PENDIENTE:
            SolicitudAprobacionCRUDService.cambiar_estado(
                solicitud,
                SolicitudAprobacion.Estado.APROBADA,
                evento=SolicitudAprobacionHistorial.Evento.APROBADA,
                usuario=aprobador,
                observacion=observacion,
            )
            solicitud.refresh_from_db()
        return True, solicitud, 200

    @staticmethod
    @transaction.atomic
    def rechazar(
        solicitud_uuid: str, empresa_id: int, aprobador, motivo: str
    ) -> tuple[bool, Any, int]:
        if not (motivo or "").strip():
            return (
                False,
                {"error": "motivo_requerido", "message": "Debe indicar el motivo de rechazo."},
                422,
            )

        solicitud = (
            SolicitudAprobacion.objects.select_for_update()
            .filter(
                uuid=solicitud_uuid,
                empresa_id=empresa_id,
            )
            .first()
        )
        if not solicitud:
            return (
                False,
                {"error": "solicitud_no_encontrada", "message": "La solicitud no existe."},
                404,
            )

        if solicitud.estado != SolicitudAprobacion.Estado.PENDIENTE:
            return True, solicitud, 200

        entry = TIPO_DOCUMENTO_REGISTRY.get(solicitud.tipo_documento)
        if not entry:
            return (
                False,
                {
                    "error": "tipo_documento_invalido",
                    "message": f"Tipo de documento no soportado: {solicitud.tipo_documento}.",
                },
                400,
            )

        ok, result, status_code = entry["rechazar"](
            solicitud.objeto_uuid, empresa_id, aprobador, motivo
        )
        if not ok:
            return False, result, status_code

        # Mismo criterio que en aprobar() -- evita duplicar el historial si
        # el dominio ya cerro su propia solicitud.
        solicitud.refresh_from_db()
        if solicitud.estado == SolicitudAprobacion.Estado.PENDIENTE:
            SolicitudAprobacionCRUDService.cambiar_estado(
                solicitud,
                SolicitudAprobacion.Estado.RECHAZADA,
                evento=SolicitudAprobacionHistorial.Evento.RECHAZADA,
                usuario=aprobador,
                observacion=motivo,
            )
            solicitud.refresh_from_db()
        return True, solicitud, 200
