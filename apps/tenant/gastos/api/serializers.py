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
from apps.tenant.empresa.models import Sede

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
    DT-SEDE-01: sede para KPIs por sede.
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

    categoria_contable_display = serializers.CharField(source='get_categoria_contable_display', read_only=True)

    movimiento_inventario_uuid = serializers.UUIDField(required=False, allow_null=True)
    movimiento_referencia = serializers.DictField(read_only=True, allow_null=True)

    # DT-SEDE-01
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, allow_null=True)

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
            'movimiento_inventario_uuid',
            'movimiento_referencia',
            'sede_nombre',  # DT-SEDE-01
        )
        read_only_fields = fields


class DocumentoSoporteDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para evidencia legal y clasificacion operativa (v2.40).
    WARNING: v3.7.1 - Campo UUID opaco para integracion contable (?18 Pull Model).
    DT-SEDE-01: sede para KPIs por sede.
    """
    resolucion_dian = ResolucionDIANNestedSerializer(read_only=True)
    numero_documento_full = serializers.CharField(source='numero_documento', read_only=True)
    fecha = serializers.DateField(format='%Y-%m-%d', required=False, read_only=True)
    fecha_anulacion = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S', required=False, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    prefijo = serializers.CharField(source='resolucion_dian.prefijo', read_only=True)

    categoria_contable_display = serializers.CharField(source='get_categoria_contable_display', read_only=True)

    movimiento_inventario_uuid = serializers.UUIDField(required=False, allow_null=True)
    movimiento_referencia = serializers.DictField(read_only=True, allow_null=True)

    # DT-SEDE-01: sede para KPIs
    sede = UUIDOrPKRelatedField(
        queryset=Sede.objects.none(),
        required=False,
        allow_null=True,
        help_text='UUID de la sede donde se origina el gasto (opcional)',
    )
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, allow_null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        empresa_id = self.context.get('empresa_id') or self.context.get('request') and getattr(
            self.context['request'], 'empresa_id', None
        )
        if empresa_id and 'sede' in self.fields:
            self.fields['sede'].queryset = Sede.objects.filter(
                empresa_id=empresa_id
            ).only('id', 'uuid', 'nombre')

    def validate(self, attrs):
        attrs = super().validate(attrs)
        sede = attrs.get('sede')
        empresa_id = self.context.get('empresa_id')
        if sede and empresa_id and sede.empresa_id != empresa_id:
            raise serializers.ValidationError(
                {'sede': 'La sede seleccionada no pertenece a esta empresa.'}
            )
        # [OSF Fase F8] anti-IDOR ya verificaba "pertenece a la empresa" -
        # esto agrega "esta dentro del alcance organizacional del usuario".
        if sede:
            from apps.tenant.core.services.organizational_scope import sede_esta_en_alcance
            if not sede_esta_en_alcance(sede.id, self.context.get('request')):
                raise serializers.ValidationError(
                    {'sede': 'No tiene permiso para asignar esta sede (fuera de su alcance organizacional).'}
                )
        return attrs

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
            'movimiento_inventario_uuid',
            'movimiento_referencia',
            'sede',
            'sede_nombre',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id', 'uuid', 'empresa', 'resolucion_dian', 'prefijo', 'consecutivo',
            'vendedor_nit', 'vendedor_nombre', 'vendedor_direccion', 'vendedor_telefono',
            'subtotal', 'total_retefuente', 'total_reteica', 'total_reteiva', 'total',
            'activo', 'anulado', 'fecha_anulacion', 'sede_nombre', 'created_at', 'updated_at',
        )



# --- Alias para compatibilidad (v2.62.0) ---
GastoSerializer = DocumentoSoporteListSerializer
GastoListSerializer = DocumentoSoporteListSerializer
GastoDetailSerializer = DocumentoSoporteDetailSerializer
