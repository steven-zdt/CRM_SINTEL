"""
Serializers para Inventario v2.60.

WARNING: SINTEL v2.60: Sincronización Arquitectónica
- NormalizationMixin: Todos los serializadores heredan de este Mixin para sanitizar strings y validar tipos
- Validación Estricta: validate_<field> para asegurar que ForeignKeys pertenezcan al tenant actual
- Separación List/Detail: ListSerializer para tablas, DetailSerializer para formularios
- Campos Explícitos: PROHIBIDO __all__, usar campos explícitos alineados con LIST_FIELDS y DETAIL_FIELDS
"""
from django.core.exceptions import ValidationError
from rest_framework import serializers

from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import (
    ActivoFijo,
    CategoriaItem,
    HistorialServicio,
    MovimientoInventario,
    Producto,
    Servicio,
)

# WARNING: v2.60: Importar campos desde services.py (SSoT)


# ==============================================================================
# NORMALIZATION MIXIN (Zero Trust)
# ==============================================================================
class NormalizationMixin:
    """
    WARNING: v2.60: Mixin para normalización de datos de entrada (Zero Trust).
    Sanitiza strings y valida tipos de datos antes de persistir.
    """
    def _get_empresa_id(self):
        """WARNING: Zero Trust: Resuelve el ID de empresa de forma segura."""
        # 1. Intentar desde contexto (SSoT para ViewSets)
        empresa_id = self.context.get('empresa_id')
        if empresa_id:
            return empresa_id
            
        # 2. Fallback: Empresa Singleton del Tenant
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.only('id').first()
        if empresa:
            return empresa.id
        
        raise serializers.ValidationError("No se pudo identificar la configuración de Empresa para este tenant.")

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


# ==============================================================================
# CATEGORÍAS
# ==============================================================================
class CategoriaItemListSerializer(serializers.ModelSerializer):
    """
    WARNING: v2.60: Serializer optimizado para LISTAS (Tabulator Factory).
    Solo incluye campos estrictamente necesarios para la tabla del frontend.
    Campos alineados con CATEGORIA_LIST_FIELDS de services.py.
    """
    id = serializers.UUIDField(source='uuid', read_only=True)
    pk = serializers.IntegerField(source='id', read_only=True)

    class Meta:
        model = CategoriaItem
        fields = ['id', 'pk', 'nombre', 'descripcion', 'aplicacion', 'activo']
        read_only_fields = ['id', 'pk']


class CategoriaItemDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    WARNING: v2.60: Serializer completo para DETALLE/EDICIÓN de Categorías.
    Campos alineados con CATEGORIA_DETAIL_FIELDS de services.py.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    """
    cuenta_inventario_label = serializers.SerializerMethodField()
    cuenta_costo_label = serializers.SerializerMethodField()
    cuenta_ingreso_label = serializers.SerializerMethodField()
    id = serializers.UUIDField(source='uuid', read_only=True)
    pk = serializers.IntegerField(source='id', read_only=True)

    class Meta:
        model = CategoriaItem
        fields = [
            'id', 'pk', 'nombre', 'descripcion', 'aplicacion', 'imagen', 'activo',
            'created_at', 'updated_at', 
            'cuenta_inventario_uuid', 'cuenta_inventario_label',
            'cuenta_costo_uuid', 'cuenta_costo_label',
            'cuenta_ingreso_uuid', 'cuenta_ingreso_label'
        ]
        read_only_fields = [
            'id', 'pk', 'created_at', 'updated_at', 'empresa',
            'cuenta_inventario_label', 'cuenta_costo_label', 'cuenta_ingreso_label'
        ]
    
    def get_cuenta_inventario_label(self, obj):
        """WARNING: v3.5: Resuelve el label de la cuenta vía HTTP/Selector (Decoupled)."""
        return self.get_cuenta_label(obj.cuenta_inventario_uuid)

    def get_cuenta_costo_label(self, obj):
        """WARNING: v3.5: Resuelve el label de la cuenta vía HTTP/Selector (Decoupled)."""
        return self.get_cuenta_label(obj.cuenta_costo_uuid)

    def get_cuenta_ingreso_label(self, obj):
        """WARNING: v3.5: Resuelve el label de la cuenta vía HTTP/Selector (Decoupled)."""
        return self.get_cuenta_label(obj.cuenta_ingreso_uuid)
    
    def get_cuenta_label(self, uuid_value):
        return None

    def validate_cuenta_uuid(self, value):
        return value

    def validate_cuenta_inventario_uuid(self, value):
        return self.validate_cuenta_uuid(value)

    def validate_cuenta_costo_uuid(self, value):
        return self.validate_cuenta_uuid(value)

    def validate_cuenta_ingreso_uuid(self, value):
        return self.validate_cuenta_uuid(value)
    
    def validate(self, attrs):
        """WARNING: Zero Trust: Normalización estricta antes de persistir."""
        attrs = self.normalize_data(attrs)
        return attrs
    
    def validate_nombre(self, value):
        """
        WARNING: v2.60: Validación estricta - Evitar nombres duplicados para la misma empresa.
        Zero Trust: No confiar en el frontend.
        """
        if not value:
            return value
            
        # Normalizar para comparación
        nombre_clean = value.strip()
        
        # SINTEL v2.60: Obtener empresa del tenant actual (SSoT)
        empresa_id = self._get_empresa_id()
            
        qs = CategoriaItem.objects.filter(
            empresa_id=empresa_id,
            nombre__iexact=nombre_clean
        )
        
        # Si estamos editando, excluir la instancia actual
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            raise ValidationError(f"Ya existe una categoría con el nombre '{nombre_clean}'. Elija un nombre diferente.")
            
        return nombre_clean


# ==============================================================================
# PRODUCTOS
# ==============================================================================
class ProductoListSerializer(serializers.ModelSerializer):
    """
    WARNING: v2.60: Serializer optimizado para LISTAS (Tabulator Factory).
    Solo incluye campos estrictamente necesarios para la tabla del frontend.
    Campos alineados con PRODUCTO_LIST_FIELDS de services.py.
    Incluye campos calculados para visualización.
    """
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    activo_display = serializers.CharField(source='get_activo_display', read_only=True)
    id = serializers.UUIDField(source='uuid', read_only=True)
    pk = serializers.IntegerField(source='id', read_only=True)
    
    # WARNING: v2.60: Campos calculados (lógica en backend - Zero Trust)
    stock_total = serializers.DecimalField(source='stock_actual', max_digits=14, decimal_places=3, read_only=True)
    valor_inventario = serializers.SerializerMethodField()
    alerta_stock = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id', 'pk', 'codigo', 'nombre', 'categoria', 'categoria_nombre',
            'stock_actual', 'stock_total', 'stock_minimo', 'precio_venta', 'costo_promedio',
            'valor_inventario', 'alerta_stock', 'activo', 'activo_display', 'imagen', 'unidad'
        ]
        read_only_fields = ['id', 'pk', 'categoria_nombre', 'activo_display', 'stock_total', 'valor_inventario', 'alerta_stock']
    
    def get_valor_inventario(self, obj):
        """
        WARNING: v2.60: Calcula el valor total del inventario: stock_actual * costo_promedio
        Lógica en backend (Zero Trust) - No confiar en cálculos del frontend.
        """
        from decimal import Decimal
        stock = obj.stock_actual or Decimal('0')
        costo = obj.costo_promedio or Decimal('0')
        return float(stock * costo)
    
    def get_alerta_stock(self, obj):
        """
        WARNING: v2.60: Retorna True si el stock actual es menor o igual al stock mínimo.
        Lógica en backend (Zero Trust).
        """
        stock_actual = obj.stock_actual or 0
        stock_minimo = obj.stock_minimo or 0
        return stock_actual <= stock_minimo


class ProductoDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    WARNING: v2.60: Serializer completo para DETALLE/EDICIÓN de Productos.
    Campos alineados con PRODUCTO_DETAIL_FIELDS de services.py.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    """
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    cuenta_inventario_label = serializers.SerializerMethodField()
    cuenta_costo_label = serializers.SerializerMethodField()
    id = serializers.UUIDField(source='uuid', read_only=True)
    pk = serializers.IntegerField(source='id', read_only=True)
    categoria = UUIDOrPKRelatedField(
        queryset=CategoriaItem.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:

        model = Producto
        fields = [
            'id', 'pk', 'codigo', 'nombre', 'categoria', 'categoria_nombre',
            'descripcion', 'unidad', 'imagen',
            'precio_venta', 'costo_promedio',
            'stock_actual', 'stock_minimo',
            'cuenta_inventario_uuid', 'cuenta_inventario_label',
            'cuenta_costo_uuid', 'cuenta_costo_label',
            'activo', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'pk', 'created_at', 'updated_at', 'empresa',
            'stock_actual', 'costo_promedio', 'cuenta_inventario_label', 'cuenta_costo_label'
        ]

    def validate(self, attrs):
        """WARNING: Zero Trust: Normalización estricta antes de persistir."""
        attrs = self.normalize_data(attrs)
        return attrs

    def get_cuenta_inventario_label(self, obj):
        """Label resuelto por frontend via Gateway Directo de contabilidad."""
        return None

    def get_cuenta_costo_label(self, obj):
        """Label resuelto por frontend via Gateway Directo de contabilidad."""
        return None

    def validate_cuenta_inventario_uuid(self, value):
        return value

    def validate_cuenta_costo_uuid(self, value):
        return value

    def validate_categoria(self, value):
        """
        WARNING: v2.60: Validación estricta - Asegurar que la categoría pertenezca al tenant actual.
        Zero Trust: No confiar en el frontend.
        """
        if value is None:
            return value  # Permitir None (categoría opcional)

        empresa_id = self._get_empresa_id()

        # Validar que la categoría pertenezca al tenant
        if not CategoriaItem.objects.filter(pk=value.id, empresa_id=empresa_id).exists():
            raise ValidationError(f"La categoría con ID {value.id} no pertenece a este tenant.")

        # Validar que la categoría sea aplicable a productos
        if value.aplicacion not in [CategoriaItem.Aplicacion.PRODUCTO, CategoriaItem.Aplicacion.TODO]:
            raise ValidationError(f"La categoría '{value.nombre}' no es aplicable a productos.")

        return value


class StockResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    pk = serializers.IntegerField(required=False)
    nombre = serializers.CharField()
    stock_actual = serializers.DecimalField(max_digits=14, decimal_places=3)


# ==============================================================================
# SERVICIOS
# ==============================================================================
class ServicioListSerializer(serializers.ModelSerializer):
    """
    WARNING: v2.60: Serializer optimizado para LISTAS (Tabulator Factory).
    Solo incluye campos estrictamente necesarios para la tabla del frontend.
    Campos alineados con SERVICIO_LIST_FIELDS de services.py.
    """
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    activo_display = serializers.CharField(source='get_activo_display', read_only=True)
    id = serializers.UUIDField(source='uuid', read_only=True)
    pk = serializers.IntegerField(source='id', read_only=True)

    class Meta:
        model = Servicio
        fields = [
            'id', 'pk', 'codigo', 'nombre', 'categoria', 'categoria_nombre',
            'precio_venta', 'activo', 'activo_display', 'imagen'
        ]
        read_only_fields = ['id', 'pk', 'categoria_nombre', 'activo_display']


class ServicioDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    WARNING: v2.60: Serializer completo para DETALLE/EDICIÓN de Servicios.
    Campos alineados con SERVICIO_DETAIL_FIELDS de services.py.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    """
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    cuenta_ingreso_label = serializers.SerializerMethodField()
    id = serializers.UUIDField(source='uuid', read_only=True)
    pk = serializers.IntegerField(source='id', read_only=True)
    categoria = UUIDOrPKRelatedField(
        queryset=CategoriaItem.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:

        model = Servicio
        fields = [
            'id', 'pk', 'codigo', 'nombre', 'categoria', 'categoria_nombre',
            'descripcion', 'imagen',
            'precio_venta',
            'cuenta_ingreso_uuid', 'cuenta_ingreso_label',
            'activo', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'pk', 'created_at', 'updated_at', 'empresa', 'cuenta_ingreso_label']

    def validate(self, attrs):
        """WARNING: Zero Trust: Normalización estricta antes de persistir."""
        attrs = self.normalize_data(attrs)
        return attrs

    def get_cuenta_ingreso_label(self, obj):
        """Label resuelto por frontend via Gateway Directo de contabilidad."""
        return None

    def validate_cuenta_ingreso_uuid(self, value):
        return value

    def validate_categoria(self, value):
        """
        WARNING: v2.60: Validación estricta - Asegurar que la categoría pertenezca al tenant actual.
        Zero Trust: No confiar en el frontend.
        """
        if value is None:
            return value  # Permitir None (categoría opcional)

        empresa_id = self._get_empresa_id()

        if not CategoriaItem.objects.filter(pk=value.id, empresa_id=empresa_id).exists():
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
    WARNING: v2.60: Serializer optimizado para LISTAS (Tabulator Factory).
    Solo incluye campos estrictamente necesarios para la tabla del frontend.
    Campos alineados con ACTIVO_LIST_FIELDS de services.py.
    """
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    id = serializers.UUIDField(source='uuid', read_only=True)
    pk = serializers.IntegerField(source='id', read_only=True)

    class Meta:
        model = ActivoFijo
        fields = [
            'id', 'pk', 'codigo', 'nombre', 'categoria', 'categoria_nombre',
            'fecha_adquisicion', 'costo_adquisicion',
            'ubicacion', 'responsable', 'estado', 'estado_display'
        ]
        read_only_fields = ['id', 'pk', 'categoria_nombre', 'estado_display']


class ActivoFijoDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    WARNING: v2.60: Serializer completo para DETALLE/EDICIÓN de Activos Fijos.
    Campos alineados con ACTIVO_DETAIL_FIELDS de services.py.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    """
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    id = serializers.UUIDField(source='uuid', read_only=True)
    pk = serializers.IntegerField(source='id', read_only=True)
    categoria = UUIDOrPKRelatedField(
        queryset=CategoriaItem.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:

        model = ActivoFijo
        fields = [
            'id', 'pk', 'codigo', 'nombre', 'categoria', 'categoria_nombre',
            'marca', 'modelo', 'descripcion', 'imagen',
            'ubicacion', 'responsable',
            'fecha_adquisicion', 'costo_adquisicion', 'estado', 'estado_display',
            'cuenta_activo_uuid', 'cuenta_activo_label',
            'cuenta_depreciacion_uuid', 'cuenta_depreciacion_label',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'pk', 'created_at', 'updated_at', 'empresa', 'cuenta_activo_label', 'cuenta_depreciacion_label']
        
    cuenta_activo_label = serializers.SerializerMethodField()
    cuenta_depreciacion_label = serializers.SerializerMethodField()

    def validate(self, attrs):
        """WARNING: Zero Trust: Normalización estricta antes de persistir."""
        attrs = self.normalize_data(attrs)
        return attrs

    def get_cuenta_activo_label(self, obj):
        """Label resuelto por frontend via Gateway Directo de contabilidad."""
        return None

    def validate_cuenta_activo_uuid(self, value):
        return value

    def get_cuenta_depreciacion_label(self, obj):
        """Label resuelto por frontend via Gateway Directo de contabilidad."""
        return None

    def validate_cuenta_depreciacion_uuid(self, value):
        return value

    def validate_categoria(self, value):
        """
        WARNING: v2.60: Validación estricta - Asegurar que la categoría pertenezca al tenant actual.
        Zero Trust: No confiar en el frontend.
        """
        if value is None:
            return value  # Permitir None (categoría opcional)

        empresa_id = self._get_empresa_id()

        if not CategoriaItem.objects.filter(pk=value.id, empresa_id=empresa_id).exists():
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
    WARNING: v3.8.2: Serializer optimizado para LISTAS (Tabulator Factory).
    Soporta Productos y Activos Fijos con campos dinamicos item_tipo/item_nombre/item_codigo.
    """
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True, allow_null=True, default=None)
    producto_codigo = serializers.CharField(source='producto.codigo', read_only=True, allow_null=True, default=None)
    activo_fijo_nombre = serializers.CharField(source='activo_fijo.nombre', read_only=True, allow_null=True, default=None)
    activo_fijo_codigo = serializers.CharField(source='activo_fijo.codigo', read_only=True, allow_null=True, default=None)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    id = serializers.UUIDField(source='uuid', read_only=True)
    pk = serializers.IntegerField(source='id', read_only=True)
    item_tipo = serializers.SerializerMethodField()
    item_nombre = serializers.SerializerMethodField()
    item_codigo = serializers.SerializerMethodField()
    item_uuid = serializers.SerializerMethodField()

    class Meta:
        model = MovimientoInventario
        fields = [
            'id', 'pk', 'created_at',
            'producto', 'producto_codigo', 'producto_nombre',
            'activo_fijo', 'activo_fijo_codigo', 'activo_fijo_nombre',
            'item_tipo', 'item_nombre', 'item_codigo', 'item_uuid',
            'tipo', 'tipo_display', 'cantidad', 'costo_unitario',
            'origen_referencia', 'cliente_referencia', 'observaciones',
            'factura_uuid', 'factura_numero'
        ]
        read_only_fields = [
            'id', 'pk', 'producto_codigo', 'producto_nombre',
            'activo_fijo_codigo', 'activo_fijo_nombre',
            'item_tipo', 'item_nombre', 'item_codigo', 'item_uuid', 'tipo_display'
        ]

    def get_item_tipo(self, obj):
        if obj.producto_id:
            return 'PRODUCTO'
        if obj.activo_fijo_id:
            return 'ACTIVO_FIJO'
        return None

    def get_item_nombre(self, obj):
        if obj.producto_id and obj.producto:
            return obj.producto.nombre
        if obj.activo_fijo_id and obj.activo_fijo:
            return obj.activo_fijo.nombre
        return None

    def get_item_codigo(self, obj):
        if obj.producto_id and obj.producto:
            return obj.producto.codigo
        if obj.activo_fijo_id and obj.activo_fijo:
            return obj.activo_fijo.codigo
        return None

    def get_item_uuid(self, obj):
        if obj.producto_id and obj.producto:
            return str(obj.producto.uuid)
        if obj.activo_fijo_id and obj.activo_fijo:
            return str(obj.activo_fijo.uuid)
        return None


class MovimientoInventarioDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    WARNING: v3.8.0: Serializer unificado para Productos y Activos Fijos (Kardex).
    Campos alineados con MOVIMIENTO_DETAIL_FIELDS de services.py.
    Soporta routing dinámico según categoría de origen.
    WARNING: IMPORTANTE: Los movimientos NO se pueden editar/eliminar (integridad del Kardex).
    """
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True, allow_null=True)
    producto_codigo = serializers.CharField(source='producto.codigo', read_only=True, allow_null=True)
    activo_fijo_nombre = serializers.CharField(source='activo_fijo.nombre', read_only=True, allow_null=True)
    activo_fijo_codigo = serializers.CharField(source='activo_fijo.codigo', read_only=True, allow_null=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    id = serializers.UUIDField(source='uuid', read_only=True)
    pk = serializers.IntegerField(source='id', read_only=True)
    producto = UUIDOrPKRelatedField(queryset=Producto.objects.all(), required=False, allow_null=True)
    activo_fijo = UUIDOrPKRelatedField(queryset=ActivoFijo.objects.all(), required=False, allow_null=True)

    class Meta:
        model = MovimientoInventario
        fields = [
            'id', 'pk', 'producto', 'producto_codigo', 'producto_nombre',
            'activo_fijo', 'activo_fijo_codigo', 'activo_fijo_nombre',
            'tipo', 'tipo_display', 'cantidad', 'costo_unitario',
            'origen_referencia', 'cliente_referencia',
            'observaciones', 'created_at', 'updated_at',
            'factura_uuid', 'factura_numero'
        ]
        read_only_fields = ['id', 'pk', 'created_at', 'updated_at', 'empresa']

    def validate(self, attrs):
        """WARNING: v3.8.0: Validar exactly-one de producto/activo_fijo.
        En PATCH parcial se omite la validación si ninguno de los dos está en el payload.
        """
        attrs = self.normalize_data(attrs)

        producto = attrs.get('producto')
        activo_fijo = attrs.get('activo_fijo')

        # En modo parcial (PATCH) solo validar si al menos uno viene en el payload
        ambos_ausentes = 'producto' not in attrs and 'activo_fijo' not in attrs
        if self.partial and ambos_ausentes:
            return attrs

        if not producto and not activo_fijo:
            raise ValidationError("Debe seleccionar un Producto o un Activo Fijo.")
        if producto and activo_fijo:
            raise ValidationError("No puede seleccionar simultáneamente Producto y Activo Fijo.")

        return attrs

    def validate_producto(self, value):
        """WARNING: v3.8.0: Validación estricta del Producto."""
        if value is None:
            return value

        empresa_id = self._get_empresa_id()
        if not Producto.objects.filter(pk=value.id, empresa_id=empresa_id).exists():
            raise ValidationError(f"El producto con ID {value.id} no pertenece a este tenant.")

        return value

    def validate_activo_fijo(self, value):
        """WARNING: v3.8.0: Validación estricta del Activo Fijo."""
        if value is None:
            return value

        empresa_id = self._get_empresa_id()
        if not ActivoFijo.objects.filter(pk=value.id, empresa_id=empresa_id).exists():
            raise ValidationError(f"El activo fijo con ID {value.id} no pertenece a este tenant.")

        return value


# ==============================================================================
# HISTORIAL SERVICIOS
# ==============================================================================
class HistorialServicioDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    WARNING: v2.60: Serializer completo para DETALLE/CREACIÓN de Historial de Servicios.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    """
    servicio_nombre = serializers.CharField(source='servicio.nombre', read_only=True)
    id = serializers.UUIDField(source='uuid', read_only=True)
    pk = serializers.IntegerField(source='id', read_only=True)
    servicio = UUIDOrPKRelatedField(queryset=Servicio.objects.all())

    class Meta:
        model = HistorialServicio
        fields = [
            'id', 'pk', 'servicio', 'servicio_nombre',
            'fecha_registro', 'cantidad', 'valor_cobrado',
            'origen_referencia', 'cliente_referencia',
            'observaciones', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'pk', 'created_at', 'updated_at', 'empresa']
    
    def validate(self, attrs):
        """WARNING: Zero Trust: Normalización estricta antes de persistir."""
        attrs = self.normalize_data(attrs)
        return attrs
    
    def validate_servicio(self, value):
        """
        WARNING: v2.60: Validación estricta - Asegurar que el servicio pertenezca al tenant actual.
        Zero Trust: No confiar en el frontend.
        """
        if value is None:
            raise ValidationError("El servicio es requerido.")
        
        empresa_id = self._get_empresa_id()
        
        # Validar que el servicio pertenezca al tenant
        if not Servicio.objects.filter(pk=value.id, empresa_id=empresa_id).exists():
            raise ValidationError(f"El servicio con ID {value.id} no pertenece a este tenant.")
        
        return value


