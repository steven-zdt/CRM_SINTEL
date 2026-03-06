"""
Servicios de dominio para Inventario v2.60.

⚠️ SINTEL v2.60: Sincronización Arquitectónica
- Aislamiento SSoT: Todos los modelos tienen empresa = ForeignKey(Empresa, on_delete=PROTECT) e índice obligatorio
- Campos Explícitos: LIST_FIELDS y DETAIL_FIELDS como tuplas (PROHIBIDO __all__)
- QuerySets Optimizados: qs_list() y qs_detail() usando .only(*FIELDS) y select_related()
- Lógica en Cálculos: Los cálculos económicos se realizan en el backend (Zero Trust)

PRINCIPIOS:
- Lógica de Negocio: Cálculos de stock, validaciones y cargas masivas.
- Transaccionalidad: Uso de transaction.atomic para integridad.
- Optimización: QuerySets pre-optimizados (qs_*) para ViewSets.
- Zero Trust: Validación estricta de pertenencia al tenant.
"""

from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Q, F
from django.core.exceptions import ValidationError

from apps.tenant.inventario.models import (
    Producto, Servicio, CategoriaItem, 
    MovimientoInventario, ActivoFijo, Empresa
)

# ==============================================================================
# 1. QUERYSETS OPTIMIZADOS (Service Layer Pattern) - v2.60
# ⚠️ SINTEL v2.60: Campos explícitos como tuplas (PROHIBIDO __all__)
# Usados por los ViewSets para evitar N+1 queries y cargar solo lo necesario.
# ==============================================================================

# ⚠️ v2.60: Constantes de campos para LISTAS (SSoT: Single Source of Truth)
# Campos estrictamente necesarios para tablas Tabulator (mínima exposición de datos)
CATEGORIA_LIST_FIELDS = (
    'id', 'nombre', 'descripcion', 'aplicacion', 'activo', 'empresa_id'
)

PRODUCTO_LIST_FIELDS = (
    'id', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__nombre',
    'stock_actual', 'stock_minimo', 'precio_venta', 'costo_promedio', 'activo', 'imagen', 'unidad', 'empresa_id'
)

SERVICIO_LIST_FIELDS = (
    'id', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__nombre',
    'precio_venta', 'activo', 'imagen', 'empresa_id'
)

ACTIVO_LIST_FIELDS = (
    'id', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__nombre',
    'ubicacion', 'responsable', 'estado', 'fecha_adquisicion', 'costo_adquisicion', 'empresa_id'
)

MOVIMIENTO_LIST_FIELDS = (
    'id', 'created_at', 'producto', 'producto__id', 'producto__codigo', 'producto__nombre',
    'tipo', 'cantidad', 'costo_unitario', 'origen_referencia', 'cliente_referencia', 'observaciones', 'empresa_id'
)

# ⚠️ v2.60: Constantes de campos para DETALLE (campos completos para edición)
# Incluye todos los campos necesarios para formularios de edición
CATEGORIA_DETAIL_FIELDS = (
    'id', 'nombre', 'descripcion', 'aplicacion', 'imagen', 'activo', 
    'created_at', 'updated_at', 'empresa_id'
)

PRODUCTO_DETAIL_FIELDS = (
    'id', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__nombre',
    'descripcion', 'unidad', 'imagen', 
    'precio_venta', 'costo_promedio', 
    'stock_actual', 'stock_minimo', 
    'activo', 'created_at', 'updated_at', 'empresa_id'
)

SERVICIO_DETAIL_FIELDS = (
    'id', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__nombre',
    'descripcion', 'imagen', 'precio_venta', 
    'activo', 'created_at', 'updated_at', 'empresa_id'
)

ACTIVO_DETAIL_FIELDS = (
    'id', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__nombre',
    'marca', 'modelo', 'descripcion', 'imagen',
    'ubicacion', 'responsable',
    'fecha_adquisicion', 'costo_adquisicion', 'estado',
    'created_at', 'updated_at', 'empresa_id'
)

MOVIMIENTO_DETAIL_FIELDS = (
    'id', 'producto', 'producto__id', 'producto__codigo', 'producto__nombre',
    'tipo', 'cantidad', 'costo_unitario',
    'origen_referencia', 'cliente_referencia', 'observaciones',
    'created_at', 'updated_at', 'empresa_id'
)

