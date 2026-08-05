from rest_framework import serializers

from apps.tenant.ventas.models import ItemVenta, ResolucionFacturacion, Venta


class ResolucionFacturacionSerializer(serializers.ModelSerializer):
    numero_formado = serializers.SerializerMethodField()
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    agotada = serializers.SerializerMethodField()

    class Meta:
        model = ResolucionFacturacion
        fields = (
            "id",
            "uuid",
            "numero_resolucion",
            "prefijo",
            "tipo",
            "tipo_display",
            "fecha_resolucion",
            "fecha_desde",
            "fecha_hasta",
            "rango_desde",
            "rango_hasta",
            "consecutivo_actual",
            "vigente",
            "numero_formado",
            "agotada",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id", "uuid", "consecutivo_actual", "numero_formado", "agotada",
            "tipo_display", "created_at", "updated_at",
        )

    def get_numero_formado(self, obj):
        return obj.formar_numero()

    def get_agotada(self, obj):
        return not obj.esta_en_rango()


class ItemVentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemVenta
        fields = (
            "id",
            "descripcion",
            "cantidad",
            "precio_unitario",
            "porcentaje_iva",
            "subtotal",
            "producto_id",
            "servicio_id",
        )
        read_only_fields = ("id", "subtotal")


class VentaListSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(
        source="cliente.razon_social",
        read_only=True,
        default="",
    )
    cliente_documento = serializers.CharField(
        source="cliente.numero_documento",
        read_only=True,
        default="",
    )
    factura_numero = serializers.SerializerMethodField()
    factura_uuid = serializers.SerializerMethodField()
    resolucion_prefijo = serializers.SerializerMethodField()

    class Meta:
        model = Venta
        fields = (
            "id",
            "uuid",
            "fecha_emision",
            "fecha_vencimiento",
            "estado",
            "subtotal",
            "impuestos",
            "total_neto",
            "numero_factura",
            "cliente_id",
            "cliente_nombre",
            "cliente_documento",
            "proyecto_id",
            "resolucion_id",
            "resolucion_prefijo",
            "factura_asociada_id",
            "factura_numero",
            "factura_uuid",
            "created_at",
        )
        read_only_fields = fields

    def get_factura_numero(self, obj):
        if obj.factura_asociada_id and obj.factura_asociada:
            return obj.factura_asociada.numero
        return obj.numero_factura

    def get_factura_uuid(self, obj):
        if obj.factura_asociada_id and obj.factura_asociada:
            return str(obj.factura_asociada.uuid)
        return None

    def get_resolucion_prefijo(self, obj):
        if obj.resolucion_id and obj.resolucion:
            return obj.resolucion.prefijo or obj.resolucion.numero_resolucion
        return None


class VentaDetailSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(
        source="cliente.razon_social",
        read_only=True,
        default="",
    )
    cliente_documento = serializers.CharField(
        source="cliente.numero_documento",
        read_only=True,
        default="",
    )
    proyecto_nombre = serializers.CharField(
        source="proyecto.nombre",
        read_only=True,
        default="",
    )
    resolucion_numero = serializers.SerializerMethodField()
    resolucion_prefijo = serializers.SerializerMethodField()
    factura_numero = serializers.SerializerMethodField()
    factura_uuid = serializers.SerializerMethodField()
    factura_estado = serializers.SerializerMethodField()
    items = ItemVentaSerializer(many=True, read_only=True)

    class Meta:
        model = Venta
        fields = (
            "id",
            "uuid",
            "fecha_emision",
            "fecha_vencimiento",
            "estado",
            "subtotal",
            "impuestos",
            "total_neto",
            "observaciones",
            "numero_factura",
            "cliente_id",
            "cliente_nombre",
            "cliente_documento",
            "proyecto_id",
            "proyecto_nombre",
            "resolucion_id",
            "resolucion_numero",
            "resolucion_prefijo",
            "factura_asociada_id",
            "factura_numero",
            "factura_uuid",
            "factura_estado",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_resolucion_numero(self, obj):
        if obj.resolucion_id and obj.resolucion:
            return obj.resolucion.numero_resolucion
        return None

    def get_resolucion_prefijo(self, obj):
        if obj.resolucion_id and obj.resolucion:
            return obj.resolucion.prefijo
        return None

    def get_factura_numero(self, obj):
        if obj.factura_asociada_id and obj.factura_asociada:
            return obj.factura_asociada.numero
        return obj.numero_factura

    def get_factura_uuid(self, obj):
        if obj.factura_asociada_id and obj.factura_asociada:
            return str(obj.factura_asociada.uuid)
        return None

    def get_factura_estado(self, obj):
        if obj.factura_asociada_id and obj.factura_asociada:
            return obj.factura_asociada.estado
        return None
