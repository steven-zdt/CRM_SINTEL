"""
Serializers para la app contabilidad.

⚠️ v2.37: Alineado con LIST_FIELDS y DETAIL_FIELDS del service.
⚠️ NORMATIVA: Cumple con "Norma General de Exposición de Datos (Proyecto SINTEL)"
- Separación ListSerializer vs DetailSerializer
- Campos explícitos (NO __all__)
- Mínima exposición de datos

Referencia: https://www.django-rest-framework.org/api-guide/serializers/
"""
from rest_framework import serializers
from apps.tenant.contabilidad.models import (
    CuentaContable, 
    AsientoContable, 
    MovimientoContable,
    CatalogoMaestroNIIF
)
# Importar directamente desde services.py para evitar circularidad con services/__init__.py
import importlib.util
from pathlib import Path
import sys

# Cargar services.py directamente desde el archivo
# __file__ = apps/tenant/contabilidad/api/serializers.py
# parent.parent = apps/tenant/contabilidad/
services_py_path = Path(__file__).parent.parent / 'services.py'
if services_py_path.exists():
    module_name = 'apps.tenant.contabilidad.services_module'
    if module_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(module_name, services_py_path)
        services_module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = services_module
        spec.loader.exec_module(services_module)
    else:
        services_module = sys.modules[module_name]
    
    CUENTA_LIST_FIELDS = services_module.CUENTA_LIST_FIELDS
    CUENTA_DETAIL_FIELDS = services_module.CUENTA_DETAIL_FIELDS
    ASIENTO_LIST_FIELDS = services_module.ASIENTO_LIST_FIELDS
    ASIENTO_DETAIL_FIELDS = services_module.ASIENTO_DETAIL_FIELDS
else:
    raise ImportError(f"No se pudo cargar services.py desde {services_py_path}")


class CuentaContableListSerializer(serializers.ModelSerializer):
    """
    Serializer mínimo para listado de cuentas contables.
    
    ⚠️ v2.37: Alineado con CUENTA_LIST_FIELDS del service.
    """
    class Meta:
        model = CuentaContable
        fields = CUENTA_LIST_FIELDS
        read_only_fields = ['id', 'created_at']


class CuentaContableDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para detalle de cuenta contable.
    
    ⚠️ v2.37: Alineado con CUENTA_DETAIL_FIELDS del service.
    ⚠️ v2.61: Incluye catalogo_referencia anidado para mostrar información del catálogo NIIF.
    """
    catalogo_referencia_detalle = serializers.SerializerMethodField()
    
    class Meta:
        model = CuentaContable
        fields = tuple(CUENTA_DETAIL_FIELDS) + ('catalogo_referencia', 'catalogo_referencia_detalle')
        read_only_fields = ['id', 'created_at']
    
    def get_catalogo_referencia_detalle(self, obj):
        """Retorna información detallada del catálogo NIIF si existe referencia."""
        if obj.catalogo_referencia:
            return CatalogoMaestroNIIFNestedSerializer(obj.catalogo_referencia).data
        return None


class MovimientoContableListSerializer(serializers.ModelSerializer):
    """Serializer mínimo para listado de movimientos contables."""
    cuenta_nombre = serializers.CharField(source='cuenta.nombre', read_only=True)
    cuenta_codigo = serializers.CharField(source='cuenta.codigo', read_only=True)
    
    class Meta:
        model = MovimientoContable
        fields = (
            'id', 'asiento', 'cuenta', 'cuenta_nombre', 'cuenta_codigo',
            'orden', 'debe', 'haber', 'descripcion'
        )
        read_only_fields = ['id']


class MovimientoContableDetailSerializer(serializers.ModelSerializer):
    """Serializer completo para detalle de movimiento contable."""
    cuenta_nombre = serializers.CharField(source='cuenta.nombre', read_only=True)
    cuenta_codigo = serializers.CharField(source='cuenta.codigo', read_only=True)
    
    class Meta:
        model = MovimientoContable
        fields = (
            'id', 'asiento', 'cuenta', 'cuenta_nombre', 'cuenta_codigo',
            'orden', 'debe', 'haber', 'descripcion'
        )
        read_only_fields = ['id']


class CuentaContableListDTSerializer(serializers.ModelSerializer):
    """
    Serializer mínimo para DataTables server-side de cuentas contables.
    
    ⚠️ v2.37: Alineado con CUENTA_LIST_FIELDS del service.
    ⚠️ DEPRECATED: Usar CuentaContableListSerializer en su lugar.
    """
    class Meta:
        model = CuentaContable
        fields = CUENTA_LIST_FIELDS
        read_only_fields = ("id", "created_at")


class AsientoContableListSerializer(serializers.ModelSerializer):
    """
    Serializer mínimo para listado de asientos contables (Tabulator v2.40).
    
    ⚠️ v2.60: Alineado con ASIENTO_LIST_FIELDS del service.
    ⚠️ OPTIMIZACIÓN: Solo campos necesarios para la tabla.
    ⚠️ Zero Waste: Incluye campo aplanado movimientos_count para evitar N+1.
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
    
    ⚠️ v2.37: Alineado con ASIENTO_LIST_FIELDS del service.
    ⚠️ DEPRECATED: Usar AsientoContableListSerializer en su lugar.
    """
    class Meta:
        model = AsientoContable
        fields = ASIENTO_LIST_FIELDS
        read_only_fields = ['id', 'total_debe', 'total_haber', 'created_at']


class AsientoContableDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para detalle de asiento contable.
    
    ⚠️ v2.37: Alineado con ASIENTO_DETAIL_FIELDS del service.
    ⚠️ IMPORTANTE: django-tenants maneja automáticamente el aislamiento por esquema.
    """
    movimientos = MovimientoContableDetailSerializer(many=True, read_only=True)
    
    class Meta:
        model = AsientoContable
        fields = tuple(ASIENTO_DETAIL_FIELDS) + ('movimientos',)
        read_only_fields = ['id', 'total_debe', 'total_haber', 'created_at', 'updated_at']
    
    def validate(self, data):
        """
        Validación básica del serializer.
        
        ⚠️ v2.60: Service Layer Pattern - Validaciones complejas (cuadratura, periodos cerrados)
        se realizan en el servicio (create_asiento, update_asiento).
        El serializer solo valida estructura básica de datos.
        """
        # La validación de cuadratura y periodos cerrados se hace en el servicio
        return data


# ═══════════════════════════════════════════════════════════════
# CATÁLOGO MAESTRO NIIF - Serializers
# ═══════════════════════════════════════════════════════════════

class CatalogoMaestroNIIFListSerializer(serializers.ModelSerializer):
    """
    Serializer mínimo para listado del Catálogo Maestro NIIF.
    
    ⚠️ v2.61: Catálogo oficial NIIF Colombia (SSoT).
    ⚠️ POLÍTICA: Solo lectura - Los datos se auto-setean desde choices.py.
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
    
    ⚠️ v2.61: Catálogo oficial NIIF Colombia (SSoT).
    ⚠️ POLÍTICA: Solo lectura - Los datos se auto-setean desde choices.py.
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
    
    ⚠️ v2.61: Usado en CuentaContableDetailSerializer para mostrar la referencia NIIF.
    """
    tipo_cuenta = serializers.SerializerMethodField()
    
    class Meta:
        model = CatalogoMaestroNIIF
        fields = ('id', 'codigo', 'nombre', 'nivel', 'naturaleza', 'tipo_cuenta')
        read_only_fields = fields
    
    def get_tipo_cuenta(self, obj):
        """Retorna el tipo de cuenta basado en el primer dígito del código."""
        return obj.get_tipo_cuenta()
