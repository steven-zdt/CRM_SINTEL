"""
selectors.py - Inventario v3.5

SSoT de QuerySets optimizados para el modulo de Inventario.
Este modulo contiene UNICAMENTE funciones de lectura (SELECT).
PROHIBIDO: logica de negocio, mutaciones, signals.

Reglas:
- Toda consulta filtra por empresa_id (Zero Trust / Anti-IDOR).
- Todo queryset usa .only(*FIELDS) + select_related() (Zero Waste).
- Constantes LIST_FIELDS y DETAIL_FIELDS como tuplas de strings (SSoT).
"""

from django.db.models import Q

from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import (
    ActivoFijo,
    CategoriaItem,
    HistorialServicio,
    MovimientoInventario,
    Producto,
    Servicio,
)

from django.core.exceptions import ValidationError

# ==============================================================================
# 1. CONSTANTES DE CAMPOS (SSoT - Single Source of Truth)
# ==============================================================================

CATEGORIA_LIST_FIELDS = (
    'id', 'nombre', 'descripcion', 'aplicacion', 'activo', 'empresa_id',
    'cuenta_inventario_uuid', 'cuenta_costo_uuid', 'cuenta_ingreso_uuid'
)

PRODUCTO_LIST_FIELDS = (
    'id', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__nombre',
    'stock_actual', 'stock_minimo', 'precio_venta', 'costo_promedio', 'activo', 'imagen', 'unidad', 
    'cuenta_inventario_uuid', 'cuenta_costo_uuid', 'empresa_id'
)

SERVICIO_LIST_FIELDS = (
    'id', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__nombre',
    'precio_venta', 'activo', 'imagen', 'cuenta_ingreso_uuid', 'empresa_id'
)

ACTIVO_LIST_FIELDS = (
    'id', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__nombre',
    'ubicacion', 'responsable', 'estado', 'fecha_adquisicion', 'costo_adquisicion', 
    'cuenta_activo_uuid', 'cuenta_depreciacion_uuid', 'empresa_id'
)

MOVIMIENTO_LIST_FIELDS = (
    'id', 'created_at', 'producto', 'producto__id', 'producto__codigo', 'producto__nombre',
    'tipo', 'cantidad', 'costo_unitario', 'origen_referencia', 'cliente_referencia', 'observaciones', 'empresa_id'
)

CATEGORIA_DETAIL_FIELDS = (
    'id', 'nombre', 'descripcion', 'aplicacion', 'imagen', 'activo',
    'cuenta_inventario_uuid', 'cuenta_costo_uuid', 'cuenta_ingreso_uuid',
    'created_at', 'updated_at', 'empresa_id'
)

PRODUCTO_DETAIL_FIELDS = (
    'id', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__nombre',
    'descripcion', 'unidad', 'imagen',
    'precio_venta', 'costo_promedio',
    'stock_actual', 'stock_minimo',
    'cuenta_inventario_uuid', 'cuenta_costo_uuid',
    'activo', 'created_at', 'updated_at', 'empresa_id'
)

SERVICIO_DETAIL_FIELDS = (
    'id', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__nombre',
    'descripcion', 'imagen', 'precio_venta',
    'cuenta_ingreso_uuid',
    'activo', 'created_at', 'updated_at', 'empresa_id'
)

ACTIVO_DETAIL_FIELDS = (
    'id', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__nombre',
    'marca', 'modelo', 'descripcion', 'imagen',
    'ubicacion', 'responsable',
    'fecha_adquisicion', 'costo_adquisicion', 'estado',
    'cuenta_activo_uuid', 'cuenta_depreciacion_uuid',
    'created_at', 'updated_at', 'empresa_id'
)

MOVIMIENTO_DETAIL_FIELDS = (
    'id', 'producto', 'producto__id', 'producto__codigo', 'producto__nombre',
    'tipo', 'cantidad', 'costo_unitario',
    'origen_referencia', 'cliente_referencia', 'observaciones',
    'created_at', 'updated_at', 'empresa_id'
)

# ==============================================================================
# 2. EMPRESA SINGLETON (Zero Trust SSoT)
# ==============================================================================

def get_empresa_singleton():
    """
    SSoT: Obtiene la empresa unica del tenant actual.
    Solo retorna campos necesarios (.only('id')).

    Raises:
        ValidationError: Si no existe una empresa configurada en este tenant.
    """
    empresa = Empresa.objects.only('id').first()
    if not empresa:
        raise ValidationError("No se encontro configuracion de Empresa para este tenant.")
    return empresa


def _obtener_empresa_singleton():
    """
    Helper interno: Obtiene y valida empresa singleton.

    Raises:
        ValidationError: Si no hay empresa o hay mas de una.
    """
    empresa = Empresa.objects.only('id').first()
    if not empresa:
        raise ValidationError("No se encontro la Empresa singleton del tenant.")
    if Empresa.objects.exclude(id=empresa.id).exists():
        raise ValidationError("Hay mas de una Empresa en este tenant (debe ser singleton).")
    return empresa