def qs_producto_list(empresa_id, search=None):
    """
    ⚠️ v2.60: QuerySet optimizado para LISTAR Productos (tabla Tabulator).
    Campos estrictamente necesarios para listado (mínima exposición de datos).
    
    Args:
        empresa_id: ID de la empresa (SSoT - Zero Trust)
        search: Término de búsqueda opcional (busca en codigo, nombre, categoria__nombre)
    
    Returns:
        QuerySet: Optimizado con .only(*PRODUCTO_LIST_FIELDS) y select_related('categoria')
    """
    # ⚠️ Zero Trust: Filtrar por empresa_id (SSoT)
    # ⚠️ Performance: select_related('categoria') para evitar N+1 queries
    # ⚠️ Performance: .only(*PRODUCTO_LIST_FIELDS) para cargar solo campos necesarios
    qs = Producto.objects.filter(empresa_id=empresa_id)\
        .select_related('categoria')\
        .only(*PRODUCTO_LIST_FIELDS)
    
    if search:
        qs = qs.filter(
            Q(codigo__icontains=search) |
            Q(nombre__icontains=search) |
            Q(categoria__nombre__icontains=search)
        )
    
    return qs


def qs_producto_detail(empresa_id, producto_id):
    """
    ⚠️ v2.60: QuerySet optimizado para DETALLE de Producto (formulario de edición).
    Campos completos necesarios para edición.
    
    Args:
        empresa_id: ID de la empresa (SSoT - Zero Trust)
        producto_id: ID del producto
    
    Returns:
        Producto: Instancia con todos los campos necesarios para edición
    
    Raises:
        Producto.DoesNotExist: Si el producto no existe o no pertenece al tenant
    """
    # ⚠️ Zero Trust: Filtrar por empresa_id (SSoT)
    # ⚠️ Performance: select_related('categoria') para evitar N+1 queries
    # ⚠️ Performance: .only(*PRODUCTO_DETAIL_FIELDS) para cargar solo campos necesarios
    return Producto.objects.filter(empresa_id=empresa_id, pk=producto_id)\
        .select_related('categoria')\
        .only(*PRODUCTO_DETAIL_FIELDS)\
        .get()

def qs_servicio_list(empresa_id, search=None):
    """
    ⚠️ v2.60: QuerySet optimizado para LISTAR Servicios (tabla Tabulator).
    Campos estrictamente necesarios para listado (mínima exposición de datos).
    
    Args:
        empresa_id: ID de la empresa (SSoT - Zero Trust)
        search: Término de búsqueda opcional (busca en codigo, nombre, categoria__nombre)
    
    Returns:
        QuerySet: Optimizado con .only(*SERVICIO_LIST_FIELDS) y select_related('categoria')
    """
    qs = Servicio.objects.filter(empresa_id=empresa_id)\
        .select_related('categoria')\
        .only(*SERVICIO_LIST_FIELDS)
    
    if search:
        qs = qs.filter(
            Q(codigo__icontains=search) |
            Q(nombre__icontains=search) |
            Q(categoria__nombre__icontains=search)
        )
    
    return qs


def qs_servicio_detail(empresa_id, servicio_id):
    """
    ⚠️ v2.60: QuerySet optimizado para DETALLE de Servicio (formulario de edición).
    Campos completos necesarios para edición.
    
    Args:
        empresa_id: ID de la empresa (SSoT - Zero Trust)
        servicio_id: ID del servicio
    
    Returns:
        Servicio: Instancia con todos los campos necesarios para edición
    
    Raises:
        Servicio.DoesNotExist: Si el servicio no existe o no pertenece al tenant
    """
    return Servicio.objects.filter(empresa_id=empresa_id, pk=servicio_id)\
        .select_related('categoria')\
        .only(*SERVICIO_DETAIL_FIELDS)\
        .get()

def qs_activo_list(empresa_id, search=None):
    """
    ⚠️ v2.60: QuerySet optimizado para LISTAR Activos Fijos (tabla Tabulator).
    Campos estrictamente necesarios para listado (mínima exposición de datos).
    
    Args:
        empresa_id: ID de la empresa (SSoT - Zero Trust)
        search: Término de búsqueda opcional (busca en codigo, nombre, categoria__nombre, ubicacion, responsable)
    
    Returns:
        QuerySet: Optimizado con .only(*ACTIVO_LIST_FIELDS) y select_related('categoria')
    """
    qs = ActivoFijo.objects.filter(empresa_id=empresa_id)\
        .select_related('categoria')\
        .only(*ACTIVO_LIST_FIELDS)
    
    if search:
        qs = qs.filter(
            Q(codigo__icontains=search) |
            Q(nombre__icontains=search) |
            Q(categoria__nombre__icontains=search) |
            Q(ubicacion__icontains=search) |
            Q(responsable__icontains=search)
        )
    
    return qs


def qs_activo_detail(empresa_id, activo_id):
    """
    ⚠️ v2.60: QuerySet optimizado para DETALLE de Activo Fijo (formulario de edición).
    Campos completos necesarios para edición.
    
    Args:
        empresa_id: ID de la empresa (SSoT - Zero Trust)
        activo_id: ID del activo
    
    Returns:
        ActivoFijo: Instancia con todos los campos necesarios para edición
    
    Raises:
        ActivoFijo.DoesNotExist: Si el activo no existe o no pertenece al tenant
    """
    return ActivoFijo.objects.filter(empresa_id=empresa_id, pk=activo_id)\
        .select_related('categoria')\
        .only(*ACTIVO_DETAIL_FIELDS)\
        .get()

