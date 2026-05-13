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
        read_only_fields = ('id', 'empresa')
    
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
    WARNING: v3.7.1 - Campo UUID opaco para integracion contable (§18 Pull Model).
    """
    ds_consecutivo = serializers.IntegerField(source='consecutivo', read_only=True)
    ds_prefijo = serializers.SerializerMethodField()
    ds_numero_documento = serializers.SerializerMethodField()
    ds_vendedor = serializers.CharField(source='proveedor.razon_social', read_only=True)
    ds_fecha = serializers.DateField(source='fecha', format='%Y-%m-%d', read_only=True)
    ds_total = serializers.DecimalField(source='total', max_digits=15, decimal_places=2, read_only=True)
    ds_activo = serializers.BooleanField(source='activo', read_only=True)
    ds_anulado = serializers.BooleanField(source='anulado', read_only=True)
    ds_numero_documento_proveedor = serializers.CharField(source='numero_documento_proveedor', read_only=True)
    cuenta_gasto_uuid = serializers.UUIDField(allow_null=True, read_only=True)

    categoria_contable_display = serializers.CharField(source='get_categoria_contable_display', read_only=True)

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
            'categoria_contable',
            'categoria_contable_display',
            'descripcion',
            'ds_consecutivo',
            'ds_prefijo',
            'ds_numero_documento',
            'ds_vendedor',
            'ds_fecha',
            'ds_total',
            'ds_activo',
            'ds_anulado',
            'ds_numero_documento_proveedor',
            'cuenta_gasto_uuid',
        )
        read_only_fields = fields


class DocumentoSoporteDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para evidencia legal y clasificacion operativa (v2.40).
    WARNING: v3.7.1 - Campo UUID opaco para integracion contable (§18 Pull Model).
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

    categoria_contable_display = serializers.CharField(source='get_categoria_contable_display', read_only=True)

    class Meta:
        model = DocumentoSoporte
        fields = (
            'id',
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
            'retefuente_porcentaje',
            'retefuente',
            'reteica_porcentaje',
            'reteica',
            'total',
            'adjunto',
            'activo',
            'anulado',
            'fecha_anulacion',
            'cuenta_gasto_uuid',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id', 'empresa', 'resolucion_dian', 'prefijo', 'consecutivo', 
            'vendedor_nit', 'vendedor_nombre', 'vendedor_direccion', 'vendedor_telefono',
            'subtotal', 'retefuente_porcentaje', 'retefuente', 'reteica_porcentaje', 'reteica', 'total', 
            'activo', 'anulado', 'fecha_anulacion', 'created_at', 'updated_at'
        )
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        from datetime import date, datetime
        if 'fecha' in data and data['fecha'] is not None:
            if isinstance(data['fecha'], date) and not isinstance(data['fecha'], datetime):
                data['fecha'] = data['fecha'].isoformat()
        return data


# --- Alias para compatibilidad (v2.62.0) ---
GastoSerializer = DocumentoSoporteListSerializer
GastoListSerializer = DocumentoSoporteListSerializer
GastoDetailSerializer = DocumentoSoporteDetailSerializer
