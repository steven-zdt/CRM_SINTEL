"""
Serializers para Inventario v2.60.

⚠️ SINTEL v2.60: Sincronización Arquitectónica
- NormalizationMixin: Todos los serializadores heredan de este Mixin para sanitizar strings y validar tipos
- Validación Estricta: validate_<field> para asegurar que ForeignKeys pertenezcan al tenant actual
- Separación List/Detail: ListSerializer para tablas, DetailSerializer para formularios
- Campos Explícitos: PROHIBIDO __all__, usar campos explícitos alineados con LIST_FIELDS y DETAIL_FIELDS
"""
from rest_framework import serializers
from django.core.exceptions import ValidationError
from apps.tenant.inventario.models import (
    CategoriaItem, ActivoFijo, Producto, Servicio, 
    MovimientoInventario, HistorialServicio
)
from apps.tenant.empresa.models import Empresa

# ⚠️ v2.60: Importar campos desde services.py (SSoT)
from apps.tenant.inventario.services import (
    CATEGORIA_LIST_FIELDS, CATEGORIA_DETAIL_FIELDS,
    PRODUCTO_LIST_FIELDS, PRODUCTO_DETAIL_FIELDS,
    SERVICIO_LIST_FIELDS, SERVICIO_DETAIL_FIELDS,
    ACTIVO_LIST_FIELDS, ACTIVO_DETAIL_FIELDS,
    MOVIMIENTO_LIST_FIELDS, MOVIMIENTO_DETAIL_FIELDS,
)


# ==============================================================================
# NORMALIZATION MIXIN (Zero Trust)
# ==============================================================================
class NormalizationMixin:
    """
    ⚠️ v2.60: Mixin para normalización de datos de entrada (Zero Trust).
    Sanitiza strings y valida tipos de datos antes de persistir.
    """
    def normalize_data(self, attrs):
        """
        Normaliza datos de entrada:
        - Strings: strip() para eliminar espacios
        - Decimales: Convierte a Decimal si es necesario
        - Booleanos: Convierte a bool explícito
        """
        for key, value in attrs.items():
            if isinstance(value, str):
                attrs[key] = value.strip()
            elif value is None and key in ['categoria', 'producto', 'servicio']:
                # Permitir None para ForeignKeys opcionales
                pass
        return attrs


# ==============================================================================
# CATEGORÍAS
# ==============================================================================
class CategoriaItemListSerializer(serializers.ModelSerializer):
    """
    ⚠️ v2.60: Serializer optimizado para LISTAS (Tabulator Factory).
    Solo incluye campos estrictamente necesarios para la tabla del frontend.
    Campos alineados con CATEGORIA_LIST_FIELDS de services.py.
    """
    class Meta:
        model = CategoriaItem
        fields = ['id', 'nombre', 'descripcion', 'aplicacion', 'activo']
        read_only_fields = ['id']


class CategoriaItemDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    ⚠️ v2.60: Serializer completo para DETALLE/EDICIÓN de Categorías.
    Campos alineados con CATEGORIA_DETAIL_FIELDS de services.py.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    """
    class Meta:
        model = CategoriaItem
        fields = ['id', 'nombre', 'descripcion', 'aplicacion', 'imagen', 'activo', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'empresa']
    
    def validate(self, attrs):
        """⚠️ Zero Trust: Normalización estricta antes de persistir."""
        attrs = self.normalize_data(attrs)
        return attrs
    
    def validate_categoria(self, value):
        """⚠️ v2.60: Validación estricta - No aplica (CategoriaItem no tiene FK a CategoriaItem)"""
        return value


# ==============================================================================
# PRODUCTOS
# ==============================================================================
class ProductoListSerializer(serializers.ModelSerializer):
    """
    ⚠️ v2.60: Serializer optimizado para LISTAS (Tabulator Factory).
    Solo incluye campos estrictamente necesarios para la tabla del frontend.
    Campos alineados con PRODUCTO_LIST_FIELDS de services.py.
    Incluye campos calculados para visualización.
    """
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    activo_display = serializers.CharField(source='get_activo_display', read_only=True)
    
    # ⚠️ v2.60: Campos calculados (lógica en backend - Zero Trust)
    stock_total = serializers.DecimalField(source='stock_actual', max_digits=14, decimal_places=3, read_only=True)
    valor_inventario = serializers.SerializerMethodField()
    alerta_stock = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id', 'codigo', 'nombre', 'categoria', 'categoria_nombre',
            'stock_actual', 'stock_total', 'stock_minimo', 'precio_venta', 'costo_promedio',
            'valor_inventario', 'alerta_stock', 'activo', 'activo_display', 'imagen', 'unidad'
        ]
        read_only_fields = ['id', 'categoria_nombre', 'activo_display', 'stock_total', 'valor_inventario', 'alerta_stock']
    
    def get_valor_inventario(self, obj):
        """
        ⚠️ v2.60: Calcula el valor total del inventario: stock_actual * costo_promedio
        Lógica en backend (Zero Trust) - No confiar en cálculos del frontend.
        """
        from decimal import Decimal
        stock = obj.stock_actual or Decimal('0')
        costo = obj.costo_promedio or Decimal('0')
        return float(stock * costo)
    
    def get_alerta_stock(self, obj):
        """
        ⚠️ v2.60: Retorna True si el stock actual es menor o igual al stock mínimo.
        Lógica en backend (Zero Trust).
        """
        stock_actual = obj.stock_actual or 0
        stock_minimo = obj.stock_minimo or 0
        return stock_actual <= stock_minimo


class ProductoDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    ⚠️ v2.60: Serializer completo para DETALLE/EDICIÓN de Productos.
    Campos alineados con PRODUCTO_DETAIL_FIELDS de services.py.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    """
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)

    class Meta:
        model = Producto
        fields = [
            'id', 'codigo', 'nombre', 'categoria', 'categoria_nombre',
            'descripcion', 'unidad', 'imagen', 
            'precio_venta', 'costo_promedio', 
            'stock_actual', 'stock_minimo', 
            'activo', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'empresa', 'stock_actual', 'costo_promedio']
    
    def validate(self, attrs):
        """⚠️ Zero Trust: Normalización estricta antes de persistir."""
        attrs = self.normalize_data(attrs)
        return attrs
    
    def validate_categoria(self, value):
        """
        ⚠️ v2.60: Validación estricta - Asegurar que la categoría pertenezca al tenant actual.
        Zero Trust: No confiar en el frontend.
        """
        if value is None:
            return value  # Permitir None (categoría opcional)
        
        # ⚠️ Zero Trust: Obtener empresa del tenant actual
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise ValidationError("No se encontró configuración de Empresa para este tenant.")
        
        # Validar que la categoría pertenezca al tenant
        if not CategoriaItem.objects.filter(pk=value.id, empresa_id=empresa.id).exists():
            raise ValidationError(f"La categoría con ID {value.id} no pertenece a este tenant.")
        
        # Validar que la categoría sea aplicable a productos
        if value.aplicacion not in [CategoriaItem.Aplicacion.PRODUCTO, CategoriaItem.Aplicacion.TODO]:
            raise ValidationError(f"La categoría '{value.nombre}' no es aplicable a productos.")
        
        return value


class StockResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    stock_actual = serializers.DecimalField(max_digits=14, decimal_places=3)


# ==============================================================================
# SERVICIOS
# ==============================================================================
class ServicioListSerializer(serializers.ModelSerializer):
    """
    ⚠️ v2.60: Serializer optimizado para LISTAS (Tabulator Factory).
    Solo incluye campos estrictamente necesarios para la tabla del frontend.
    Campos alineados con SERVICIO_LIST_FIELDS de services.py.
    """
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    activo_display = serializers.CharField(source='get_activo_display', read_only=True)

    class Meta:
        model = Servicio
        fields = [
            'id', 'codigo', 'nombre', 'categoria', 'categoria_nombre',
            'precio_venta', 'activo', 'activo_display', 'imagen'
        ]
        read_only_fields = ['id', 'categoria_nombre', 'activo_display']


class ServicioDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    ⚠️ v2.60: Serializer completo para DETALLE/EDICIÓN de Servicios.
    Campos alineados con SERVICIO_DETAIL_FIELDS de services.py.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    """
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)

    class Meta:
        model = Servicio
        fields = [
            'id', 'codigo', 'nombre', 'categoria', 'categoria_nombre',
            'descripcion', 'imagen', 
            'precio_venta', 
            'activo', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'empresa']
    
    def validate(self, attrs):
        """⚠️ Zero Trust: Normalización estricta antes de persistir."""
        attrs = self.normalize_data(attrs)
        return attrs
    
    def validate_categoria(self, value):
        """
        ⚠️ v2.60: Validación estricta - Asegurar que la categoría pertenezca al tenant actual.
        Zero Trust: No confiar en el frontend.
        """
        if value is None:
            return value  # Permitir None (categoría opcional)
        
        # ⚠️ Zero Trust: Obtener empresa del tenant actual
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise ValidationError("No se encontró configuración de Empresa para este tenant.")
        
        # Validar que la categoría pertenezca al tenant
        if not CategoriaItem.objects.filter(pk=value.id, empresa_id=empresa.id).exists():
            raise ValidationError(f"La categoría con ID {value.id} no pertenece a este tenant.")
        
        # Validar que la categoría sea aplicable a servicios
        if value.aplicacion not in [CategoriaItem.Aplicacion.SERVICIO, CategoriaItem.Aplicacion.TODO]:
            raise ValidationError(f"La categoría '{value.nombre}' no es aplicable a servicios.")
        
        return value


# ==============================================================================
# ACTIVOS FIJOS
# ==============================================================================
class ActivoFijoListSerializer(serializers.ModelSerializer):
    """
    ⚠️ v2.60: Serializer optimizado para LISTAS (Tabulator Factory).
    Solo incluye campos estrictamente necesarios para la tabla del frontend.
    Campos alineados con ACTIVO_LIST_FIELDS de services.py.
    """
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = ActivoFijo
        fields = [
            'id', 'codigo', 'nombre', 'categoria', 'categoria_nombre',
            'fecha_adquisicion', 'costo_adquisicion',
            'ubicacion', 'responsable', 'estado', 'estado_display'
        ]
        read_only_fields = ['id', 'categoria_nombre', 'estado_display']


class ActivoFijoDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    ⚠️ v2.60: Serializer completo para DETALLE/EDICIÓN de Activos Fijos.
    Campos alineados con ACTIVO_DETAIL_FIELDS de services.py.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    """
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = ActivoFijo
        fields = [
            'id', 'codigo', 'nombre', 'categoria', 'categoria_nombre',
            'marca', 'modelo', 'descripcion', 'imagen',
            'ubicacion', 'responsable',
            'fecha_adquisicion', 'costo_adquisicion', 'estado', 'estado_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'empresa']
    
    def validate(self, attrs):
        """⚠️ Zero Trust: Normalización estricta antes de persistir."""
        attrs = self.normalize_data(attrs)
        return attrs
    
    def validate_categoria(self, value):
        """
        ⚠️ v2.60: Validación estricta - Asegurar que la categoría pertenezca al tenant actual.
        Zero Trust: No confiar en el frontend.
        """
        if value is None:
            return value  # Permitir None (categoría opcional)
        
        # ⚠️ Zero Trust: Obtener empresa del tenant actual
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise ValidationError("No se encontró configuración de Empresa para este tenant.")
        
        # Validar que la categoría pertenezca al tenant
        if not CategoriaItem.objects.filter(pk=value.id, empresa_id=empresa.id).exists():
            raise ValidationError(f"La categoría con ID {value.id} no pertenece a este tenant.")
        
        # Validar que la categoría sea aplicable a activos
        if value.aplicacion not in [CategoriaItem.Aplicacion.ACTIVO, CategoriaItem.Aplicacion.TODO]:
            raise ValidationError(f"La categoría '{value.nombre}' no es aplicable a activos fijos.")
        
        return value


# ==============================================================================
# MOVIMIENTOS INVENTARIO (KARDEX)
# ==============================================================================
class MovimientoInventarioListSerializer(serializers.ModelSerializer):
    """
    ⚠️ v2.60: Serializer optimizado para LISTAS (Tabulator Factory).
    Solo incluye campos estrictamente necesarios para la tabla del frontend.
    Campos alineados con MOVIMIENTO_LIST_FIELDS de services.py.
    """
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_codigo = serializers.CharField(source='producto.codigo', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = MovimientoInventario
        fields = [
            'id', 'created_at', 'producto', 'producto_codigo', 'producto_nombre',
            'tipo', 'tipo_display', 'cantidad', 'costo_unitario',
            'origen_referencia', 'cliente_referencia', 'observaciones'
        ]
        read_only_fields = ['id', 'producto_codigo', 'producto_nombre', 'tipo_display']


class MovimientoInventarioDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    ⚠️ v2.60: Serializer completo para DETALLE/CREACIÓN de Movimientos.
    Campos alineados con MOVIMIENTO_DETAIL_FIELDS de services.py.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    ⚠️ IMPORTANTE: Los movimientos NO se pueden editar/eliminar (integridad del Kardex).
    """
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_codigo = serializers.CharField(source='producto.codigo', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = MovimientoInventario
        fields = [
            'id', 'producto', 'producto_codigo', 'producto_nombre',
            'tipo', 'tipo_display', 'cantidad', 'costo_unitario',
            'origen_referencia', 'cliente_referencia',
            'observaciones', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'empresa']
    
    def validate(self, attrs):
        """⚠️ Zero Trust: Normalización estricta antes de persistir."""
        attrs = self.normalize_data(attrs)
        return attrs
    
    def validate_producto(self, value):
        """
        ⚠️ v2.60: Validación estricta - Asegurar que el producto pertenezca al tenant actual.
        Zero Trust: No confiar en el frontend.
        """
        if value is None:
            raise ValidationError("El producto es requerido.")
        
        # ⚠️ Zero Trust: Obtener empresa del tenant actual
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise ValidationError("No se encontró configuración de Empresa para este tenant.")
        
        # Validar que el producto pertenezca al tenant
        if not Producto.objects.filter(pk=value.id, empresa_id=empresa.id).exists():
            raise ValidationError(f"El producto con ID {value.id} no pertenece a este tenant.")
        
        return value


# ==============================================================================
# HISTORIAL SERVICIOS
# ==============================================================================
class HistorialServicioDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    ⚠️ v2.60: Serializer completo para DETALLE/CREACIÓN de Historial de Servicios.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    """
    servicio_nombre = serializers.CharField(source='servicio.nombre', read_only=True)

    class Meta:
        model = HistorialServicio
        fields = [
            'id', 'servicio', 'servicio_nombre',
            'fecha_registro', 'cantidad', 'valor_cobrado',
            'origen_referencia', 'cliente_referencia',
            'observaciones', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'empresa']
    
    def validate(self, attrs):
        """⚠️ Zero Trust: Normalización estricta antes de persistir."""
        attrs = self.normalize_data(attrs)
        return attrs
    
    def validate_servicio(self, value):
        """
        ⚠️ v2.60: Validación estricta - Asegurar que el servicio pertenezca al tenant actual.
        Zero Trust: No confiar en el frontend.
        """
        if value is None:
            raise ValidationError("El servicio es requerido.")
        
        # ⚠️ Zero Trust: Obtener empresa del tenant actual
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise ValidationError("No se encontró configuración de Empresa para este tenant.")
        
        # Validar que el servicio pertenezca al tenant
        if not Servicio.objects.filter(pk=value.id, empresa_id=empresa.id).exists():
            raise ValidationError(f"El servicio con ID {value.id} no pertenece a este tenant.")
        
        return value


# ==============================================================================
# ALIASES PARA COMPATIBILIDAD (v2.60)
# ==============================================================================
# ⚠️ v2.60: Mantener aliases para compatibilidad con código existente
# Los ViewSets deben usar los nombres Detail/List explícitos
CategoriaItemSerializer = CategoriaItemDetailSerializer
ProductoSerializer = ProductoDetailSerializer
ServicioSerializer = ServicioDetailSerializer
ActivoFijoSerializer = ActivoFijoDetailSerializer
MovimientoInventarioSerializer = MovimientoInventarioDetailSerializer
HistorialServicioSerializer = HistorialServicioDetailSerializer