# ==============================================================================
# 3. QUERYSETS OPTIMIZADOS (Class-based Selectors)
# ==============================================================================

class ProductoSelector:
    @staticmethod
    def get_list(empresa_id: int, search: str = None):
        """
        QuerySet optimizado para LISTAR Productos (tabla Tabulator).
        """
        qs = (
            Producto.objects
            .filter(empresa_id=empresa_id)
            .select_related('categoria')
            .only(*PRODUCTO_LIST_FIELDS)
        )
        if search:
            qs = qs.filter(
                Q(codigo__icontains=search) |
                Q(nombre__icontains=search) |
                Q(categoria__nombre__icontains=search)
            )
        return qs

    @staticmethod
    def get_detail(empresa_id: int, producto_id: int):
        """
        QuerySet optimizado para DETALLE de Producto.
        """
        return (
            Producto.objects
            .filter(empresa_id=empresa_id, pk=producto_id)
            .select_related('categoria')
            .only(*PRODUCTO_DETAIL_FIELDS)
            .get()
        )


class ServicioSelector:
    @staticmethod
    def get_list(empresa_id: int, search: str = None):
        """
        QuerySet optimizado para LISTAR Servicios (tabla Tabulator).
        """
        qs = (
            Servicio.objects
            .filter(empresa_id=empresa_id)
            .select_related('categoria')
            .only(*SERVICIO_LIST_FIELDS)
        )
        if search:
            qs = qs.filter(
                Q(codigo__icontains=search) |
                Q(nombre__icontains=search) |
                Q(categoria__nombre__icontains=search)
            )
        return qs

    @staticmethod
    def get_detail(empresa_id: int, servicio_id: int):
        """
        QuerySet optimizado para DETALLE de Servicio.
        """
        return (
            Servicio.objects
            .filter(empresa_id=empresa_id, pk=servicio_id)
            .select_related('categoria')
            .only(*SERVICIO_DETAIL_FIELDS)
            .get()
        )


class ActivoFijoSelector:
    @staticmethod
    def get_list(empresa_id: int, search: str = None):
        """
        QuerySet optimizado para LISTAR Activos Fijos (tabla Tabulator).
        """
        qs = (
            ActivoFijo.objects
            .filter(empresa_id=empresa_id)
            .select_related('categoria')
            .only(*ACTIVO_LIST_FIELDS)
        )
        if search:
            qs = qs.filter(
                Q(codigo__icontains=search) |
                Q(nombre__icontains=search) |
                Q(categoria__nombre__icontains=search) |
                Q(ubicacion__icontains=search) |
                Q(responsable__icontains=search)
            )
        return qs

    @staticmethod
    def get_detail(empresa_id: int, activo_id: int):
        """
        QuerySet optimizado para DETALLE de Activo Fijo.
        """
        return (
            ActivoFijo.objects
            .filter(empresa_id=empresa_id, pk=activo_id)
            .select_related('categoria')
            .only(*ACTIVO_DETAIL_FIELDS)
            .get()
        )


class MovimientoInventarioSelector:
    @staticmethod
    def get_list(empresa_id: int, search: str = None):
        """
        QuerySet optimizado para LISTAR Movimientos de Inventario (Kardex).
        """
        qs = (
            MovimientoInventario.objects
            .filter(producto__empresa_id=empresa_id)
            .select_related('producto')
            .only(*MOVIMIENTO_LIST_FIELDS)
        )
        if search:
            qs = qs.filter(
                Q(producto__codigo__icontains=search) |
                Q(producto__nombre__icontains=search) |
                Q(origen_referencia__icontains=search) |
                Q(observaciones__icontains=search)
            )
        return qs

    @staticmethod
    def get_detail(empresa_id: int, movimiento_id: int):
        """
        QuerySet optimizado para DETALLE de Movimiento.
        """
        return (
            MovimientoInventario.objects
            .filter(empresa_id=empresa_id, pk=movimiento_id)
            .select_related('producto')
            .only(*MOVIMIENTO_DETAIL_FIELDS)
            .get()
        )


class CategoriaItemSelector:
    @staticmethod
    def get_list(empresa_id: int = None, search: str = None):
        """
        QuerySet optimizado para LISTAR Categorias (tabla Tabulator).
        """
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

    @staticmethod
    def get_detail(empresa_id: int, categoria_id: int):
        """
        QuerySet optimizado para DETALLE de Categoria.
        """
        return (
            CategoriaItem.objects
            .filter(empresa_id=empresa_id, pk=categoria_id)
            .only(*CATEGORIA_DETAIL_FIELDS)
            .get()
        )


class HistorialServicioSelector:
    @staticmethod
    def get_list(empresa):
        """
        QuerySet optimizado para LISTAR Historial de Servicios.
        """
        return (
            HistorialServicio.objects
            .select_related('servicio')
            .filter(empresa=empresa)
            .only(
                'id', 'fecha_registro', 'cantidad', 'valor_cobrado',
                'origen_referencia', 'cliente_referencia', 'observaciones',
                'servicio__nombre'
            )
            .order_by('-fecha_registro')
        )
