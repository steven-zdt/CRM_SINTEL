"""Core API v1 - Gastos serializers facade.

⚠️ POLÍTICA:
- No copiar lógica de negocio.
- Heredar serializers existentes de la app gastos.
- Exponer URLs de adjuntos (evidencia) para el Workspace.
"""

from rest_framework import serializers

from apps.tenant.gastos.api.serializers import (
    DocumentoSoporteDetailSerializer,
    GastoDetailSerializer,
    GastoListSerializer,
)


class DocumentoSoporteWorkspaceDetailSerializer(DocumentoSoporteDetailSerializer):
    adjunto_url = serializers.SerializerMethodField()

    class Meta(DocumentoSoporteDetailSerializer.Meta):
        fields = tuple(DocumentoSoporteDetailSerializer.Meta.fields) + ("adjunto_url",)

    def get_adjunto_url(self, obj):
        request = self.context.get("request") if hasattr(self, "context") else None
        if not getattr(obj, "adjunto", None):
            return None
        try:
            url = obj.adjunto.url
        except Exception:
            return None
        return request.build_absolute_uri(url) if request else url


class GastoWorkspaceListSerializer(GastoListSerializer):
    class Meta(GastoListSerializer.Meta):
        pass


class GastoWorkspaceDetailSerializer(GastoDetailSerializer):
    documento_soporte = DocumentoSoporteWorkspaceDetailSerializer(read_only=True)

    class Meta(GastoDetailSerializer.Meta):
        pass
