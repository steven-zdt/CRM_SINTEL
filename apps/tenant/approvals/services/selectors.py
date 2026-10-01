from decimal import Decimal, InvalidOperation

from django.utils import timezone

from apps.tenant.approvals.models import SolicitudAprobacion

SOLICITUD_LIST_FIELDS = (
    "id",
    "uuid",
    "tipo_documento",
    "objeto_uuid",
    "estado",
    "prioridad",
    "fecha_envio",
    "fecha_decision",
    "empresa_id",
    "solicitante_id",
    "aprobador_id",
    "snapshot_financiero",
)


class SolicitudAprobacionSelector:
    """Selectores de solo lectura."""

    @staticmethod
    def get_list(empresa_id: int, estado: str = None, tipo_documento: str = None):
        """Fase 7 del plan: bandeja del Centro de Aprobaciones. Sin filtro
        de estado devuelve TODAS las solicitudes (no solo PENDIENTE) -- el
        filtro por defecto lo aplica el frontend/consumidor, este selector
        no asume cual es "la" vista por defecto."""
        qs = (
            SolicitudAprobacion.objects.filter(empresa_id=empresa_id)
            .select_related(
                "solicitante",
                "aprobador",
            )
            .only(*SOLICITUD_LIST_FIELDS)
        )
        if estado:
            qs = qs.filter(estado=estado)
        if tipo_documento:
            qs = qs.filter(tipo_documento=tipo_documento)
        return qs.order_by("-fecha_envio")

    @staticmethod
    def get_pendientes(empresa_id: int):
        # TenantProfile no tiene campos nombres/apellidos propios (__str__
        # usa user.email + cargo, apps/tenant/perfil/models.py) -- no se
        # restringe con 'solicitante__x'/'aprobador__x' en .only() a
        # proposito (mismo criterio que RequisicionCompraSelector.get_list()):
        # con select_related() sin ningun traversal en .only(), Django carga
        # el objeto relacionado completo en vez de fallar por buscar columnas
        # inexistentes.
        return (
            SolicitudAprobacion.objects.filter(
                empresa_id=empresa_id,
                estado=SolicitudAprobacion.Estado.PENDIENTE,
            )
            .select_related("solicitante", "aprobador")
            .only(
                *SOLICITUD_LIST_FIELDS,
            )
            .order_by("-fecha_envio")
        )

    @staticmethod
    def get_detail(empresa_id: int, solicitud_uuid: str):
        return (
            SolicitudAprobacion.objects.filter(
                empresa_id=empresa_id,
                uuid=solicitud_uuid,
            )
            .select_related("solicitante", "aprobador")
            .prefetch_related("historial")
        )

    @staticmethod
    def get_resumen(empresa_id: int) -> dict:
        """Fase 8 del plan (#6 banner, #7 KPIs): "Todos los numeros deben
        provenir del backend" -- nunca calculados/hardcodeados en JS. Lee
        `snapshot_financiero` (ya congelado al enviar, #13) en vez de
        recalcular saldos en vivo para cada fila de la bandeja."""
        hoy = timezone.localdate()
        base = SolicitudAprobacion.objects.filter(empresa_id=empresa_id).only(
            *SOLICITUD_LIST_FIELDS
        )

        pendientes_qs = base.filter(estado=SolicitudAprobacion.Estado.PENDIENTE)
        pendientes = list(pendientes_qs)

        criticas = sum(1 for s in pendientes if s.prioridad == SolicitudAprobacion.Prioridad.ALTA)
        riesgo = sum(1 for s in pendientes if s.prioridad == SolicitudAprobacion.Prioridad.MEDIA)
        normales = sum(1 for s in pendientes if s.prioridad == SolicitudAprobacion.Prioridad.BAJA)

        valor_pendiente = Decimal("0.00")
        for s in pendientes:
            try:
                valor_pendiente += Decimal(str((s.snapshot_financiero or {}).get("valor") or "0"))
            except (InvalidOperation, TypeError):
                continue

        ahora = timezone.now()
        antiguedades_horas = [(ahora - s.fecha_envio).total_seconds() / 3600.0 for s in pendientes]
        antiguedad_promedio_horas = (
            round(sum(antiguedades_horas) / len(antiguedades_horas), 1)
            if antiguedades_horas
            else 0.0
        )
        antiguedad_maxima_horas = round(max(antiguedades_horas), 1) if antiguedades_horas else 0.0

        aprobadas_hoy = base.filter(
            estado=SolicitudAprobacion.Estado.APROBADA,
            fecha_decision__date=hoy,
        ).count()
        rechazadas = base.filter(estado=SolicitudAprobacion.Estado.RECHAZADA).count()

        return {
            "pendientes": len(pendientes),
            "criticas": criticas,
            "riesgo": riesgo,
            "normales": normales,
            "aprobadas_hoy": aprobadas_hoy,
            "rechazadas": rechazadas,
            "valor_pendiente": str(valor_pendiente),
            "antiguedad_promedio_horas": antiguedad_promedio_horas,
            "antiguedad_maxima_horas": antiguedad_maxima_horas,
        }
