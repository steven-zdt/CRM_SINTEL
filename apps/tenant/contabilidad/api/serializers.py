"""
Serializers para la app contabilidad.

WARNING: v2.37: Alineado con LIST_FIELDS y DETAIL_FIELDS del service.
WARNING: NORMATIVA: Cumple con "Norma General de Exposición de Datos (Proyecto SINTEL)"
- Separación ListSerializer vs DetailSerializer
- Campos explícitos (NO __all__)
- Mínima exposición de datos

Referencia: https://www.django-rest-framework.org/api-guide/serializers/
"""
from decimal import Decimal
from rest_framework import serializers

from apps.tenant.contabilidad.models import (
    TIPO_COMPROBANTE_CHOICES,
    TIPO_TERCERO_CHOICES,
    AsientoContable,
    CatalogoMaestroNIIF,
    CuentaContable,
    MovimientoContable,
    PeriodoContable,
    TipoComprobante,
)
from apps.tenant.contabilidad.services.selectors import (
    ASIENTO_DETAIL_FIELDS,
    ASIENTO_LIST_FIELDS,
    CUENTA_DETAIL_FIELDS,
    CUENTA_LIST_FIELDS,
    PERIODO_DETAIL_FIELDS,
    PERIODO_LIST_FIELDS,
)


class CuentaContableListSerializer(serializers.ModelSerializer):
    """
    Serializer mínimo para listado de cuentas contables.
    
    WARNING: v2.37: Alineado con CUENTA_LIST_FIELDS del service.
    """
    class Meta:
        model = CuentaContable
        fields = CUENTA_LIST_FIELDS
        read_only_fields = ['id', 'created_at']


class CuentaContableDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para detalle de cuenta contable.
    
    WARNING: v2.37: Alineado con CUENTA_DETAIL_FIELDS del service.
    WARNING: v2.61: Incluye catalogo_referencia anidado para mostrar información del catálogo NIIF.
    """
    catalogo_referencia_detalle = serializers.SerializerMethodField()
    
    class Meta:
        model = CuentaContable
        fields = tuple(CUENTA_DETAIL_FIELDS) + ('catalogo_referencia', 'catalogo_referencia_detalle')
        read_only_fields = ['id', 'created_at']
    
    def get_catalogo_referencia_detalle(self, obj):
        """Retorna información detallada del catálogo NIIF si existe referencia."""
        try:
            if obj.catalogo_referencia:
                return CatalogoMaestroNIIFNestedSerializer(obj.catalogo_referencia).data
        except Exception as e:
            # WARNING: Manejar errores silenciosamente para evitar 500 en detalle
            print(f"Error al serializar catalogo_referencia: {e}")
        return None


class MovimientoContableListSerializer(serializers.ModelSerializer):
    """
    Serializer mínimo para listado de movimientos contables.
    
    WARNING: NORMATIVA: Incluye campos básicos de terceros para trazabilidad.
    """
    cuenta_nombre = serializers.CharField(source='cuenta.nombre', read_only=True)
    cuenta_codigo = serializers.CharField(source='cuenta.codigo', read_only=True)
    tercero_nit = serializers.CharField(read_only=True)
    tercero_razon_social = serializers.CharField(read_only=True)
    
    class Meta:
        model = MovimientoContable
        fields = (
            'id', 'asiento', 'cuenta', 'cuenta_nombre', 'cuenta_codigo',
            'orden', 'debe', 'haber', 'descripcion',
            'tipo_tercero', 'tercero_nit', 'tercero_razon_social'
        )
        read_only_fields = ['id']


class MovimientoContableDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para detalle de movimiento contable.
    
    WARNING: NORMATIVA: Incluye campos de terceros y tributarios según normativa colombiana.
    """
    cuenta_nombre = serializers.SerializerMethodField()
    cuenta_codigo = serializers.CharField(required=False, allow_null=True)
    
    # WARNING: NORMATIVA: Campos de terceros (opcionales inicialmente para compatibilidad)
    tipo_tercero = serializers.ChoiceField(
        choices=TIPO_TERCERO_CHOICES,
        required=False,
        allow_null=True,
        allow_blank=True
    )
    tercero_id = serializers.IntegerField(required=False, allow_null=True)
    tercero_nit = serializers.CharField(
        max_length=32,
        required=False,
        allow_null=True,
        allow_blank=True
    )
    tercero_razon_social = serializers.CharField(
        max_length=200,
        required=False,
        allow_null=True,
        allow_blank=True
    )
    
    # WARNING: NORMATIVA: Campos tributarios (read-only, se calculan automáticamente)
    base_iva = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    iva_generado = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    iva_descontable = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    retefuente = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    reteica = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    
    def get_cuenta_nombre(self, obj):
        if obj.cuenta:
            return obj.cuenta.nombre
        return obj.cuenta_codigo or "Cuenta no especificada"

    class Meta:
        model = MovimientoContable
        fields = (
            'id', 'asiento', 'cuenta', 'cuenta_nombre', 'cuenta_codigo',
            'orden', 'debe', 'haber', 'descripcion',
            # Campos nuevos de normativa
            'tipo_tercero', 'tercero_id', 'tercero_nit', 'tercero_razon_social',
            'base_iva', 'iva_generado', 'iva_descontable', 'retefuente', 'reteica'
        )
        read_only_fields = ['id', 'base_iva', 'iva_generado', 'iva_descontable', 'retefuente', 'reteica']


