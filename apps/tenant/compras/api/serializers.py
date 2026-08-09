from rest_framework import serializers

from apps.tenant.compras.models import (
    ItemOrdenCompra,
    OrdenCompra,
    PlantillaOrdenCompra,
    RecepcionCompra,
    RecepcionCompraItem,
)
from apps.tenant.empresa.models import Area
from apps.tenant.gastos.models import DocumentoSoporte
from apps.tenant.proveedores.models import Proveedor
from apps.tenant.proyectos.models import Proyecto


class UUIDOrPKRelatedField(serializers.PrimaryKeyRelatedField):
    """
    Campo relacionado que acepta UUID publico o ID interno de Django.
    Garantiza compatibilidad con interfaces FSD y Zero Trust.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        if queryset is None:
            return queryset
        root = getattr(self, 'root', None)
        context = getattr(root, 'context', {}) if root else {}
        empresa_id = context.get('empresa_id')
        if empresa_id and hasattr(queryset.model, 'empresa_id'):
            return queryset.filter(empresa_id=empresa_id)
        return queryset

    def to_internal_value(self, data):
        if data in (None, ''):
            if self.allow_null:
                return None
            self.fail('required')
        data_str = str(data)
        if not data_str.isdigit():
            queryset = self.get_queryset()
            try:
                return queryset.get(uuid=data_str)
            except (TypeError, ValueError, queryset.model.DoesNotExist):
                self.fail('does_not_exist', pk_value=data)
        return super().to_internal_value(data)


class PlantillaOrdenCompraSerializer(serializers.ModelSerializer):
    """
    Serializer para Plantilla de Orden de Compra.
    """
    class Meta:
        model = PlantillaOrdenCompra
        fields = (
            'id',
            'uuid',
            'nombre',
            'prefijo',
            'rango_desde',
            'rango_hasta',
            'consecutivo_actual',
            'vigente',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'uuid', 'created_at', 'updated_at')


class ItemOrdenCompraSerializer(serializers.ModelSerializer):
    """
    Serializer para el detalle de items de la Orden de Compra.
    """
    class Meta:
        model = ItemOrdenCompra
        fields = (
            'id',
            'uuid',
            'descripcion',
            'item_inventario_uuid',
            'cantidad',
            'valor_unitario',
            'porcentaje_iva',
            'valor_iva',
            'subtotal',
            'total',
        )
        read_only_fields = ('id', 'uuid', 'valor_iva', 'subtotal', 'total')


class OrdenCompraListSerializer(serializers.ModelSerializer):
    """
    Serializer aplanado para renderizado en grillas (Tabulator) y listado general.
    """
    proveedor_nombre = serializers.CharField(source='proveedor.razon_social', read_only=True)
    proveedor_nit = serializers.CharField(source='proveedor.numero_documento', read_only=True)
    proyecto_nombre = serializers.CharField(source='proyecto.nombre', read_only=True, default='')
    documento_soporte_numero = serializers.SerializerMethodField()
    plantilla_nombre = serializers.CharField(source='plantilla.nombre', read_only=True, default='')
    # [OSF Fase F5] antes invisible: un listado puede traer ordenes de
    # multiples sedes/areas a la vez (ver OrdenCompraSelector.get_list),
    # sin esto no habia forma de distinguir de donde era cada fila.
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, default='')
    area_nombre = serializers.CharField(source='area.nombre', read_only=True, default='')

    def get_documento_soporte_numero(self, obj) -> str:
        if obj.documento_soporte:
            return obj.documento_soporte.numero_documento_proveedor or ''
        return ''

    class Meta:
        model = OrdenCompra
        fields = (
            'id',
            'uuid',
            'consecutivo',
            'numero_documento',
            'fecha',
            'fecha_entrega',
            'estado',
            'subtotal',
            'impuestos',
            'total',
            'proveedor_nombre',
            'proveedor_nit',
            'proyecto_nombre',
            'documento_soporte_numero',
            'plantilla_nombre',
            'sede_nombre',
            'area_nombre',
        )
        read_only_fields = fields


class OrdenCompraDetailSerializer(serializers.ModelSerializer):
    """
    Serializer detallado que incluye la lista de items.
    """
    items = ItemOrdenCompraSerializer(many=True, read_only=True)
    proveedor_nombre = serializers.CharField(source='proveedor.razon_social', read_only=True)
    proveedor_nit = serializers.CharField(source='proveedor.numero_documento', read_only=True)
    proyecto_nombre = serializers.CharField(source='proyecto.nombre', read_only=True, default='')
    documento_soporte_numero = serializers.SerializerMethodField()
    plantilla_nombre = serializers.CharField(source='plantilla.nombre', read_only=True, default='')
    plantilla_uuid = serializers.CharField(source='plantilla.uuid', read_only=True, default='')
    # [OSF Fase F5] ver nota en OrdenCompraListSerializer.
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, default='')
    area_nombre = serializers.CharField(source='area.nombre', read_only=True, default='')

    def get_documento_soporte_numero(self, obj) -> str:
        if obj.documento_soporte:
            return obj.documento_soporte.numero_documento_proveedor or ''
        return ''

    class Meta:
        model = OrdenCompra
        fields = (
            'id',
            'uuid',
            'consecutivo',
            'numero_documento',
            'fecha',
            'fecha_entrega',
            'estado',
            'subtotal',
            'impuestos',
            'total',
            'observaciones',
            'proveedor',
            'proveedor_nombre',
            'proveedor_nit',
            'proyecto',
            'proyecto_nombre',
            'documento_soporte',
            'documento_soporte_numero',
            'plantilla_nombre',
            'plantilla_uuid',
            'sede_nombre',
            'area_nombre',
            'items',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class OrdenCompraCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer de escritura para la creacion y actualizacion de Ordenes de Compra.
    """
    plantilla = UUIDOrPKRelatedField(queryset=PlantillaOrdenCompra.objects.all(), required=True)
    proveedor = UUIDOrPKRelatedField(queryset=Proveedor.objects.all())
    proyecto = UUIDOrPKRelatedField(queryset=Proyecto.objects.all(), required=False, allow_null=True)
    documento_soporte = UUIDOrPKRelatedField(queryset=DocumentoSoporte.objects.all(), required=False, allow_null=True)
    # [OSF Fase F5] Hallazgo real: este campo faltaba por completo aqui -
    # OrdenCompraBusinessService.crear_orden_compra() ya tenia logica DSV
    # completa para 'area' (opcional), pero como el serializer nunca lo
    # declaraba, DRF lo descartaba de validated_data antes de llegar al
    # business service - Area era, en la practica, IMPOSIBLE de asignar via
    # la API pese a que el modelo/service la soportan.
    area = UUIDOrPKRelatedField(queryset=Area.objects.all(), required=False, allow_null=True)
    items = ItemOrdenCompraSerializer(many=True, required=True)

    class Meta:
        model = OrdenCompra
        fields = (
            'plantilla',
            'proveedor',
            'proyecto',
            'area',
            'documento_soporte',
            'fecha',
            'fecha_entrega',
            'estado',
            'observaciones',
            'items',
        )

    def validate(self, attrs):
        fecha = attrs.get('fecha')
        fecha_entrega = attrs.get('fecha_entrega')
        if fecha and fecha_entrega and fecha_entrega < fecha:
            raise serializers.ValidationError(
                {'fecha_entrega': 'La fecha de entrega no puede ser anterior a la fecha de emision.'}
            )
        return attrs

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Debe proporcionar al menos un item para la orden de compra.")
        return value


