"""
Serializadores para Cotizaciones v2.62.0 - SINTEL FSD
"""
import logging

from rest_framework import serializers

from apps.tenant.api.utils import resolve_tenant_empresa
from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Sede
from ..configuracion.models import ConfiguracionCotizacion
from ..models import Cotizacion, CotizacionItem, Producto, Servicio

logger = logging.getLogger(__name__)


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ['id', 'uuid', 'codigo', 'nombre', 'marca', 'referencia', 'unidad', 'precio_venta', 'activo', 'created_at']
        read_only_fields = ['uuid', 'created_at']


class ServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio
        fields = ['id', 'uuid', 'nombre', 'precio_venta', 'activo', 'created_at']
        read_only_fields = ['uuid', 'created_at']


class CotizacionItemNestedSerializer(serializers.ModelSerializer):
    """Items embebidos en CotizacionSerializer. Sin campo cotizacion - lo asigna el servicio."""
    id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = CotizacionItem
        fields = [
            'id', 'uuid', 'tipo_item',
            'descripcion', 'marca', 'referencia', 'unidad',
            'cantidad', 'costo_unitario', 'porcentaje_utilidad',
            'precio_unitario_venta', 'subtotal_linea', 'orden',
        ]
        read_only_fields = ['uuid', 'precio_unitario_venta', 'subtotal_linea']


class CotizacionItemSerializer(serializers.ModelSerializer):
    """Standalone para CRUD directo de items via CotizacionItemViewSet."""
    class Meta:
        model = CotizacionItem
        fields = [
            'id', 'uuid', 'cotizacion', 'tipo_item',
            'descripcion', 'marca', 'referencia', 'unidad',
            'cantidad', 'costo_unitario', 'porcentaje_utilidad',
            'precio_unitario_venta', 'subtotal_linea', 'orden',
        ]
        read_only_fields = ['uuid', 'precio_unitario_venta', 'subtotal_linea']


class CotizacionListSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.ReadOnlyField(source='cliente.nombre_comercial')
    cliente_razon_social = serializers.ReadOnlyField(source='cliente.razon_social')
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    # DT-SEDE-04: sede para KPIs por sede
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, allow_null=True)

    class Meta:
        model = Cotizacion
        fields = [
            'id', 'uuid', 'numero_cotizacion', 'codigo_unico', 'tipo_cotizacion',
            'estado', 'estado_display',
            'fecha_emision', 'fecha_vencimiento', 'total_con_impuestos',
            'cliente', 'cliente_nombre', 'cliente_razon_social',
            'empresa', 'created_at',
            'sede_nombre',  # DT-SEDE-04
        ]
        read_only_fields = fields


class UUIDOrPKRelatedField(serializers.PrimaryKeyRelatedField):
    """Campo relacionado que acepta UUID publico o PK interno en formularios legacy."""

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


class CotizacionSerializer(serializers.ModelSerializer):
    items = CotizacionItemNestedSerializer(many=True, required=False)
    cliente_nombre = serializers.ReadOnlyField(source='cliente.nombre_comercial')
    configuracion_nombre = serializers.ReadOnlyField(source='configuracion.nombre_configuracion')
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    cliente = UUIDOrPKRelatedField(queryset=Cliente.objects.none())
    configuracion = UUIDOrPKRelatedField(queryset=ConfiguracionCotizacion.objects.none())

    # DT-SEDE-04: sede para KPIs por sede
    sede = UUIDOrPKRelatedField(queryset=Sede.objects.none(), required=False, allow_null=True,
                                help_text='UUID de la sede que emite la cotizacion (opcional)')
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, allow_null=True)

    class Meta:
        model = Cotizacion
        fields = [
            'uuid', 'numero_cotizacion', 'codigo_unico', 'empresa',
            'cliente', 'cliente_nombre',
            'configuracion', 'configuracion_nombre',
            'tipo_cotizacion', 'estado', 'estado_display',
            'fecha_emision', 'fecha_vencimiento',
            'porcentaje_aiu_admin', 'porcentaje_aiu_imprevistos', 'porcentaje_aiu_utilidad',
            'iva_porcentaje', 'total_con_impuestos',
            'dias_totales', 'dias_infraestructura', 'dias_instalacion', 'dias_configuracion', 'dias_pruebas',
            'sede', 'sede_nombre',  # DT-SEDE-04
            'items',
        ]
        read_only_fields = [
            'numero_cotizacion', 'codigo_unico', 'empresa',
            'total_con_impuestos', 'estado_display', 'fecha_vencimiento', 'sede_nombre',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        empresa = self.context.get('empresa')
        request = self.context.get('request')
        if not empresa and request:
            empresa = resolve_tenant_empresa(request)
        if not empresa:
            return
        self.fields['cliente'].queryset = Cliente.objects.filter(empresa_id=empresa.id, activo=True)
        self.fields['configuracion'].queryset = ConfiguracionCotizacion.objects.filter(empresa_id=empresa.id)
        self.fields['sede'].queryset = Sede.objects.filter(empresa_id=empresa.id).only('id', 'uuid', 'nombre')

    def validate(self, attrs):
        attrs = super().validate(attrs)
        sede = attrs.get('sede')
        empresa = self.context.get('empresa')
        if sede and empresa and sede.empresa_id != empresa.id:
            raise serializers.ValidationError(
                {'sede': 'La sede seleccionada no pertenece a esta empresa.'}
            )
        return attrs