class CuentaContableListDTSerializer(serializers.ModelSerializer):
    """
    Serializer mínimo para DataTables server-side de cuentas contables.
    
    WARNING: v2.37: Alineado con CUENTA_LIST_FIELDS del service.
    WARNING: ELIMINADO v2.61: DataTables fue migrado a Tabulator. Este serializer se mantiene solo para compatibilidad histórica.
    """
    class Meta:
        model = CuentaContable
        fields = CUENTA_LIST_FIELDS
        read_only_fields = ("id", "created_at")


class AsientoContableListSerializer(serializers.ModelSerializer):
    """
    Serializer mínimo para listado de asientos contables (Tabulator v2.40).
    
    WARNING: v2.60: Alineado con ASIENTO_LIST_FIELDS del service.
    WARNING: OPTIMIZACIÓN: Solo campos necesarios para la tabla.
    WARNING: Zero Waste: Incluye campo aplanado movimientos_count para evitar N+1.
    """
    movimientos_count = serializers.SerializerMethodField()
    cuadratura = serializers.SerializerMethodField()
    
    class Meta:
        model = AsientoContable
        fields = tuple(ASIENTO_LIST_FIELDS) + ('movimientos_count', 'cuadratura')
        read_only_fields = ['id', 'total_debe', 'total_haber', 'created_at', 'movimientos_count', 'cuadratura']
    
    def get_movimientos_count(self, obj):
        """Conteo de movimientos usando prefetch_related para evitar N+1."""
        if hasattr(obj, 'movimientos'):
            # Si ya está prefetch_related, usar len()
            return obj.movimientos.count() if hasattr(obj.movimientos, 'count') else len(obj.movimientos)
        # Fallback: consulta directa (no debería ocurrir si qs_asiento_list usa prefetch_related)
        return obj.movimientos.count()
    
    def get_cuadratura(self, obj):
        """Indica si el asiento está cuadrado (debe == haber)."""
        diferencia = abs(float(obj.total_debe) - float(obj.total_haber))
        return diferencia < 0.01  # Tolerancia para errores de punto flotante


class AsientoContableListDTSerializer(serializers.ModelSerializer):
    """
    Serializer mínimo para DataTables server-side de asientos contables.
    
    WARNING: v2.37: Alineado con ASIENTO_LIST_FIELDS del service.
    WARNING: ELIMINADO v2.61: DataTables fue migrado a Tabulator. Este serializer se mantiene solo para compatibilidad histórica.
    """
    class Meta:
        model = AsientoContable
        fields = ASIENTO_LIST_FIELDS
        read_only_fields = ['id', 'total_debe', 'total_haber', 'created_at']


# ═══════════════════════════════════════════════════════════════
# TIPOS DE COMPROBANTE - Serializers (v3.5)
# ═══════════════════════════════════════════════════════════════

class TipoComprobanteListSerializer(serializers.ModelSerializer):
    """Serializer mínimo para listado de tipos de comprobante."""
    class Meta:
        model = TipoComprobante
        fields = ('id', 'uuid', 'codigo', 'nombre', 'prefijo', 'activa')
        read_only_fields = ('id', 'uuid')


