"""
Serializers para la app contabilidad.

WARNING: v2.37: Alineado con LIST_FIELDS y DETAIL_FIELDS del service.
WARNING: NORMATIVA: Cumple con "Norma General de Exposición de Datos (Proyecto SINTEL)"
- Separación ListSerializer vs DetailSerializer
- Campos explícitos (NO __all__)
- Mínima exposición de datos

Referencia: https://www.django-rest-framework.org/api-guide/serializers/
"""
from rest_framework import serializers

from apps.tenant.contabilidad.models import (
    TIPO_COMPROBANTE_CHOICES,
    TIPO_TERCERO_CHOICES,
    AsientoContable,
    CatalogoMaestroNIIF,
    CuentaContable,
    MovimientoContable,
    PeriodoContable,
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
    cuenta_nombre = serializers.CharField(source='cuenta.nombre', read_only=True)
    cuenta_codigo = serializers.CharField(source='cuenta.codigo', read_only=True)
    
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


class AsientoContableDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para detalle de asiento contable.
    
    WARNING: v2.37: Alineado con ASIENTO_DETAIL_FIELDS del service.
    WARNING: NORMATIVA: Incluye campos de comprobante para trazabilidad.
    WARNING: IMPORTANTE: django-tenants maneja automáticamente el aislamiento por esquema.
    """
    movimientos = MovimientoContableDetailSerializer(many=True, read_only=True)
    
    # WARNING: NORMATIVA: Campos de comprobante (opcionales inicialmente para compatibilidad)
    tipo_comprobante = serializers.ChoiceField(
        choices=TIPO_COMPROBANTE_CHOICES,
        required=False,
        allow_null=True,
        allow_blank=True
    )
    numero_comprobante = serializers.CharField(
        max_length=50,
        required=False,
        allow_null=True,
        allow_blank=True
    )
    
    class Meta:
        model = AsientoContable
        fields = tuple(ASIENTO_DETAIL_FIELDS) + (
            'movimientos',
            'tipo_comprobante',
            'numero_comprobante'
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
