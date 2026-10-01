import logging

from django.db import transaction

from apps.tenant.approvals.models import SolicitudAprobacion, SolicitudAprobacionHistorial

logger = logging.getLogger(__name__)


class SolicitudAprobacionCRUDService:
    """Escritura de bajo nivel de SolicitudAprobacion. Toda validacion de
    negocio (transiciones, DSV, revalidacion de snapshot) vive en
    ApprovalBusinessService -- estos metodos asumen que ya fue validada."""

    @staticmethod
    @transaction.atomic
    def crear_solicitud(
        *,
        empresa_id,
        tipo_documento,
        objeto_uuid,
        solicitante,
        snapshot,
        observaciones="",
        prioridad=None,
    ):
        solicitud = SolicitudAprobacion.objects.create(
            empresa_id=empresa_id,
            tipo_documento=tipo_documento,
            objeto_uuid=objeto_uuid,
            solicitante=solicitante,
            snapshot_financiero=snapshot or {},
            observaciones=observaciones or "",
            prioridad=prioridad or SolicitudAprobacion.Prioridad.MEDIA,
        )
        SolicitudAprobacionHistorial.objects.create(
            empresa_id=empresa_id,
            solicitud=solicitud,
            evento=SolicitudAprobacionHistorial.Evento.CREADA,
            estado_anterior="",
            estado_nuevo=SolicitudAprobacion.Estado.PENDIENTE,
            usuario=solicitante,
            snapshot=snapshot or {},
        )
        logger.info(
            "[SolicitudAprobacionCRUD] Creada id=%s tipo=%s objeto=%s",
            solicitud.id,
            tipo_documento,
            objeto_uuid,
        )
        return solicitud

    @staticmethod
    @transaction.atomic
    def cambiar_estado(
        solicitud: SolicitudAprobacion,
        nuevo_estado: str,
        *,
        evento: str,
        usuario=None,
        observacion: str = "",
        snapshot: dict = None,
    ) -> SolicitudAprobacion:
        estado_anterior = solicitud.estado
        solicitud.estado = nuevo_estado
        update_fields = ["estado", "updated_at"]
        if nuevo_estado != SolicitudAprobacion.Estado.PENDIENTE:
            from django.utils import timezone

            solicitud.fecha_decision = timezone.now()
            solicitud.aprobador = usuario
            update_fields += ["fecha_decision", "aprobador"]
        if nuevo_estado == SolicitudAprobacion.Estado.RECHAZADA and observacion:
            solicitud.motivo_rechazo = observacion
            update_fields.append("motivo_rechazo")
        solicitud.save(update_fields=update_fields)

        SolicitudAprobacionHistorial.objects.create(
            empresa_id=solicitud.empresa_id,
            solicitud=solicitud,
            evento=evento,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            usuario=usuario,
            observacion=observacion or "",
            snapshot=snapshot or {},
        )
        logger.info(
            "[SolicitudAprobacionCRUD] estado %s -> %s (id=%s)",
            estado_anterior,
            nuevo_estado,
            solicitud.id,
        )
        return solicitud