class TipoComprobanteDetailSerializer(serializers.ModelSerializer):
    """Serializer completo para detalle de tipo de comprobante."""
    class Meta:
        model = TipoComprobante
        fields = ('id', 'uuid', 'codigo', 'nombre', 'prefijo', 'consecutivo_actual', 'activa', 'created_at')
        read_only_fields = ('id', 'uuid', 'created_at')


class AsientoContableDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para detalle de asiento contable.
    
    WARNING: v2.37: Alineado con ASIENTO_DETAIL_FIELDS del service.
    WARNING: NORMATIVA: Incluye campos de comprobante para trazabilidad.
    WARNING: IMPORTANTE: django-tenants maneja automáticamente el aislamiento por esquema.
    """
    tipo_comprobante_ref_detalle = TipoComprobanteListSerializer(source='tipo_comprobante_ref', read_only=True)
    movimientos = MovimientoContableDetailSerializer(many=True, read_only=True)
    
    class Meta:
        model = AsientoContable
        fields = tuple(ASIENTO_DETAIL_FIELDS) + (
            'movimientos',
            'tipo_comprobante_ref',
            'tipo_comprobante_ref_detalle',
        )
        read_only_fields = ['id', 'total_debe', 'total_haber', 'created_at', 'updated_at']
    
    def validate(self, data):
        """
        Validación básica del serializer.
        
        WARNING: v2.60: Service Layer Pattern - Validaciones complejas (cuadratura, periodos cerrados)
        se realizan en el servicio (create_asiento, update_asiento).
        El serializer solo valida estructura básica de datos.
        """
        # La validación de cuadratura y periodos cerrados se hace en el servicio
        return data


# ═══════════════════════════════════════════════════════════════
# PERIODOS CONTABLES - Serializers (v2.61)
# ═══════════════════════════════════════════════════════════════

class PeriodoContableListSerializer(serializers.ModelSerializer):
    """
    Serializer mínimo para listado de periodos contables.
    
    WARNING: v2.61: Alineado con PERIODO_LIST_FIELDS del service.
    """
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    
    class Meta:
        model = PeriodoContable
        fields = list(PERIODO_LIST_FIELDS) + ['estado_display', 'empresa_nombre']
        read_only_fields = ['id', 'uuid', 'created_at']


class PeriodoContableDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para detalle de periodo contable.
    
    WARNING: v2.61: Alineado con PERIODO_DETAIL_FIELDS del service.
    """
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    cerrado_por_nombre = serializers.SerializerMethodField()
    
    class Meta:
        model = PeriodoContable
        fields = list(PERIODO_DETAIL_FIELDS) + ['estado_display', 'empresa_nombre', 'cerrado_por_nombre']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']
    
    def get_cerrado_por_nombre(self, obj):
        """Retorna el nombre del usuario que cerró el periodo."""
        if obj.cerrado_por:
            return obj.cerrado_por.get_full_name() or obj.cerrado_por.username
        return None


# ═══════════════════════════════════════════════════════════════
# CATÁLOGO MAESTRO NIIF - Serializers
# ═══════════════════════════════════════════════════════════════

class CatalogoMaestroNIIFListSerializer(serializers.ModelSerializer):
    """
    Serializer mínimo para listado del Catálogo Maestro NIIF.
    
    WARNING: v2.61: Catálogo oficial NIIF Colombia (SSoT).
    WARNING: POLÍTICA: Solo lectura - Los datos se auto-setean desde choices.py.
    """
    tipo_cuenta = serializers.SerializerMethodField()
    
    class Meta:
        model = CatalogoMaestroNIIF
        fields = ('id', 'codigo', 'nombre', 'nivel', 'naturaleza', 'tipo_cuenta', 'activa')
        read_only_fields = ('id', 'nombre', 'nivel', 'naturaleza', 'tipo_cuenta', 'created_at')
    
    def get_tipo_cuenta(self, obj):
        """Retorna el tipo de cuenta basado en el primer dígito del código."""
        return obj.get_tipo_cuenta()


class CatalogoMaestroNIIFDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para detalle del Catálogo Maestro NIIF.
    
    WARNING: v2.61: Catálogo oficial NIIF Colombia (SSoT).
    WARNING: POLÍTICA: Solo lectura - Los datos se auto-setean desde choices.py.
    """
    tipo_cuenta = serializers.SerializerMethodField()
    cuentas_vinculadas_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CatalogoMaestroNIIF
        fields = (
            'id', 'codigo', 'nombre', 'nivel', 'naturaleza', 
            'tipo_cuenta', 'activa', 'created_at', 'cuentas_vinculadas_count'
        )
        read_only_fields = ('id', 'nombre', 'nivel', 'naturaleza', 'tipo_cuenta', 'created_at')
    
    def get_tipo_cuenta(self, obj):
        """Retorna el tipo de cuenta basado en el primer dígito del código."""
        return obj.get_tipo_cuenta()
    
    def get_cuentas_vinculadas_count(self, obj):
        """Retorna el número de cuentas del tenant vinculadas a esta cuenta del catálogo."""
        return obj.cuentas_vinculadas.count()


class CatalogoMaestroNIIFNestedSerializer(serializers.ModelSerializer):
    """
    Serializer anidado para mostrar información del catálogo en CuentaContable.

    WARNING: v2.61: Usado en CuentaContableDetailSerializer para mostrar la referencia NIIF.
    """
    tipo_cuenta = serializers.SerializerMethodField()

    class Meta:
        model = CatalogoMaestroNIIF
        fields = ('id', 'codigo', 'nombre', 'nivel', 'naturaleza', 'tipo_cuenta')
        read_only_fields = fields

    def get_tipo_cuenta(self, obj):
        """Retorna el tipo de cuenta basado en el primer dígito del código."""
        return obj.get_tipo_cuenta()


# ============================================================================
# SERIALIZERS FLUJO MANUAL ON-DEMAND
# ============================================================================

class DocumentoPendienteSerializer(serializers.Serializer):
    """Representacion unificada de Factura o DocumentoSoporte pendiente de contabilizar."""
    tipo_doc = serializers.CharField()
    app_label = serializers.CharField()
    modelo = serializers.CharField()
    documento_id = serializers.IntegerField()
    numero = serializers.CharField()
    fecha = serializers.DateField()
    tercero_nit = serializers.CharField()
    tercero_nombre = serializers.CharField()
    subtotal = serializers.DecimalField(max_digits=15, decimal_places=2)
    impuestos = serializers.DecimalField(max_digits=15, decimal_places=2)
    total = serializers.DecimalField(max_digits=15, decimal_places=2)
    estado = serializers.CharField()


class LineaManualInputSerializer(serializers.Serializer):
    """Una linea del asiento manual: cuenta PUC + montos DEBE/HABER."""
    cuenta_codigo = serializers.CharField(max_length=20)
    debe = serializers.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0'), min_value=Decimal('0')
    )
    haber = serializers.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0'), min_value=Decimal('0')
    )
    descripcion = serializers.CharField(max_length=255, allow_blank=True, required=False, default='')
    tercero_nit = serializers.CharField(max_length=32, allow_blank=True, required=False, default='')
    tercero_razon_social = serializers.CharField(
        max_length=200, allow_blank=True, required=False, default=''
    )

    def validate(self, data):
        if data.get('debe', Decimal('0')) == Decimal('0') and data.get('haber', Decimal('0')) == Decimal('0'):
            raise serializers.ValidationError('Cada linea debe tener debe > 0 o haber > 0.')
        if data.get('debe', Decimal('0')) > Decimal('0') and data.get('haber', Decimal('0')) > Decimal('0'):
            raise serializers.ValidationError('Una linea no puede tener debe Y haber simultaneamente.')
        return data


class ContabilizarManualInputSerializer(serializers.Serializer):
    """Payload del POST /contabilizar-manual/."""
    app_label = serializers.ChoiceField(choices=['facturas', 'gastos', 'empleados', 'inventario'])
    modelo = serializers.ChoiceField(choices=['Factura', 'DocumentoSoporte', 'Devengo', 'MovimientoInventario'])
    documento_id = serializers.IntegerField(min_value=1)
    documento_numero = serializers.CharField(max_length=50)
    tipo_comprobante_id = serializers.IntegerField(required=True)
    fecha = serializers.DateField()
    descripcion = serializers.CharField(max_length=500)
    lineas = LineaManualInputSerializer(many=True)

    def validate_lineas(self, value):
        if len(value) < 2:
            raise serializers.ValidationError('El asiento debe tener al menos 2 lineas.')
        return value


# ============================================================================
# ASISTENTE IA
# ============================================================================

class AsistenteIAInputSerializer(serializers.Serializer):
    """Payload del POST /asistente-ia/ — datos del documento para sugerir lineas."""
    app_label = serializers.ChoiceField(choices=['facturas', 'gastos', 'empleados', 'inventario'])
    modelo = serializers.ChoiceField(choices=['Factura', 'DocumentoSoporte', 'Devengo', 'MovimientoInventario'])
    documento_id = serializers.IntegerField(min_value=1)
    numero = serializers.CharField(max_length=50, allow_blank=True, default='')
    subtotal = serializers.DecimalField(max_digits=15, decimal_places=2)
    impuestos = serializers.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    total = serializers.DecimalField(max_digits=15, decimal_places=2)
    tercero_nit = serializers.CharField(max_length=30, allow_blank=True, default='')
    tercero_nombre = serializers.CharField(max_length=200, allow_blank=True, default='')


# ============================================================================
# REPORTES
# ============================================================================

class ReporteFinancieroInputSerializer(serializers.Serializer):
    """Parámetros para generar reportes (Balance, P&G)."""
    fecha_inicio = serializers.DateField(required=True)
    fecha_fin = serializers.DateField(required=True)

    def validate(self, data):
        if data['fecha_inicio'] > data['fecha_fin']:
            raise serializers.ValidationError("La fecha de inicio no puede ser mayor a la fecha fin.")
        return data

class BalancePruebaOutputSerializer(serializers.Serializer):
    """Estructura de una fila del Balance de Prueba."""
    codigo = serializers.CharField()
    nombre = serializers.CharField()
    nivel = serializers.IntegerField()
    saldo_anterior = serializers.DecimalField(max_digits=15, decimal_places=2)
    debito = serializers.DecimalField(max_digits=15, decimal_places=2)
    credito = serializers.DecimalField(max_digits=15, decimal_places=2)
    nuevo_saldo = serializers.DecimalField(max_digits=15, decimal_places=2)

class EstadoResultadosDetalleSerializer(serializers.Serializer):
    """Fila de detalle para ingresos, gastos o costos."""
    codigo = serializers.CharField()
    nombre = serializers.CharField()
    valor = serializers.DecimalField(max_digits=15, decimal_places=2)

class EstadoResultadosOutputSerializer(serializers.Serializer):
    """Estructura completa del Estado de Resultados."""
    ingresos = EstadoResultadosDetalleSerializer(many=True)
    gastos = EstadoResultadosDetalleSerializer(many=True)
    costos = EstadoResultadosDetalleSerializer(many=True)
    totales = serializers.DictField()


# ============================================================================
# RETENCIONES (v3.7.1)
# ============================================================================

class ConfiguracionRetencionesListSerializer(serializers.ModelSerializer):
    """
    Serializer mínimo para listado de configuraciones de retenciones.
    """
    clase_meta = None

    class Meta:
        from apps.tenant.contabilidad.models import ConfiguracionRetenciones
        model = ConfiguracionRetenciones
        fields = [
            'uuid', 'tipo_tercero', 'nit_tercero', 'tipo_retencion',
            'porcentaje_por_defecto', 'activa', 'naturaleza', 'created_at'
        ]
        read_only_fields = ['uuid', 'created_at']


class ConfiguracionRetencionesDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para detalle de configuración de retenciones.
    """
    cuenta_retencion_data = serializers.SerializerMethodField()

    class Meta:
        from apps.tenant.contabilidad.models import ConfiguracionRetenciones
        model = ConfiguracionRetenciones
        fields = [
            'uuid', 'tipo_tercero', 'nit_tercero', 'tipo_retencion',
            'porcentaje_por_defecto', 'cuenta_retencion', 'cuenta_retencion_data',
            'activa', 'naturaleza', 'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']

    def get_cuenta_retencion_data(self, obj):
        """Retorna datos de cuenta contable asociada."""
        if obj.cuenta_retencion:
            return {
                'uuid': str(obj.cuenta_retencion.uuid),
                'codigo': obj.cuenta_retencion.codigo,
                'nombre': obj.cuenta_retencion.nombre,
            }
        return None


