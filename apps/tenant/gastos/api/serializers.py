"""
Serializers para la API de gastos.

⚠️ v2.40: Sistema de Documento Soporte Inmutable.
- Alineado con LIST_FIELDS y DETAIL_FIELDS del service.
- Campos aplanados para Tabulator (v2.40): 'ds_consecutivo', etc.
- Inmutabilidad estricta: Bloqueo de edición en campos monetarios y legales.
"""
from rest_framework import serializers
from ..models import Gasto, DocumentoSoporte, ResolucionDIAN
from django.utils.translation import gettext_lazy as _

class ResolucionDIANNestedSerializer(serializers.ModelSerializer):
    """
    Serializer anidado para ResolucionDIAN (v2.40).
    
    ⚠️ CORRECCIÓN: Asegura que las fechas se serialicen como cadenas ISO.
    ⚠️ CORRECCIÓN: Campos de fecha explícitamente declarados para evitar errores de utcoffset.
    ⚠️ ALINEADO: Incluye todos los campos del modelo ResolucionDIAN.
    """
    # ⚠️ CORRECCIÓN: DateField explícitos (no DateTimeField) porque el modelo usa DateField
    fecha_resolucion = serializers.DateField(format='%Y-%m-%d', required=False, read_only=True)
    fecha_inicio = serializers.DateField(format='%Y-%m-%d', required=False, read_only=True)
    fecha_fin = serializers.DateField(format='%Y-%m-%d', required=False, read_only=True)
    # ⚠️ CORRECCIÓN: DateTimeField explícitos para created_at y updated_at
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
    
    ⚠️ REGLA DE EXPOSICIÓN: Mínimo payload, máximo rendimiento.
    """
    fecha_resolucion = serializers.DateField(format='%Y-%m-%d', read_only=True)
    fecha_inicio = serializers.DateField(format='%Y-%m-%d', read_only=True)
    fecha_fin = serializers.DateField(format='%Y-%m-%d', read_only=True)
    conteo_documentos = serializers.SerializerMethodField()
    
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
    
    def get_conteo_documentos(self, obj):
        """Retorna el número de Documentos de Soporte asociados."""
        return obj.documentos_soporte.count()


class ResolucionDIANCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear resoluciones DIAN (v2.60).
    
    ⚠️ CORRECCIÓN: Maneja el valor "on" de los checkboxes HTML.
    ⚠️ INMUTABILIDAD: Las resoluciones son documentos legales y no deben editarse después de creadas.
    """
    fecha_resolucion = serializers.DateField(format='%Y-%m-%d', input_formats=['%Y-%m-%d', '%d-%m-%Y'])
    fecha_fin = serializers.DateField(format='%Y-%m-%d', input_formats=['%Y-%m-%d', '%d-%m-%Y'])
    vigente = serializers.BooleanField(required=False, default=True)
    
    class Meta:
        model = ResolucionDIAN
        fields = (
            'empresa',
            'numero_resolucion',
            'prefijo',
            'rango_desde',
            'rango_hasta',
            'fecha_resolucion',
            'fecha_fin',
            'clave_tecnica',
            'vigente',
        )
    
    def validate_vigente(self, value):
        """
        ⚠️ CORRECCIÓN v2.60: Maneja el valor "on" de los checkboxes HTML.
        Los checkboxes HTML envían "on" cuando están marcados, necesitamos convertirlo a booleano.
        """
        # Si viene como string "on" (checkbox marcado), convertir a True
        if isinstance(value, str):
            if value.lower() in ('on', 'true', '1', 'yes'):
                return True
            elif value.lower() in ('off', 'false', '0', 'no', ''):
                return False
        # Si ya es booleano, retornarlo tal cual
        return bool(value) if value is not None else True
    
    def validate(self, attrs):
        """
        Validación adicional: fecha_fin debe ser posterior a fecha_resolucion.
        """
        fecha_resolucion = attrs.get('fecha_resolucion')
        fecha_fin = attrs.get('fecha_fin')
        
        if fecha_resolucion and fecha_fin:
            if fecha_fin <= fecha_resolucion:
                raise serializers.ValidationError({
                    'fecha_fin': 'La fecha de fin debe ser posterior a la fecha de emisión (inicio).'
                })
        
        return attrs


class ResolucionDIANDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para detalle de resolución (v2.40).
    
    ⚠️ INMUTABILIDAD: Las resoluciones son documentos legales y no deben editarse.
    Este serializer es solo para lectura (read_only).
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
        """Retorna el número de Documentos de Soporte asociados."""
        return obj.documentos_soporte.count()
    
    def to_representation(self, instance):
        """
        Asegura que las fechas se serialicen como cadenas ISO.
        Previene TypeError: fromisoformat: argument must be str
        Previene AttributeError: 'datetime.date' object has no attribute 'utcoffset'
        
        ⚠️ CORRECCIÓN: DRF serializa automáticamente DateField a cadenas ISO,
        pero si por alguna razón recibe un objeto date, lo convierte explícitamente.
        Esto evita que DRF intente tratar objetos date como datetime (que tienen utcoffset).
        """
        data = super().to_representation(instance)
        # Convertir fechas a cadena si son objetos date (caso edge)
        # Esto previene el error 'datetime.date' object has no attribute 'utcoffset'
        from datetime import date, datetime
        for fecha_field in ['fecha_resolucion', 'fecha_inicio', 'fecha_fin']:
            if fecha_field in data and data[fecha_field] is not None:
                # Si es un objeto date, convertir a string ISO
                if isinstance(data[fecha_field], date) and not isinstance(data[fecha_field], datetime):
                    data[fecha_field] = data[fecha_field].isoformat()
        return data


class GastoListSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para Tabulator (v2.40).
    
    ⚠️ REGLA DE EXPOSICIÓN: Mínimo payload, máximo rendimiento.
    - Aplanamiento de campos para Tabulator ('ds_consecutivo', etc).
    - Incluye estado de anulación para lógica de UI.
    - Campos display para choices (texto legible).
    """
    # Campos aplanados para facilitar el acceso en el cliente (gastos.page.js)
    ds_consecutivo = serializers.IntegerField(source='documento_soporte.consecutivo', read_only=True)
    ds_prefijo = serializers.CharField(source='documento_soporte.prefijo', read_only=True)
    ds_numero_documento = serializers.CharField(source='documento_soporte.numero_documento', read_only=True)  # ⚠️ v2.40: Prefijo + Consecutivo completo
    ds_vendedor = serializers.CharField(source='documento_soporte.vendedor_nombre', read_only=True)
    # ⚠️ CORRECCIÓN: DateField (no DateTimeField) porque DocumentoSoporte.fecha es DateField
    ds_fecha = serializers.DateField(source='documento_soporte.fecha', format='%Y-%m-%d', read_only=True)
    ds_total = serializers.DecimalField(source='documento_soporte.total', max_digits=15, decimal_places=2, read_only=True)
    ds_activo = serializers.BooleanField(source='documento_soporte.activo', read_only=True)  # ⚠️ v2.40: Campo activo
    ds_anulado = serializers.BooleanField(source='documento_soporte.anulado', read_only=True)
    
    # ⚠️ Campos display para choices (texto legible para el frontend)
    centro_costo_display = serializers.CharField(source='get_centro_costo_display', read_only=True)
    categoria_contable_display = serializers.CharField(source='get_categoria_contable_display', read_only=True)

    class Meta:
        model = Gasto
        fields = (
            'id',
            'categoria_contable',
            'categoria_contable_display',
            'centro_costo',
            'centro_costo_display',
            'ds_consecutivo',
            'ds_prefijo',
            'ds_numero_documento',  # ⚠️ v2.40: Campo completo para mostrar en tabla (prefijo + consecutivo)
            'ds_vendedor',
            'ds_fecha',
            'ds_total',
            'ds_activo',  # ⚠️ v2.40: Campo activo
            'ds_anulado',
        )
        read_only_fields = fields


class DocumentoSoporteDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para evidencia legal (v2.40).
    
    ⚠️ ALINEADO: Incluye todos los campos del modelo DocumentoSoporte.
    ⚠️ CORRECCIÓN: Campos de fecha explícitamente declarados para evitar errores de utcoffset.
    """
    resolucion_dian = ResolucionDIANNestedSerializer(read_only=True)
    numero_documento_full = serializers.CharField(source='numero_documento', read_only=True)
    # ⚠️ CORRECCIÓN: DateField explícito (no DateTimeField) porque el modelo es DateField
    fecha = serializers.DateField(format='%Y-%m-%d', required=False, read_only=True)
    # ⚠️ CORRECCIÓN: DateTimeField explícito para fecha_anulacion (es DateTimeField en el modelo)
    fecha_anulacion = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S', required=False, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = DocumentoSoporte
        fields = (
            'id',
            'empresa',
            'resolucion_dian',
            'prefijo',
            'consecutivo',
            'numero_documento_full',
            'fecha',
            'vendedor_nit',
            'vendedor_nombre',
            'vendedor_direccion',
            'vendedor_telefono',
            'numero_factura_proveedor',
            'subtotal',
            'retefuente_porcentaje',  # ⚠️ v2.40: Porcentaje seleccionado de Retefuente
            'retefuente',  # ⚠️ v2.40: Valor calculado de Retefuente
            'reteica_porcentaje',  # ⚠️ v2.40: Porcentaje seleccionado de ReteICA
            'reteica',  # ⚠️ v2.40: Valor calculado de ReteICA
            'total',
            'adjunto',
            'activo',  # ⚠️ v2.40: Campo activo
            'anulado',
            'fecha_anulacion',
            'created_at',
            'updated_at',
        )
        # ⚠️ v2.40: Campos monetarios y legales son INMUTABLES
        read_only_fields = (
            'id', 'empresa', 'resolucion_dian', 'prefijo', 'consecutivo', 
            'subtotal', 'retefuente_porcentaje', 'retefuente', 'reteica_porcentaje', 'reteica', 'total', 
            'activo', 'anulado', 'fecha_anulacion', 'created_at', 'updated_at'
        )
    
    def to_representation(self, instance):
        """
        Asegura que las fechas se serialicen correctamente.
        Previene AttributeError: 'datetime.date' object has no attribute 'utcoffset'
        """
        data = super().to_representation(instance)
        # Convertir fecha (DateField) a string si es necesario
        from datetime import date, datetime
        if 'fecha' in data and data['fecha'] is not None:
            if isinstance(data['fecha'], date) and not isinstance(data['fecha'], datetime):
                data['fecha'] = data['fecha'].isoformat()
        return data


class GastoDetailSerializer(serializers.ModelSerializer):
    """
    Serializer de detalle que vincula Gasto con su evidencia legal.
    
    ⚠️ ALINEADO: Incluye todos los campos del modelo Gasto.
    ⚠️ CORRECCIÓN: Campos DateTimeField explícitamente declarados.
    ⚠️ Campos display para choices (texto legible para el frontend).
    """
    documento_soporte = DocumentoSoporteDetailSerializer(read_only=True)
    empresa = serializers.PrimaryKeyRelatedField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    # ⚠️ Campos display para choices (texto legible para el frontend)
    centro_costo_display = serializers.CharField(source='get_centro_costo_display', read_only=True)
    categoria_contable_display = serializers.CharField(source='get_categoria_contable_display', read_only=True)
    
    class Meta:
        model = Gasto
        fields = (
            'id',
            'empresa',
            'documento_soporte',
            'periodo',
            'centro_costo',
            'centro_costo_display',
            'categoria_contable',
            'categoria_contable_display',
            'descripcion',
            'observaciones',
            'created_at',
            'updated_at',
        )
        read_only_fields = ("empresa", "created_at", "updated_at")

    def validate_periodo(self, value):
        import re
        if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", value):
            raise serializers.ValidationError(_("Periodo inválido (esperado YYYY-MM)."))
        return value