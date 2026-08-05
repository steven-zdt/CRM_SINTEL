"""
Serializers para la app impuestos (catálogo DIAN).

Referencia: https://www.django-rest-framework.org/api-guide/serializers/
"""

from rest_framework import serializers

from apps.public.impuestos.models import (
    ActividadEconomica,
    CodigoTributario,
    ConceptoRetencion,
    ContribuyenteTipo,
    NormaTributaria,
    PerfilTributario,
    RegimenRenta,
    ResponsabilidadRUT,
    TarifaIVA,
    TipoImpuesto,
)


class TipoImpuestoSerializer(serializers.ModelSerializer):
    """Serializer para TipoImpuesto."""

    class Meta:
        model = TipoImpuesto
        fields = "__all__"


class TarifaIVASerializer(serializers.ModelSerializer):
    """Serializer para TarifaIVA."""

    class Meta:
        model = TarifaIVA
        fields = "__all__"


class ConceptoRetencionSerializer(serializers.ModelSerializer):
    """Serializer para ConceptoRetencion."""

    class Meta:
        model = ConceptoRetencion
        fields = "__all__"


class CodigoTributarioSerializer(serializers.ModelSerializer):
    """Serializer para CodigoTributario."""

    class Meta:
        model = CodigoTributario
        fields = "__all__"


class ActividadEconomicaSerializer(serializers.ModelSerializer):
    """Serializer para ActividadEconomica."""

    class Meta:
        model = ActividadEconomica
        fields = "__all__"


class NormaTributariaSerializer(serializers.ModelSerializer):
    """Serializer para NormaTributaria."""

    class Meta:
        model = NormaTributaria
        fields = "__all__"


class NormaTributariaListSerializer(serializers.ModelSerializer):
    """
    [PERF-A3] Serializer de listado para NormaTributaria: excluye texto_html/
    texto_plano (TextField con el articulo legal completo -- pueden ser grandes
    y no se muestran en un listado, solo en el detalle). El filtrado por
    texto_plano (search_fields) sigue funcionando: SearchFilter genera un
    WHERE ... ILIKE a nivel SQL, no depende de que el campo se traiga a Python.
    """

    class Meta:
        model = NormaTributaria
        exclude = ("texto_html", "texto_plano")


# ============================================================================
# SERIALIZERS PARA NORMATIVA DIAN - CATÁLOGOS TRIBUTARIOS (v2.30+)
# ============================================================================


class ContribuyenteTipoSerializer(serializers.ModelSerializer):
    """Serializer para ContribuyenteTipo."""

    class Meta:
        model = ContribuyenteTipo
        fields = "__all__"


class RegimenRentaSerializer(serializers.ModelSerializer):
    """Serializer para RegimenRenta."""

    class Meta:
        model = RegimenRenta
        fields = "__all__"


class ResponsabilidadRUTSerializer(serializers.ModelSerializer):
    """Serializer para ResponsabilidadRUT."""

    class Meta:
        model = ResponsabilidadRUT
        fields = "__all__"


class PerfilTributarioSerializer(serializers.ModelSerializer):
    """Serializer para PerfilTributario."""

    tipo_contribuyente = ContribuyenteTipoSerializer(read_only=True)
    regimen_renta = RegimenRentaSerializer(read_only=True)
    responsabilidades = ResponsabilidadRUTSerializer(many=True, read_only=True)

    # Campos para escritura (IDs)
    tipo_contribuyente_id = serializers.PrimaryKeyRelatedField(
        queryset=ContribuyenteTipo.objects.all(),
        source="tipo_contribuyente",
        write_only=True,
        required=True,
    )
    regimen_renta_id = serializers.PrimaryKeyRelatedField(
        queryset=RegimenRenta.objects.all(), source="regimen_renta", write_only=True, required=True
    )
    responsabilidades_ids = serializers.PrimaryKeyRelatedField(
        queryset=ResponsabilidadRUT.objects.all(),
        source="responsabilidades",
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = PerfilTributario
        fields = "__all__"