class RetencionListSerializer(serializers.ModelSerializer):
    """
    Serializer mínimo para listado de retenciones.
    """
    class Meta:
        from apps.tenant.contabilidad.models import Retencion
        model = Retencion
        fields = [
            'uuid', 'tipo', 'porcentaje', 'monto', 'documento_origen_app',
            'documento_origen_modelo', 'documento_origen_id', 'reversada',
            'fecha_creacion'
        ]
        read_only_fields = ['uuid', 'fecha_creacion']


class RetencionDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para detalle de retención.
    """
    configuracion_data = serializers.SerializerMethodField()
    asiento_data = serializers.SerializerMethodField()

    class Meta:
        from apps.tenant.contabilidad.models import Retencion
        model = Retencion
        fields = [
            'uuid', 'tipo', 'porcentaje', 'base', 'monto',
            'documento_origen_app', 'documento_origen_modelo', 'documento_origen_id',
            'asiento_contable', 'asiento_data',
            'configuracion', 'configuracion_data',
            'aplicada_por_cliente', 'aplicada_por_proveedor',
            'reversada', 'retencion_reversada_por',
            'fecha_creacion', 'notas'
        ]
        read_only_fields = ['uuid', 'fecha_creacion']

    def get_configuracion_data(self, obj):
        """Retorna datos de configuración asociada."""
        if obj.configuracion:
            return {
                'uuid': str(obj.configuracion.uuid),
                'tipo_tercero': obj.configuracion.tipo_tercero,
                'nit_tercero': obj.configuracion.nit_tercero,
                'porcentaje': str(obj.configuracion.porcentaje_por_defecto),
            }
        return None

    def get_asiento_data(self, obj):
        """Retorna datos de asiento contable asociado."""
        if obj.asiento_contable:
            return {
                'uuid': str(obj.asiento_contable.uuid),
                'numero_asiento': obj.asiento_contable.numero_asiento,
                'fecha': obj.asiento_contable.fecha.isoformat(),
            }
        return None

# ============================================================================
# LIBRO DIARIO UNIFICADO (v3.7.1)
# ============================================================================

class CuentaAsignadaSerializer(serializers.Serializer):
    """Cuenta PUC ya asignada en el documento de origen (antes de contabilizar)."""
    concepto = serializers.CharField(read_only=True)
    uuid = serializers.CharField(read_only=True)
    codigo_puc = serializers.CharField(read_only=True)
    nombre = serializers.CharField(read_only=True)
    monto = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)


class MovimientoResumenSerializer(serializers.Serializer):
    """Resumen de un movimiento contable real (materializado en el asiento)."""
    cuenta_codigo = serializers.CharField(read_only=True)
    cuenta_nombre = serializers.CharField(read_only=True)
    debe = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    haber = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)


class LibroDiarioSerializer(serializers.Serializer):
    """
    Serializer unificado para el Libro Diario (Codigo de Comercio Art. 48).
    Consolida documentos de Facturas, Gastos y Nomina con su estado contable.
    Campos alineados con DocumentoEnriquecido DTO en extractores/base.py.
    """
    fecha = serializers.DateField(read_only=True)
    tipo_comprobante = serializers.CharField(read_only=True)
    tipo_comprobante_display = serializers.CharField(read_only=True)
    numero = serializers.CharField(read_only=True)
    tercero_nit = serializers.CharField(read_only=True)
    tercero_nombre = serializers.CharField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    impuestos = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    estado_contable = serializers.CharField(read_only=True)
    cuadra = serializers.BooleanField(read_only=True)
    asiento_uuid = serializers.CharField(read_only=True, allow_null=True)
    asiento_numero = serializers.CharField(read_only=True, allow_null=True)
    app_label = serializers.CharField(read_only=True)
    app_display = serializers.CharField(read_only=True)
    modelo = serializers.CharField(read_only=True)
    documento_id = serializers.IntegerField(read_only=True)

    # Cuentas PUC ya asignadas en el documento (antes de contabilizar)
    cuentas_asignadas = CuentaAsignadaSerializer(many=True, read_only=True)
    # Movimientos reales del asiento (solo si estado_contable = CONTABILIZADO)
    movimientos = MovimientoResumenSerializer(many=True, read_only=True)