def qs_movimiento_list(empresa_id, search=None):
    """
    ⚠️ v2.60: QuerySet optimizado para LISTAR Movimientos de Inventario (Kardex).
    Campos estrictamente necesarios para listado (mínima exposición de datos).
    
    Args:
        empresa_id: ID de la empresa (SSoT - Zero Trust)
        search: Término de búsqueda opcional (busca en producto__codigo, producto__nombre, origen_referencia, observaciones)
    
    Returns:
        QuerySet: Optimizado con .only(*MOVIMIENTO_LIST_FIELDS) y select_related('producto')
    """
    # ⚠️ Zero Trust: Filtrar por producto__empresa_id (SSoT)
    # ⚠️ Performance: select_related('producto') para evitar N+1 queries
    # ⚠️ Performance: .only(*MOVIMIENTO_LIST_FIELDS) para cargar solo campos necesarios
    qs = MovimientoInventario.objects.filter(producto__empresa_id=empresa_id)\
        .select_related('producto')\
        .only(*MOVIMIENTO_LIST_FIELDS)
    
    if search:
        qs = qs.filter(
            Q(producto__codigo__icontains=search) |
            Q(producto__nombre__icontains=search) |
            Q(origen_referencia__icontains=search) |
            Q(observaciones__icontains=search)
        )
    
    return qs


def qs_movimiento_detail(empresa_id, movimiento_id):
    """
    ⚠️ v2.60: QuerySet optimizado para DETALLE de Movimiento (formulario de edición).
    Campos completos necesarios para edición.
    
    Args:
        empresa_id: ID de la empresa (SSoT - Zero Trust)
        movimiento_id: ID del movimiento
    
    Returns:
        MovimientoInventario: Instancia con todos los campos necesarios para edición
    
    Raises:
        MovimientoInventario.DoesNotExist: Si el movimiento no existe o no pertenece al tenant
    """
    return MovimientoInventario.objects.filter(empresa_id=empresa_id, pk=movimiento_id)\
        .select_related('producto')\
        .only(*MOVIMIENTO_DETAIL_FIELDS)\
        .get()

