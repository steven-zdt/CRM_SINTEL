"""
crud_service.py - Inventario v3.5

Capa de persistencia pura para el modulo de Inventario.
Contiene UNICAMENTE operaciones de escritura atomicas en BD sin
logica de negocio ni calculos de stock.

Reglas:
- Toda operacion de escritura usa @transaction.atomic.
- Ninguna funcion aqui recalcula stock (delegar a business_service.py).
- Validacion de empresa_id obligatoria en toda creacion (Zero Trust).
"""

from decimal import Decimal

from django.db import transaction

from apps.tenant.inventario.models import (
    ActivoFijo,
    CategoriaItem,
    Empresa,
    MovimientoInventario,
    Producto,
    Servicio,
)


@transaction.atomic
def crear_producto(
    *,
    empresa: Empresa,
    codigo: str,
    nombre: str,
    categoria: CategoriaItem = None,
    descripcion: str = "",
    unidad: str = "UND",
    precio_venta: Decimal = Decimal("0"),
    costo_promedio: Decimal = Decimal("0"),
    stock_minimo: Decimal = Decimal("0"),
    activo: bool = True,
    cuenta_inventario_uuid=None,
    cuenta_costo_uuid=None,
) -> Producto:
    """
    Crea un nuevo Producto en BD de forma atomica.

    Args:
        empresa: Instancia de Empresa (Zero Trust SSoT).
        codigo: SKU unico del producto.
        nombre: Nombre del producto.
        categoria: ForeignKey a CategoriaItem (opcional).
        ...campos opcionales...

    Returns:
        Producto: Instancia creada.
    """
    return Producto.objects.create(
        empresa=empresa,
        codigo=codigo,
        nombre=nombre,
        categoria=categoria,
        descripcion=descripcion,
        unidad=unidad,
        precio_venta=precio_venta,
        costo_promedio=costo_promedio,
        stock_minimo=stock_minimo,
        activo=activo,
        cuenta_inventario_uuid=cuenta_inventario_uuid,
        cuenta_costo_uuid=cuenta_costo_uuid,
    )


@transaction.atomic
def actualizar_producto(*, producto: Producto, **kwargs) -> Producto:
    """
    Actualiza campos de un Producto existente.

    Args:
        producto: Instancia de Producto a actualizar.
        **kwargs: Campos a actualizar (nombre, precio_venta, etc.).

    Returns:
        Producto: Instancia actualizada.
    """
    campos_actualizables = [
        'nombre', 'categoria', 'descripcion', 'unidad',
        'precio_venta', 'costo_promedio', 'stock_minimo', 'activo',
        'cuenta_inventario_uuid', 'cuenta_costo_uuid',
    ]
    campos_modificados = []
    for campo in campos_actualizables:
        if campo in kwargs:
            setattr(producto, campo, kwargs[campo])
            campos_modificados.append(campo)

    if campos_modificados:
        campos_modificados.append('updated_at')
        producto.save(update_fields=campos_modificados)

    return producto


@transaction.atomic
def crear_servicio(
    *,
    empresa: Empresa,
    codigo: str,
    nombre: str,
    categoria: CategoriaItem = None,
    descripcion: str = "",
    precio_venta: Decimal = Decimal("0"),
    activo: bool = True,
    cuenta_ingreso_uuid=None,
) -> Servicio:
    """
    Crea un nuevo Servicio en BD de forma atomica.

    Args:
        empresa: Instancia de Empresa (Zero Trust SSoT).
        codigo: Codigo unico del servicio.
        nombre: Nombre del servicio.
        ...campos opcionales...

    Returns:
        Servicio: Instancia creada.
    """
    return Servicio.objects.create(
        empresa=empresa,
        codigo=codigo,
        nombre=nombre,
        categoria=categoria,
        descripcion=descripcion,
        precio_venta=precio_venta,
        activo=activo,
        cuenta_ingreso_uuid=cuenta_ingreso_uuid,
    )


