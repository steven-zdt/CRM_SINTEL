"""
Serializers para Ventas — OrdenVenta e ItemOrdenVenta.

Sigue el patron FSD de SINTEL v3.10.5:
- UUIDOrPKRelatedField para cliente (acepta UUID publico o PK interno).
- Campos read_only calculados por el CRUD service (subtotal, impuestos, total).
- Items anidados en el serializer de detalle y creacion.
"""
from decimal import Decimal

from rest_framework import serializers

from apps.tenant.ventas.models import ItemOrdenVenta, OrdenVenta


class UUIDOrPKRelatedField(serializers.PrimaryKeyRelatedField):
    """
    Campo relacionado que acepta UUID publico o ID entero de Django.
    Filtra el queryset por empresa_id (DSV al nivel de serializacion).
    """

    def get_queryset(self):
        qs = super().get_queryset()
        if qs is None:
            return qs
        root = getattr(self, "root", None)
        context = getattr(root, "context", {}) if root else {}
        empresa_id = context.get("empresa_id")
        if empresa_id and hasattr(qs.model, "empresa_id"):
            return qs.filter(empresa_id=empresa_id)
        return qs

    def to_internal_value(self, data):
        if data in (None, ""):
            if self.allow_null:
                return None
            self.fail("required")
        data_str = str(data)
        if not data_str.isdigit():
            qs = self.get_queryset()
            try:
                return qs.get(uuid=data_str)
            except (TypeError, ValueError, qs.model.DoesNotExist):
                self.fail("does_not_exist", pk_value=data)
        return super().to_internal_value(data)


class ItemOrdenVentaSerializer(serializers.ModelSerializer):
    """Serializer para items de OrdenVenta (lectura y escritura)."""

    class Meta:
        model = ItemOrdenVenta
        fields = (
            "id",
            "descripcion",
            "cantidad",
            "precio_unitario",
            "tasa_iva",
            "subtotal",
            "producto_id",
            "servicio_id",
        )
        read_only_fields = ("id", "subtotal")


class OrdenVentaListSerializer(serializers.ModelSerializer):
    """Serializer optimizado para el listado en Tabulator."""

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

    class Meta:
        model = OrdenVenta
        fields = (
            "id",
            "uuid",
            "fecha_emision",
            "fecha_vencimiento",
            "estado",
            "subtotal",
            "impuestos",
            "total",
            "cliente_id",
            "cliente_nombre",
            "cliente_documento",
            "factura_id",
            "factura_numero",
            "created_at",
        )
        read_only_fields = fields

    def get_factura_numero(self, obj):
        if obj.factura_id and obj.factura:
            return obj.factura.numero
        return None


class OrdenVentaDetailSerializer(serializers.ModelSerializer):
    """Serializer completo para detalle e HTMX offcanvas."""

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
    items = ItemOrdenVentaSerializer(many=True, read_only=True)

    class Meta:
        model = OrdenVenta
        fields = (
            "id",
            "uuid",
            "fecha_emision",
            "fecha_vencimiento",
            "estado",
            "subtotal",
            "impuestos",
            "total",
            "observaciones",
            "cliente_id",
            "cliente_nombre",
            "cliente_documento",
            "factura_id",
            "factura_numero",
            "factura_uuid",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_factura_numero(self, obj):
        if obj.factura_id and obj.factura:
            return obj.factura.numero
        return None

    def get_factura_uuid(self, obj):
        if obj.factura_id and obj.factura:
            return str(obj.factura.uuid)
        return None


class OrdenVentaCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer para CREATE y PATCH de OrdenVenta con items anidados."""

    from apps.tenant.clientes.models import Cliente

    cliente = UUIDOrPKRelatedField(
        queryset=Cliente.objects.none(),
    )
    items = ItemOrdenVentaSerializer(many=True, required=False)

    class Meta:
        model = OrdenVenta
        fields = (
            "cliente",
            "fecha_emision",
            "fecha_vencimiento",
            "observaciones",
            "items",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.tenant.clientes.models import Cliente

        empresa_id = self.context.get("empresa_id")
        if empresa_id:
            self.fields["cliente"].queryset = Cliente.objects.filter(
                empresa_id=empresa_id,
                activo=True,
            )
        else:
            self.fields["cliente"].queryset = Cliente.objects.none()

    def validate_items(self, items):
        if items is not None and len(items) == 0:
            raise serializers.ValidationError(
                "La orden debe tener al menos un item."
            )
        return items

    def to_representation(self, instance):
        return OrdenVentaDetailSerializer(instance, context=self.context).data
