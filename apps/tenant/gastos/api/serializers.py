"""
Serializers para la API de gastos.

v2.62: FLEXIBILIDAD OPERATIVA - Inmutabilidad deshabilitada.
- Alineado con LIST_FIELDS y DETAIL_FIELDS del service.
- Campos aplanados para Tabulator (v2.40): 'ds_consecutivo', etc.
- Edicion permitida en campos monetarios y legales segun requerimiento.
"""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.proveedores.models import Proveedor


from apps.tenant.inventario.models import Producto, Servicio, ActivoFijo

class UUIDOrPKRelatedField(serializers.PrimaryKeyRelatedField):
    """Campo relacionado que acepta UUID publico o PK interno en formularios legacy."""

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


class ResolucionDIANNestedSerializer(serializers.ModelSerializer):
    """
    Serializer anidado para ResolucionDIAN (v2.40).
    """
    fecha_resolucion = serializers.DateField(format='%Y-%m-%d', required=False, read_only=True)
    fecha_inicio = serializers.DateField(format='%Y-%m-%d', required=False, read_only=True)
    fecha_fin = serializers.DateField(format='%Y-%m-%d', required=False, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = ResolucionDIAN
        fields = (
            'id',
            'uuid',
            'numero_resolucion',
            'prefijo',
            'rango_desde',
            'rango_hasta',
            'fecha_resolucion',
            'fecha_inicio',
            'fecha_fin',
            'clave_tecnica',
            'vigente',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class ResolucionDIANListSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para listado de resoluciones (Tabulator v2.40).
    """
    fecha_resolucion = serializers.DateField(format='%Y-%m-%d', read_only=True)
    fecha_inicio = serializers.DateField(format='%Y-%m-%d', read_only=True)
    fecha_fin = serializers.DateField(format='%Y-%m-%d', read_only=True)
    conteo_documentos = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ResolucionDIAN
        fields = (
            'id',
            'uuid',
            'numero_resolucion',
            'prefijo',
            'rango_desde',
            'rango_hasta',
            'fecha_resolucion',
            'fecha_inicio',
            'fecha_fin',
            'vigente',
            'conteo_documentos',
        )
        read_only_fields = fields


class ResolucionDIANCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear resoluciones DIAN (v2.60).
    """
    fecha_resolucion = serializers.DateField(format='%Y-%m-%d', input_formats=['%Y-%m-%d', '%d-%m-%Y'])
    fecha_inicio = serializers.DateField(format='%Y-%m-%d', input_formats=['%Y-%m-%d', '%d-%m-%Y'], required=False, allow_null=True)
    fecha_fin = serializers.DateField(format='%Y-%m-%d', input_formats=['%Y-%m-%d', '%d-%m-%Y'])
    vigente = serializers.BooleanField(required=False, default=True)
    
    class Meta:
        model = ResolucionDIAN
        fields = (
            'id',
            'uuid',
            'empresa',
            'numero_resolucion',
            'prefijo',
            'rango_desde',
            'rango_hasta',
            'fecha_resolucion',
            'fecha_inicio',
            'fecha_fin',
            'clave_tecnica',
            'vigente',
        )
        read_only_fields = ('id', 'uuid', 'empresa')
    
    def validate_vigente(self, value):
        if value is None or value == '':
            return False
        if isinstance(value, str):
            if value.lower() in ('on', 'true', '1', 'yes'):
                return True
            return False
        return bool(value)
    
    def validate(self, attrs):
        fecha_resolucion = attrs.get('fecha_resolucion')
        fecha_fin = attrs.get('fecha_fin')
        rango_desde = attrs.get('rango_desde')
        rango_hasta = attrs.get('rango_hasta')
        
        if fecha_resolucion and fecha_fin:
            if fecha_fin <= fecha_resolucion:
                raise serializers.ValidationError({
                    'fecha_fin': 'La fecha de fin debe ser posterior a la fecha de emision.'
                })
        
        if rango_desde is not None and rango_hasta is not None:
            if rango_hasta <= rango_desde:
                raise serializers.ValidationError({
                    'rango_hasta': 'El numero final del rango debe ser mayor al inicial.'
                })
        return attrs


class ResolucionDIANDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para detalle de resolucion (v2.40).
    """
    fecha_resolucion = serializers.DateField(format='%Y-%m-%d', read_only=True)
    fecha_inicio = serializers.DateField(format='%Y-%m-%d', read_only=True)
    fecha_fin = serializers.DateField(format='%Y-%m-%d', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    conteo_documentos = serializers.SerializerMethodField()
    
    class Meta:
        model = ResolucionDIAN
        fields = (
            'id',
            'uuid',
            'empresa',
            'numero_resolucion',
            'prefijo',
            'rango_desde',
            'rango_hasta',
            'fecha_resolucion',
            'fecha_inicio',
            'fecha_fin',
            'clave_tecnica',
            'vigente',
            'conteo_documentos',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields
    
    def get_conteo_documentos(self, obj):
        return obj.documentos_soporte.count()
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        from datetime import date, datetime
        for fecha_field in ['fecha_resolucion', 'fecha_inicio', 'fecha_fin']:
            if fecha_field in data and data[fecha_field] is not None:
                if isinstance(data[fecha_field], date) and not isinstance(data[fecha_field], datetime):
                    data[fecha_field] = data[fecha_field].isoformat()
        return data



class DocumentoSoporteListSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para Tabulator (v2.40).
    Alineado con DocumentoSoporte tras unificacion.
    WARNING: v3.7.1 - Campo UUID opaco para integracion contable (?18 Pull Model).
    """
    ds_consecutivo = serializers.IntegerField(source='consecutivo', read_only=True)
    ds_prefijo = serializers.SerializerMethodField()
    ds_numero_documento = serializers.SerializerMethodField()
    ds_vendedor = serializers.CharField(source='proveedor.razon_social', read_only=True)
    ds_fecha = serializers.DateField(source='fecha', format='%Y-%m-%d', read_only=True)
    ds_subtotal = serializers.DecimalField(source='subtotal', max_digits=12, decimal_places=2, read_only=True)
    ds_total = serializers.DecimalField(source='total', max_digits=15, decimal_places=2, read_only=True)
    ds_activo = serializers.BooleanField(source='activo', read_only=True)
    ds_anulado = serializers.BooleanField(source='anulado', read_only=True)
    ds_numero_documento_proveedor = serializers.CharField(source='numero_documento_proveedor', read_only=True)
    cuenta_gasto_uuid = serializers.UUIDField(allow_null=True, read_only=True)

    categoria_contable_display = serializers.CharField(source='get_categoria_contable_display', read_only=True)

    producto_relacionado = UUIDOrPKRelatedField(queryset=Producto.objects.all(), required=False, allow_null=True)
    servicio_relacionado = UUIDOrPKRelatedField(queryset=Servicio.objects.all(), required=False, allow_null=True)
    activo_relacionado = UUIDOrPKRelatedField(queryset=ActivoFijo.objects.all(), required=False, allow_null=True)

    producto_relacionado_nombre = serializers.CharField(source='producto_relacionado.nombre', read_only=True, allow_null=True)
    servicio_relacionado_nombre = serializers.CharField(source='servicio_relacionado.nombre', read_only=True, allow_null=True)
    activo_relacionado_nombre = serializers.CharField(source='activo_relacionado.nombre', read_only=True, allow_null=True)

    def get_ds_prefijo(self, obj):
        try:
            return obj.resolucion_dian.prefijo
        except Exception:
            return ''

    def get_ds_numero_documento(self, obj):
        try:
            return obj.numero_documento
        except Exception:
            return str(obj.consecutivo)

    class Meta:
        model = DocumentoSoporte
        fields = (
            'id',
            'uuid',
            'categoria_contable',
            'categoria_contable_display',
            'descripcion',
            'ds_consecutivo',
            'ds_prefijo',
            'ds_numero_documento',
            'ds_vendedor',
            'ds_fecha',
            'ds_subtotal',
            'ds_total',
            'ds_activo',
            'ds_anulado',
            'ds_numero_documento_proveedor',
            'cuenta_gasto_uuid',
            'producto_relacionado',
            'servicio_relacionado',
            'activo_relacionado',
            'producto_relacionado_nombre',
            'servicio_relacionado_nombre',
            'activo_relacionado_nombre',
        )
        read_only_fields = fields


class DocumentoSoporteDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para evidencia legal y clasificacion operativa (v2.40).
    WARNING: v3.7.1 - Campo UUID opaco para integracion contable (?18 Pull Model).
    Contrapartida orquestada por app contabilidad.
    """
    resolucion_dian = ResolucionDIANNestedSerializer(read_only=True)
    numero_documento_full = serializers.CharField(source='numero_documento', read_only=True)
    fecha = serializers.DateField(format='%Y-%m-%d', required=False, read_only=True)
    fecha_anulacion = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S', required=False, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    prefijo = serializers.CharField(source='resolucion_dian.prefijo', read_only=True)
    cuenta_gasto_uuid = serializers.UUIDField(allow_null=True, required=False)
    cuenta_gasto_label = serializers.SerializerMethodField()

    categoria_contable_display = serializers.CharField(source='get_categoria_contable_display', read_only=True)

    producto_relacionado = UUIDOrPKRelatedField(queryset=Producto.objects.all(), required=False, allow_null=True)
    servicio_relacionado = UUIDOrPKRelatedField(queryset=Servicio.objects.all(), required=False, allow_null=True)
    activo_relacionado = UUIDOrPKRelatedField(queryset=ActivoFijo.objects.all(), required=False, allow_null=True)

    producto_relacionado_nombre = serializers.CharField(source='producto_relacionado.nombre', read_only=True, allow_null=True)
    servicio_relacionado_nombre = serializers.CharField(source='servicio_relacionado.nombre', read_only=True, allow_null=True)
    activo_relacionado_nombre = serializers.CharField(source='activo_relacionado.nombre', read_only=True, allow_null=True)

    class Meta:
        model = DocumentoSoporte
        fields = (
            'id',
            'uuid',
            'empresa',
            'resolucion_dian',
            'proveedor',
            'prefijo',
            'consecutivo',
            'numero_documento_full',
            'fecha',
            'vendedor_nit',
            'vendedor_nombre',
            'vendedor_direccion',
            'vendedor_telefono',
            'numero_documento_proveedor',
            'categoria_contable',
            'categoria_contable_display',
            'descripcion',
            'observaciones',
            'subtotal',
            'total_retefuente',
            'total_reteica',
            'total_reteiva',
            'total',
            'adjunto',
            'activo',
            'anulado',
            'fecha_anulacion',
            'cuenta_gasto_uuid',
            'cuenta_gasto_label',
            'producto_relacionado',
            'servicio_relacionado',
            'activo_relacionado',
            'producto_relacionado_nombre',
            'servicio_relacionado_nombre',
            'activo_relacionado_nombre',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id', 'uuid', 'empresa', 'resolucion_dian', 'prefijo', 'consecutivo',
            'vendedor_nit', 'vendedor_nombre', 'vendedor_direccion', 'vendedor_telefono',
            'subtotal', 'total_retefuente', 'total_reteica', 'total_reteiva', 'total',
            'activo', 'anulado', 'fecha_anulacion', 'created_at', 'updated_at',
            'producto_relacionado_nombre', 'servicio_relacionado_nombre', 'activo_relacionado_nombre'
        )

    def get_cuenta_gasto_label(self, obj):
        if not obj.cuenta_gasto_uuid:
            return None
        from apps.tenant.contabilidad.services.selectors import CuentaContableSelector
        return CuentaContableSelector.get_label_by_uuid(
            empresa_id=obj.empresa_id,
            uuid=obj.cuenta_gasto_uuid
        )
    


# --- Alias para compatibilidad (v2.62.0) ---
GastoSerializer = DocumentoSoporteListSerializer
GastoListSerializer = DocumentoSoporteListSerializer
GastoDetailSerializer = DocumentoSoporteDetailSerializer