@transaction.atomic
def actualizar_servicio(*, servicio: Servicio, **kwargs) -> Servicio:
    """
    Actualiza campos de un Servicio existente.

    Args:
        servicio: Instancia de Servicio a actualizar.
        **kwargs: Campos a actualizar.

    Returns:
        Servicio: Instancia actualizada.
    """
    campos_actualizables = [
        'nombre', 'categoria', 'descripcion', 'precio_venta', 'activo',
        'cuenta_ingreso_uuid',
    ]
    campos_modificados = []
    for campo in campos_actualizables:
        if campo in kwargs:
            setattr(servicio, campo, kwargs[campo])
            campos_modificados.append(campo)

    if campos_modificados:
        campos_modificados.append('updated_at')
        servicio.save(update_fields=campos_modificados)

    return servicio


@transaction.atomic
def crear_activo(
    *,
    empresa: Empresa,
    codigo: str,
    nombre: str,
    costo_adquisicion: Decimal = Decimal("0"),
    categoria: CategoriaItem = None,
    descripcion: str = None,
    ubicacion: str = None,
    responsable: str = None,
    fecha_adquisicion=None,
    estado: str = ActivoFijo.Estado.ACTIVO,
    cuenta_activo_uuid=None,
    cuenta_depreciacion_uuid=None,
) -> ActivoFijo:
    """
    Crea un nuevo Activo Fijo en BD de forma atomica.

    Args:
        empresa: Instancia de Empresa (Zero Trust SSoT).
        codigo: Placa, serial o identificador unico.
        nombre: Nombre del activo.
        costo_adquisicion: Costo de adquisicion.
        ...campos opcionales...

    Returns:
        ActivoFijo: Instancia creada.
    """
    return ActivoFijo.objects.create(
        empresa=empresa,
        codigo=codigo,
        nombre=nombre,
        categoria=categoria,
        descripcion=descripcion,
        ubicacion=ubicacion,
        responsable=responsable,
        costo_adquisicion=costo_adquisicion,
        fecha_adquisicion=fecha_adquisicion,
        estado=estado,
        cuenta_activo_uuid=cuenta_activo_uuid,
        cuenta_depreciacion_uuid=cuenta_depreciacion_uuid,
    )


@transaction.atomic
def actualizar_activo(*, activo: ActivoFijo, **kwargs) -> ActivoFijo:
    """
    Actualiza campos de un Activo Fijo existente.

    Args:
        activo: Instancia de ActivoFijo a actualizar.
        **kwargs: Campos a actualizar.

    Returns:
        ActivoFijo: Instancia actualizada.
    """
    campos_actualizables = [
        'nombre', 'categoria', 'descripcion', 'ubicacion',
        'responsable', 'costo_adquisicion', 'fecha_adquisicion', 'estado',
        'cuenta_activo_uuid', 'cuenta_depreciacion_uuid',
    ]
    campos_modificados = []
    for campo in campos_actualizables:
        if campo in kwargs:
            setattr(activo, campo, kwargs[campo])
            campos_modificados.append(campo)

    if campos_modificados:
        campos_modificados.append('updated_at')
        activo.save(update_fields=campos_modificados)

    return activo


@transaction.atomic
def crear_movimiento_raw(
    *,
    empresa: Empresa,
    producto: Producto,
    tipo: str,
    cantidad: Decimal,
    costo_unitario: Decimal = Decimal("0"),
    origen_referencia: str = None,
    cliente_referencia: str = None,
    observaciones: str = None,
) -> MovimientoInventario:
    """
    Crea un movimiento de inventario en BD SIN recalcular stock.
    Usar solo cuando el recalculo de stock se maneja externamente.

    Args:
        empresa: Instancia de Empresa (Zero Trust SSoT).
        producto: Instancia de Producto.
        tipo: TipoMovimiento string.
        cantidad: Cantidad del movimiento.
        ...campos opcionales...

    Returns:
        MovimientoInventario: Instancia creada.
    """
    return MovimientoInventario.objects.create(
        empresa=empresa,
        producto=producto,
        tipo=tipo,
        cantidad=cantidad,
        costo_unitario=costo_unitario,
        origen_referencia=origen_referencia,
        cliente_referencia=cliente_referencia,
        observaciones=observaciones,
    )
