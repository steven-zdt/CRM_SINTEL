from django.utils import timezone
from rest_framework import serializers

from apps.tenant.approvals.models import SolicitudAprobacion, SolicitudAprobacionHistorial


class SolicitudAprobacionListSerializer(serializers.ModelSerializer):
    """Fase 8: expone `snapshot_financiero` (numero/valor/proyecto/cotizacion/
    riesgo_pct, ya congelados al enviar, #13) para que la bandeja del Centro
    de Aprobaciones muestre Documento/Proyecto/Origen/Valor/Riesgo sin una
    segunda consulta por fila -- unica fuente de esos datos, nunca
    recalculados en JS."""

    solicitante_nombre = serializers.SerializerMethodField()
    aprobador_nombre = serializers.SerializerMethodField()
    tiempo_pendiente_horas = serializers.SerializerMethodField()

    def get_solicitante_nombre(self, obj) -> str:
        return str(obj.solicitante) if obj.solicitante_id else ""

    def get_aprobador_nombre(self, obj) -> str:
        return str(obj.aprobador) if obj.aprobador_id else ""

    def get_tiempo_pendiente_horas(self, obj):
        if obj.estado != SolicitudAprobacion.Estado.PENDIENTE:
            return None
        return round((timezone.now() - obj.fecha_envio).total_seconds() / 3600.0, 1)

    class Meta:
        model = SolicitudAprobacion
        fields = (
            "id",
            "uuid",
            "tipo_documento",
            "objeto_uuid",
            "estado",
            "prioridad",
            "fecha_envio",
            "fecha_decision",
            "solicitante_nombre",
            "aprobador_nombre",
            "snapshot_financiero",
            "tiempo_pendiente_horas",
        )
        read_only_fields = fields


class SolicitudAprobacionHistorialSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()

    def get_usuario_nombre(self, obj) -> str:
        return str(obj.usuario) if obj.usuario_id else ""

    class Meta:
        model = SolicitudAprobacionHistorial
        fields = (
            "id",
            "uuid",
            "evento",
            "estado_anterior",
            "estado_nuevo",
            "usuario_nombre",
            "observacion",
            "created_at",
        )
        read_only_fields = fields


class SolicitudAprobacionDetailSerializer(serializers.ModelSerializer):
    solicitante_nombre = serializers.SerializerMethodField()
    aprobador_nombre = serializers.SerializerMethodField()
    historial = SolicitudAprobacionHistorialSerializer(many=True, read_only=True)

    def get_solicitante_nombre(self, obj) -> str:
        return str(obj.solicitante) if obj.solicitante_id else ""

    def get_aprobador_nombre(self, obj) -> str:
        return str(obj.aprobador) if obj.aprobador_id else ""

    class Meta:
        model = SolicitudAprobacion
        fields = (
            "id",
            "uuid",
            "tipo_documento",
            "objeto_uuid",
            "estado",
            "prioridad",
            "solicitante_nombre",
            "aprobador_nombre",
            "fecha_envio",
            "fecha_decision",
            "motivo_rechazo",
            "observaciones",
            "snapshot_financiero",
            "historial",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