class RecepcionCompraItemSerializer(serializers.ModelSerializer):
    """Linea de recepcion (F21) — referencia al ItemOrdenCompra que se esta recibiendo."""
    item_orden_compra = UUIDOrPKRelatedField(queryset=ItemOrdenCompra.objects.all())

    class Meta:
        model = RecepcionCompraItem
        fields = ('id', 'uuid', 'item_orden_compra', 'cantidad_recibida', 'observaciones')
        read_only_fields = ('id', 'uuid')


class RecepcionCompraListSerializer(serializers.ModelSerializer):
    """Serializer aplanado para listado de Recepciones de Compra (F21)."""
    orden_compra_uuid = serializers.CharField(source='orden_compra.uuid', read_only=True)
    orden_compra_numero = serializers.CharField(source='orden_compra.numero_documento', read_only=True, default='')
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, default='')
    area_nombre = serializers.CharField(source='area.nombre', read_only=True, default='')
    usuario_nombre = serializers.SerializerMethodField()

    def get_usuario_nombre(self, obj) -> str:
        return str(obj.usuario) if obj.usuario_id else ''

    class Meta:
        model = RecepcionCompra
        fields = (
            'id', 'uuid', 'fecha', 'estado', 'observaciones',
            'orden_compra_uuid', 'orden_compra_numero',
            'sede_nombre', 'area_nombre', 'usuario_nombre', 'created_at',
        )
        read_only_fields = fields


class RecepcionCompraDetailSerializer(RecepcionCompraListSerializer):
    """Serializer detallado que incluye las lineas de recepcion."""
    items = RecepcionCompraItemSerializer(many=True, read_only=True)

    class Meta(RecepcionCompraListSerializer.Meta):
        fields = RecepcionCompraListSerializer.Meta.fields + ('items', 'updated_at')


class RecepcionCompraCreateSerializer(serializers.ModelSerializer):
    """Serializer de escritura para crear una Recepcion de Compra en BORRADOR."""
    orden_compra = UUIDOrPKRelatedField(queryset=OrdenCompra.objects.all())
    items = RecepcionCompraItemSerializer(many=True, required=True)

    class Meta:
        model = RecepcionCompra
        fields = ('orden_compra', 'fecha', 'observaciones', 'items')

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Debe indicar al menos un item recibido.")
        return value