def qs_categoria_list(empresa_id=None, search=None):
    """
    ⚠️ v2.60: QuerySet optimizado para LISTAR Categorías (tabla Tabulator).
    Campos estrictamente necesarios para listado (mínima exposición de datos).
    
    Args:
        empresa_id: ID de la empresa (SSoT - Zero Trust, opcional para compatibilidad)
        search: Término de búsqueda opcional (busca en nombre, descripcion)
    
    Returns:
        QuerySet: Optimizado con .only(*CATEGORIA_LIST_FIELDS)
    """
    # ⚠️ Zero Trust: Filtrar por empresa_id si se proporciona
    if empresa_id:
        qs = CategoriaItem.objects.filter(empresa_id=empresa_id).only(*CATEGORIA_LIST_FIELDS)
    else:
        qs = CategoriaItem.objects.only(*CATEGORIA_LIST_FIELDS)
    
    if search:
        qs = qs.filter(
            Q(nombre__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    return qs


def qs_categoria_detail(empresa_id, categoria_id):
    """
    ⚠️ v2.60: QuerySet optimizado para DETALLE de Categoría (formulario de edición).
    Campos completos necesarios para edición.
    
    Args:
        empresa_id: ID de la empresa (SSoT - Zero Trust)
        categoria_id: ID de la categoría
    
    Returns:
        CategoriaItem: Instancia con todos los campos necesarios para edición
    
    Raises:
        CategoriaItem.DoesNotExist: Si la categoría no existe o no pertenece al tenant
    """
    return CategoriaItem.objects.filter(empresa_id=empresa_id, pk=categoria_id)\
        .only(*CATEGORIA_DETAIL_FIELDS)\
        .get()

# ==============================================================================
# 2. GESTIÓN DE STOCK (Motor de Kardex)
# ==============================================================================

def calcular_stock(producto_id: int) -> Decimal:
    """
    Calcula el stock actual de un producto basado en sus movimientos (solo lectura).
    
    ⚠️ v2.40: Esta función solo calcula, no actualiza el campo stock_actual.
    Para actualizar el stock, usar recalcular_stock_producto().
    
    ⚠️ PERFORMANCE BIBLE:
    - Usa .exists() en lugar de .get() si solo verificamos existencia
    - Agregaciones optimizadas con .aggregate()
    
    Returns:
        Decimal: Stock calculado (entradas - salidas + ajustes)
    """
    # ⚠️ CRÍTICO: Usar .exists() en lugar de .get() si solo verificamos existencia
    if not Producto.objects.filter(pk=producto_id).exists():
        return Decimal("0")

    # Calcular entradas (todos los tipos de entrada)
    entradas = MovimientoInventario.objects.filter(
        producto_id=producto_id,
        tipo__in=[
            MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
            MovimientoInventario.TipoMovimiento.ENTRADA_DEVOLUCION,
        ]
    ).aggregate(total=Sum("cantidad"))["total"] or Decimal("0")

    # Calcular salidas (todos los tipos de salida)
    salidas = MovimientoInventario.objects.filter(
        producto_id=producto_id,
        tipo__in=[
            MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
            MovimientoInventario.TipoMovimiento.SALIDA_BAJA,
            MovimientoInventario.TipoMovimiento.SALIDA_CONSUMO,
        ]
    ).aggregate(total=Sum("cantidad"))["total"] or Decimal("0")

    # Ajustes positivos
    ajustes_pos = MovimientoInventario.objects.filter(
        producto_id=producto_id,
        tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
        cantidad__gt=0
    ).aggregate(total=Sum("cantidad"))["total"] or Decimal("0")

    # Ajustes negativos (salidas por ajuste)
    ajustes_neg = MovimientoInventario.objects.filter(
        producto_id=producto_id,
        tipo=MovimientoInventario.TipoMovimiento.SALIDA_BAJA,
        cantidad__lt=0
    ).aggregate(total=Sum("cantidad"))["total"] or Decimal("0")

    return entradas + ajustes_pos - (salidas + abs(ajustes_neg))


def recalcular_stock_producto(producto_id: int) -> Decimal:
    """
    Recalcula el stock físico de un producto sumando/restando todos sus movimientos.
    Actualiza el campo desnormalizado `stock_actual` del Producto.
    
    ⚠️ PERFORMANCE BIBLE:
    - Usa select_for_update() para lock optimista
    - Agregaciones optimizadas en una sola consulta cuando es posible
    - Solo actualiza campos necesarios (update_fields)
    
    Returns:
        Decimal: El nuevo stock calculado.
    """
    with transaction.atomic():
        # ⚠️ CRÍTICO: select_for_update() para lock optimista + solo campos necesarios
        producto = Producto.objects.select_for_update().only('id', 'stock_actual').get(id=producto_id)
        
        # Definir tipos de movimiento (⚠️ v2.40: Solo tipos válidos según modelo)
        entradas = [
            MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
            MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
            MovimientoInventario.TipoMovimiento.ENTRADA_DEVOLUCION,
        ]
        
        salidas = [
            MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
            MovimientoInventario.TipoMovimiento.SALIDA_BAJA,
            MovimientoInventario.TipoMovimiento.SALIDA_CONSUMO,
        ]

        # ⚠️ OPTIMIZACIÓN: Agregaciones optimizadas - solo campo 'cantidad' necesario
        suma_entradas = MovimientoInventario.objects.filter(
            producto_id=producto_id, 
            tipo__in=entradas
        ).aggregate(total=Sum('cantidad'))['total'] or Decimal(0)
        
        suma_salidas = MovimientoInventario.objects.filter(
            producto_id=producto_id, 
            tipo__in=salidas
        ).aggregate(total=Sum('cantidad'))['total'] or Decimal(0)
        
        nuevo_stock = suma_entradas - suma_salidas
        
        # ⚠️ CRÍTICO: Solo actualizar campos necesarios (update_fields)
        producto.stock_actual = nuevo_stock
        producto.save(update_fields=['stock_actual', 'updated_at'])
        
        return nuevo_stock

@transaction.atomic
def registrar_entrada(producto_id: int, empresa_id: int, cantidad: Decimal, tipo_movimiento: str = None, costo_unitario: Decimal = None, origen_referencia: str = None, observaciones: str = None):
    """
    ⚠️ v2.60: Registra una entrada de producto (compra, devolución, ajuste positivo) con Zero Trust.
    
    Args:
        producto_id: ID del producto
        empresa_id: ID de la empresa del tenant (Zero Trust)
        cantidad: Cantidad a registrar (debe ser positiva)
        tipo_movimiento: Tipo de movimiento (ENTRADA_COMPRA, ENTRADA_DEVOLUCION, ENTRADA_AJUSTE). Default: ENTRADA_COMPRA
        costo_unitario: Costo unitario opcional
        origen_referencia: Referencia externa (string, ej: "FAC-123", "ORD-456")
        observaciones: Observaciones del movimiento
        
    Returns:
        MovimientoInventario: Movimiento creado
        
    Raises:
        ValidationError: Si la cantidad es negativa, el producto no existe o no pertenece al tenant
    """
    if cantidad <= 0:
        raise ValidationError("La cantidad de entrada debe ser positiva.")
    
    # ⚠️ ZERO TRUST: Validar que el producto pertenezca al tenant
    producto = Producto.objects.only('id', 'empresa_id').filter(pk=producto_id, empresa_id=empresa_id).first()
    if not producto:
        raise ValidationError(f"El producto con ID {producto_id} no existe o no pertenece a este tenant.")
    
    # Tipo de movimiento por defecto
    if not tipo_movimiento:
        tipo_movimiento = MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA
    
    # Validar que sea un tipo de entrada válido
    tipos_entrada = [
        MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
        MovimientoInventario.TipoMovimiento.ENTRADA_DEVOLUCION,
        MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
    ]
    if tipo_movimiento not in tipos_entrada:
        raise ValidationError(f"Tipo de movimiento inválido para entrada: {tipo_movimiento}")
    
    movimiento = MovimientoInventario.objects.create(
        producto=producto,
        empresa_id=empresa_id,  # Zero Trust: usar empresa_id del tenant
        tipo=tipo_movimiento,
        cantidad=cantidad,
        costo_unitario=costo_unitario or Decimal('0'),
        origen_referencia=origen_referencia,
        observaciones=observaciones,
    )
    
    # Actualizar stock maestro
    recalcular_stock_producto(producto_id)
    
    return movimiento


@transaction.atomic
def registrar_salida(producto_id: int, empresa_id: int, cantidad: Decimal, tipo_movimiento: str = None, costo_unitario: Decimal = None, origen_referencia: str = None, cliente_referencia: str = None, observaciones: str = None):
    """
    ⚠️ v2.60: Registra una salida de producto (venta, baja, consumo interno) con Zero Trust.
    
    Args:
        producto_id: ID del producto
        empresa_id: ID de la empresa del tenant (Zero Trust)
        cantidad: Cantidad a registrar (debe ser positiva)
        tipo_movimiento: Tipo de movimiento (SALIDA_VENTA, SALIDA_BAJA, SALIDA_CONSUMO). Default: SALIDA_VENTA
        costo_unitario: Costo unitario opcional
        origen_referencia: Referencia externa (string, ej: "FAC-123", "ORD-456")
        cliente_referencia: Cliente relacionado (opcional)
        observaciones: Observaciones del movimiento
        
    Returns:
        MovimientoInventario: Movimiento creado
        
    Raises:
        ValidationError: Si la cantidad es negativa, el producto no existe, no pertenece al tenant o no hay stock suficiente
    """
    if cantidad <= 0:
        raise ValidationError("La cantidad de salida debe ser positiva.")
    
    # ⚠️ ZERO TRUST: Validar que el producto pertenezca al tenant
    producto = Producto.objects.only('id', 'empresa_id', 'stock_actual').filter(pk=producto_id, empresa_id=empresa_id).first()
    if not producto:
        raise ValidationError(f"El producto con ID {producto_id} no existe o no pertenece a este tenant.")
    
    # Validar stock disponible (regla de negocio)
    if producto.stock_actual < cantidad:
        raise ValidationError(f"Stock insuficiente. Disponible: {producto.stock_actual}, Solicitado: {cantidad}")
    
    # Tipo de movimiento por defecto
    if not tipo_movimiento:
        tipo_movimiento = MovimientoInventario.TipoMovimiento.SALIDA_VENTA
    
    # Validar que sea un tipo de salida válido
    tipos_salida = [
        MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
        MovimientoInventario.TipoMovimiento.SALIDA_BAJA,
        MovimientoInventario.TipoMovimiento.SALIDA_CONSUMO,
    ]
    if tipo_movimiento not in tipos_salida:
        raise ValidationError(f"Tipo de movimiento inválido para salida: {tipo_movimiento}")
    
    movimiento = MovimientoInventario.objects.create(
        producto=producto,
        empresa_id=empresa_id,  # Zero Trust: usar empresa_id del tenant
        tipo=tipo_movimiento,
        cantidad=cantidad,
        costo_unitario=costo_unitario or Decimal('0'),
        origen_referencia=origen_referencia,
        cliente_referencia=cliente_referencia,
        observaciones=observaciones,
    )
    
    # Actualizar stock maestro
    recalcular_stock_producto(producto_id)
    
    return movimiento


@transaction.atomic
def ajustar_stock(producto_id: int, empresa_id: int, cantidad_ajuste: Decimal, observaciones: str = None):
    """
    ⚠️ v2.60: Ajusta el stock de un producto (puede ser positivo o negativo) con Zero Trust.
    
    Args:
        producto_id: ID del producto
        empresa_id: ID de la empresa del tenant (Zero Trust)
        cantidad_ajuste: Cantidad a ajustar (positiva para aumentar, negativa para disminuir)
        observaciones: Observaciones del ajuste
        
    Returns:
        MovimientoInventario: Movimiento de ajuste creado
        
    Raises:
        ValidationError: Si el producto no existe, no pertenece al tenant o el ajuste resultaría en stock negativo
    """
    # ⚠️ ZERO TRUST: Validar que el producto pertenezca al tenant
    producto = Producto.objects.only('id', 'empresa_id', 'stock_actual').filter(pk=producto_id, empresa_id=empresa_id).first()
    if not producto:
        raise ValidationError(f"El producto con ID {producto_id} no existe o no pertenece a este tenant.")
    
    # Validar que el ajuste no resulte en stock negativo
    nuevo_stock = producto.stock_actual + cantidad_ajuste
    if nuevo_stock < 0:
        raise ValidationError(f"El ajuste resultaría en stock negativo. Stock actual: {producto.stock_actual}, Ajuste: {cantidad_ajuste}")
    
    # Determinar tipo de movimiento según el signo del ajuste
    if cantidad_ajuste > 0:
        tipo_movimiento = MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE
    else:
        tipo_movimiento = MovimientoInventario.TipoMovimiento.SALIDA_BAJA
        cantidad_ajuste = abs(cantidad_ajuste)  # Convertir a positivo para el movimiento
    
    movimiento = MovimientoInventario.objects.create(
        producto=producto,
        empresa_id=empresa_id,  # Zero Trust: usar empresa_id del tenant
        tipo=tipo_movimiento,
        cantidad=cantidad_ajuste,
        costo_unitario=producto.costo_promedio or Decimal('0'),
        observaciones=observaciones or f"Ajuste de inventario: {cantidad_ajuste:+} unidades",
    )
    
    # Actualizar stock maestro
    recalcular_stock_producto(producto_id)
    
    return movimiento


def registrar_movimiento(
    producto_id: int,
    tipo: str,
    cantidad: Decimal,
    empresa: Empresa,
    costo_unitario: Decimal = 0,
    origen_referencia: str = None,
    cliente_referencia: str = None,
    observaciones: str = None,
    usuario=None
) -> MovimientoInventario:
    """
    Crea un movimiento de inventario y dispara la actualización de stock.
    Esta es la función segura para usar desde APIs externas (Ventas, Compras).
    
    ⚠️ v2.40: Para registrar entradas simples, usar registrar_entrada() en su lugar.
    """
    with transaction.atomic():
        # Validar stock negativo si es salida (regla de negocio opcional)
        # if tipo in [SALIDAS...] and stock_actual < cantidad: raise ValidationError...

        movimiento = MovimientoInventario.objects.create(
            empresa=empresa,
            producto_id=producto_id,
            tipo=tipo,
            cantidad=cantidad,
            costo_unitario=costo_unitario,
            origen_referencia=origen_referencia,
            cliente_referencia=cliente_referencia,
            observaciones=observaciones
            # usuario=usuario # (Campo eliminado del modelo por SSoT estricto)
        )
        
        # Actualizar stock maestro
        recalcular_stock_producto(producto_id)
        
        return movimiento

# ==============================================================================
# 3. INGESTA DE DATOS (Carga Masiva desde Excel/PDF Parser)
# Conector para apps.services.document_parser
# ==============================================================================

def materializar_inventario_desde_dto(dto: dict) -> tuple[dict, int]:
    """
    Materializa inventario desde DTO canónico del pipeline de documentos.
    
    ⚠️ v2.40: Compatible con Document Ingest Pipeline Universal.
    Recibe DTO canónico y materializa productos en la base de datos.
    
    Args:
        dto: DTO canónico con estructura:
            {
                "tipo": "producto" | "servicio" | "activo",
                "codigo": str,
                "nombre": str,
                "categoria": str,
                "precio_venta": Decimal,
                "stock_actual": Decimal (solo productos),
                ...
            }
            
    Returns:
        Tuple (payload, status_code):
        - 201 Created: Si se crea nuevo registro
        - 200 OK: Si se actualiza registro existente
        - 422 Unprocessable Entity: Si faltan campos obligatorios
    """
    from apps.tenant.empresa.models import Empresa
    
    # ⚠️ PERFORMANCE BIBLE: Usar .only('id') para obtener empresa singleton
    empresa = Empresa.objects.only('id').first()
    if not empresa:
        return {
            "error": "empresa_no_configurada",
            "message": "No existe Empresa en este tenant. Configure una Empresa antes de importar inventario."
        }, 422
    
    # Extraer tipo y datos básicos
    tipo = dto.get("tipo", "producto").lower()
    codigo = dto.get("codigo")
    nombre = dto.get("nombre")
    categoria_nombre = dto.get("categoria", "General")
    
    if not codigo or not nombre:
        return {
            "error": "missing_required_fields",
            "message": "Faltan campos obligatorios: codigo, nombre"
        }, 422
    
    try:
        with transaction.atomic():
            # Gestionar Categoría
            categoria, _ = CategoriaItem.objects.get_or_create(
                empresa=empresa,
                nombre__iexact=categoria_nombre,
                defaults={
                    'nombre': categoria_nombre,
                    'aplicacion': CategoriaItem.Aplicacion.PRODUCTO if tipo == "producto" else (
                        CategoriaItem.Aplicacion.SERVICIO if tipo == "servicio" else CategoriaItem.Aplicacion.ACTIVO
                    ),
                    'descripcion': 'Auto-generada desde DTO'
                }
            )
            
            if tipo == "producto":
                # Materializar Producto
                producto, created = Producto.objects.update_or_create(
                    empresa=empresa,
                    codigo=codigo,
                    defaults={
                        'nombre': nombre,
                        'categoria': categoria,
                        'descripcion': dto.get("descripcion", ""),
                        'unidad': dto.get("unidad", "UND"),
                        'precio_venta': Decimal(str(dto.get("precio_venta", "0"))),
                        'costo_promedio': Decimal(str(dto.get("costo_promedio", "0"))),
                        'activo': True
                    }
                )
                
                # Si es nuevo y tiene stock inicial, crear movimiento
                if created and dto.get("stock_actual"):
                    stock_inicial = Decimal(str(dto.get("stock_actual", "0")))
                    if stock_inicial > 0:
                        MovimientoInventario.objects.create(
                            empresa=empresa,
                            producto=producto,
                            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
                            cantidad=stock_inicial,
                            observaciones="Carga desde DTO"
                        )
                        recalcular_stock_producto(producto.id)
                
                return {
                    "id": producto.id,
                    "codigo": producto.codigo,
                    "nombre": producto.nombre,
                    "created": created
                }, 201 if created else 200
                
            elif tipo == "servicio":
                # Materializar Servicio
                servicio, created = Servicio.objects.update_or_create(
                    empresa=empresa,
                    codigo=codigo,
                    defaults={
                        'nombre': nombre,
                        'categoria': categoria,
                        'descripcion': dto.get("descripcion", ""),
                        'precio_venta': Decimal(str(dto.get("precio_venta", "0"))),
                        'activo': True
                    }
                )
                
                return {
                    "id": servicio.id,
                    "codigo": servicio.codigo,
                    "nombre": servicio.nombre,
                    "created": created
                }, 201 if created else 200
                
            elif tipo == "activo":
                # Materializar Activo Fijo
                activo, created = ActivoFijo.objects.update_or_create(
                    empresa=empresa,
                    codigo=codigo,
                    defaults={
                        'nombre': nombre,
                        'categoria': categoria,
                        'descripcion': dto.get("descripcion", ""),
                        'costo_adquisicion': Decimal(str(dto.get("costo_adquisicion", "0"))),
                        'estado': dto.get("estado", ActivoFijo.Estado.ACTIVO),
                        'ubicacion': dto.get("ubicacion"),
                        'responsable': dto.get("responsable"),
                    }
                )
                
                return {
                    "id": activo.id,
                    "codigo": activo.codigo,
                    "nombre": activo.nombre,
                    "created": created
                }, 201 if created else 200
            else:
                return {
                    "error": "invalid_type",
                    "message": f"Tipo inválido: {tipo}. Use 'producto', 'servicio' o 'activo'."
                }, 422
                
    except Exception as e:
        return {
            "error": "materialization_error",
            "message": f"Error al materializar inventario: {str(e)}"
        }, 422


def materializar_carga_masiva_productos(empresa_id, lista_datos, usuario=None):
    """
    Recibe una lista de diccionarios (ya procesados por document_parser)
    y los materializa en la base de datos de Inventario.
    
    Args:
        empresa_id: ID de la empresa SSoT.
        lista_datos: Lista de dicts [{'codigo': 'A1', 'nombre': 'X', 'categoria': 'CCTV', ...}]
        usuario: Usuario que realiza la carga (opcional, para logs).
        
    Returns:
        dict: Resumen de la operación (creados, actualizados, errores).
    """
    resumen = {
        "creados": 0,
        "actualizados": 0,
        "errores": []
    }

    # ⚠️ PERFORMANCE BIBLE: Solo obtener empresa si realmente la necesitamos (para get_or_create)
    # En este caso sí la necesitamos porque get_or_create requiere el objeto
    try:
        empresa = Empresa.objects.only('id').get(id=empresa_id)
    except Empresa.DoesNotExist:
        raise ValidationError(f"La empresa con ID {empresa_id} no existe.")

    with transaction.atomic():
        for index, fila in enumerate(lista_datos):
            try:
                # 1. Validar datos mínimos
                codigo = fila.get('codigo')
                nombre = fila.get('nombre')
                categoria_nombre = fila.get('categoria', 'General')
                
                if not codigo or not nombre:
                    resumen["errores"].append(f"Fila {index+1}: Falta código o nombre.")
                    continue

                # 2. Gestionar Categoría (Buscar o Crear)
                categoria, _ = CategoriaItem.objects.get_or_create(
                    empresa=empresa,
                    nombre__iexact=categoria_nombre,
                    defaults={
                        'nombre': categoria_nombre,
                        'aplicacion': CategoriaItem.Aplicacion.PRODUCTO,
                        'descripcion': 'Auto-generada por carga masiva'
                    }
                )

                # 3. Materializar Producto
                stock_inicial = Decimal(str(fila.get('stock_actual', '0')))
                
                producto, created = Producto.objects.update_or_create(
                    empresa=empresa,
                    codigo=codigo,
                    defaults={
                        'nombre': nombre,
                        'categoria': categoria,
                        'descripcion': fila.get('descripcion', ''),
                        'unidad': fila.get('unidad', 'UND'),
                        'precio_venta': Decimal(str(fila.get('precio_venta', '0'))),
                        'costo_promedio': Decimal(str(fila.get('costo_promedio', '0'))),
                        # Nota: Si es actualización, decidimos NO sobrescribir stock automáticamente
                        # para no romper el Kardex, salvo que sea creación.
                        'activo': True
                    }
                )

                if created:
                    resumen["creados"] += 1
                    # Si es nuevo, establecemos el stock inicial (Ajuste de Inventario)
                    if stock_inicial > 0:
                        MovimientoInventario.objects.create(
                            empresa=empresa,
                            producto=producto,
                            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
                            cantidad=stock_inicial,
                            observaciones="Carga Masiva Inicial"
                        )
                        producto.stock_actual = stock_inicial
                        producto.save()
                else:
                    resumen["actualizados"] += 1

            except Exception as e:
                resumen["errores"].append(f"Fila {index+1} ({codigo if codigo else '?' }): {str(e)}")

    return resumen


# ==============================================================================
# 4. GESTIÓN DE ACTIVOS FIJOS
# ==============================================================================

def _obtener_empresa_singleton():
    """
    Obtiene la Empresa del tenant actual (SSoT). Debe existir 0..1; si hay 0, forzar creación previa.
    
    ⚠️ v2.40: Helper interno para funciones que requieren empresa singleton.
    ⚠️ PERFORMANCE BIBLE:
    - PROHIBIDO .all(): Usa .first() directamente
    - PROHIBIDO .count(): Usa .exists() para verificar existencia
    """
    # ⚠️ CRÍTICO: No usar .all() - usar .first() directamente
    empresa = Empresa.objects.only('id').first()
    if not empresa:
        raise ValidationError("No se encontró la Empresa singleton del tenant.")
    
    # Verificar que no hay más de una (singleton pattern)
    if Empresa.objects.exclude(id=empresa.id).exists():
        raise ValidationError("Hay más de una Empresa en este tenant (debe ser singleton).")
    
    return empresa


@transaction.atomic
def crear_activo_fijo(*, codigo: str, nombre: str, costo_adquisicion, empresa_id=None, 
                      descripcion=None, fecha_adquisicion=None, estado=None, categoria_id=None,
                      ubicacion=None, responsable=None):
    """
    ⚠️ v2.40: Crea un ActivoFijo. Si empresa_id es None, usa la Empresa singleton del tenant.
    
    Nota: ActivoFijo no tiene campos 'vida_util_meses', 'metodo_depreciacion' ni 'activo'.
    Usa 'estado' (ACTIVO, MANTENIMIENTO, BAJA, VENDIDO) en lugar de 'activo'.
    
    Args:
        codigo: Código único del activo (placa, serial, etc.)
        nombre: Nombre del activo
        costo_adquisicion: Costo de adquisición
        empresa_id: ID de la empresa (opcional, usa singleton si None)
        descripcion: Descripción opcional
        fecha_adquisicion: Fecha de adquisición opcional
        estado: Estado del activo (ACTIVO por defecto)
        categoria_id: ID de la categoría opcional
        ubicacion: Ubicación física opcional
        responsable: Responsable del activo opcional
        
    Returns:
        ActivoFijo: Instancia creada
        
    Raises:
        ValidationError: Si no se encuentra empresa singleton o hay más de una
    """
    if empresa_id is None:
        empresa = _obtener_empresa_singleton()
    else:
        # ⚠️ PERFORMANCE BIBLE: Solo obtener ID si realmente necesitamos el objeto
        # En este caso sí lo necesitamos para crear ActivoFijo
        empresa = Empresa.objects.only('id').get(pk=empresa_id)

    # Usar estado por defecto si no se especifica
    if estado is None:
        estado = ActivoFijo.Estado.ACTIVO

    return ActivoFijo.objects.create(
        empresa=empresa,
        codigo=codigo,
        nombre=nombre,
        descripcion=descripcion,
        fecha_adquisicion=fecha_adquisicion,
        costo_adquisicion=costo_adquisicion,
        estado=estado,
        categoria_id=categoria_id,
        ubicacion=ubicacion,
        responsable=responsable,
    )