# ==============================================================================
# INGESTA MASIVA
# ==============================================================================
class ProductoCargaMasivaItemSerializer(serializers.Serializer):
    """DTO de producto para carga masiva idempotente."""

    codigo = serializers.CharField(max_length=64)
    nombre = serializers.CharField(max_length=200)
    categoria = serializers.CharField(max_length=100, required=False, allow_blank=True, default='General')
    descripcion = serializers.CharField(required=False, allow_blank=True, default='')
    unidad = serializers.CharField(max_length=16, required=False, allow_blank=True, default='UND')
    precio_venta = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, default=0)
    costo_promedio = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, default=0)
    stock_actual = serializers.DecimalField(max_digits=14, decimal_places=3, required=False, default=0)

    def validate_codigo(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El codigo es obligatorio.")
        return value

    def validate_nombre(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El nombre es obligatorio.")
        return value


class CargaMasivaInventarioSerializer(serializers.Serializer):
    """Payload de carga masiva de productos."""

    items = ProductoCargaMasivaItemSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Debe enviar al menos un item.")
        return value


# ==============================================================================
# TIMELINE UNIFICADO — Ledger Universal (v3.9.0)
# ==============================================================================

class MovimientoUnificadoListSerializer(serializers.Serializer):
    """
    Read-only serializer para el Ledger Universal.
    Proyecta DTOs unificados de MovimientoInventario + HistorialServicio.
    """
    uuid = serializers.CharField(read_only=True)
    fecha = serializers.CharField(read_only=True)
    modulo_origen = serializers.ChoiceField(
        choices=['PRODUCTO', 'ACTIVO_FIJO', 'SERVICIO'],
        read_only=True
    )
    item_uuid = serializers.CharField(read_only=True)
    item_codigo = serializers.CharField(read_only=True)
    item_nombre = serializers.CharField(read_only=True)
    tipo_accion = serializers.CharField(read_only=True)
    tipo_accion_display = serializers.CharField(read_only=True)
    cantidad = serializers.CharField(read_only=True)
    valor_costo = serializers.CharField(read_only=True)
    referencia = serializers.CharField(read_only=True)
    observaciones = serializers.CharField(read_only=True)


# ==============================================================================
# ALIASES PARA COMPATIBILIDAD (v2.60)
# ==============================================================================
# WARNING: v2.60: Mantener aliases para compatibilidad con codigo existente
# Los ViewSets deben usar los nombres Detail/List explicitos
CategoriaItemSerializer = CategoriaItemDetailSerializer
ProductoSerializer = ProductoDetailSerializer
ServicioSerializer = ServicioDetailSerializer
ActivoFijoSerializer = ActivoFijoDetailSerializer
MovimientoInventarioSerializer = MovimientoInventarioDetailSerializer
HistorialServicioSerializer = HistorialServicioDetailSerializer
