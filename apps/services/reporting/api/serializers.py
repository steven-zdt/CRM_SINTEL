"""
Serializers del Reporting Hub -- validan el limite de entrada (Regla
Absoluta #4/#9: el frontend solo puede enviar report_id/filtros/dimensiones/
medidas/orden/paginacion declarados, nunca SQL/modelo/tabla/campo libre).
"""
from rest_framework import serializers

from apps.services.reporting.exporters import SUPPORTED_FORMATS


class ReportQueryRequestSerializer(serializers.Serializer):
    dataset_id = serializers.CharField(max_length=100)
    filters = serializers.DictField(required=False, default=dict)
    group_by = serializers.ListField(child=serializers.CharField(max_length=100), required=False, default=list)
    measures = serializers.ListField(child=serializers.CharField(max_length=100), required=False, default=list)
    order_by = serializers.CharField(max_length=100, required=False, allow_null=True, default=None)
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=50, min_value=1, max_value=1000)


class ReportExportRequestSerializer(ReportQueryRequestSerializer):
    # WARNING: BUGFIX: el campo NO puede llamarse "format" -- DRF reserva ese
    # nombre de query param para su propia negociacion de contenido
    # (settings.URL_FORMAT_OVERRIDE, default 'format'). DefaultContentNegotiation.
    # filter_renderers() levanta Http404 (no 406) cuando ?format=csv/xlsx no
    # coincide con ningun renderer registrado -- confirmado en vivo: GET
    # .../export/?format=csv devolvia 404 antes de que export_report() se
    # ejecutara siquiera, mientras que el mismo valor en el body de un POST
    # (fuera de query_params) funcionaba bien.
    export_format = serializers.ChoiceField(choices=SUPPORTED_FORMATS, default="csv")
