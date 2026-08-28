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

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Q, Sum

from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import (
    ActivoFijo,
    CategoriaItem,
    HistorialServicio,
    MovimientoInventario,
    Producto,
    Servicio,
    TrasladoInventario,
)

# ==============================================================================
# 1. CONSTANTES DE CAMPOS (SSoT - Single Source of Truth)
# ==============================================================================

CATEGORIA_LIST_FIELDS = (
    'id', 'uuid', 'nombre', 'descripcion', 'aplicacion', 'activo', 'empresa_id',
)

PRODUCTO_LIST_FIELDS = (
    'id', 'uuid', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__uuid', 'categoria__nombre',
    'stock_actual', 'stock_minimo', 'precio_venta', 'costo_promedio', 'activo', 'imagen', 'unidad', 
)

SERVICIO_LIST_FIELDS = (
    'id', 'uuid', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__uuid', 'categoria__nombre',
    'precio_venta', 'activo', 'imagen',
)

ACTIVO_LIST_FIELDS = (
    'id', 'uuid', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__uuid', 'categoria__nombre',
    'ubicacion', 'responsable', 'estado', 'fecha_adquisicion', 'costo_adquisicion', 
)

MOVIMIENTO_LIST_FIELDS = (
    'id', 'uuid', 'created_at',
    'producto', 'producto__id', 'producto__uuid', 'producto__codigo', 'producto__nombre',
    'activo_fijo', 'activo_fijo__id', 'activo_fijo__uuid', 'activo_fijo__codigo', 'activo_fijo__nombre',
    'tipo', 'cantidad', 'costo_unitario', 'origen_referencia', 'cliente_referencia', 'observaciones', 'empresa_id',
    'sede_id', 'sede__nombre',  # DT-SEDE-05: KPI por sede
)

CATEGORIA_DETAIL_FIELDS = (
    'id', 'uuid', 'nombre', 'descripcion', 'aplicacion', 'imagen', 'activo',
    'created_at', 'updated_at', 'empresa_id'
)

PRODUCTO_DETAIL_FIELDS = (
    'id', 'uuid', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__uuid', 'categoria__nombre',
    'descripcion', 'unidad', 'imagen',
    'precio_venta', 'costo_promedio',
    'stock_actual', 'stock_minimo',
    'activo', 'created_at', 'updated_at', 'empresa_id'
)

SERVICIO_DETAIL_FIELDS = (
    'id', 'uuid', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__uuid', 'categoria__nombre',
    'descripcion', 'imagen', 'precio_venta',
    'activo', 'created_at', 'updated_at', 'empresa_id'
)

ACTIVO_DETAIL_FIELDS = (
    'id', 'uuid', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__uuid', 'categoria__nombre',
    'marca', 'modelo', 'descripcion', 'imagen',
    'ubicacion', 'responsable',
    'fecha_adquisicion', 'costo_adquisicion', 'estado',
    'created_at', 'updated_at', 'empresa_id'
)

MOVIMIENTO_DETAIL_FIELDS = (
    'id', 'uuid',
    'producto', 'producto__id', 'producto__uuid', 'producto__codigo', 'producto__nombre',
    'activo_fijo', 'activo_fijo__id', 'activo_fijo__uuid', 'activo_fijo__codigo', 'activo_fijo__nombre',
    'tipo', 'cantidad', 'costo_unitario',
    'origen_referencia', 'cliente_referencia', 'observaciones',
    'sede_id', 'sede__uuid', 'sede__nombre',  # DT-SEDE-05
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
    def get_detail(empresa_id: int, producto_uuid):
        """
        QuerySet optimizado para DETALLE de Producto.
        """
        return (
            Producto.objects
            .filter(empresa_id=empresa_id, uuid=producto_uuid)
            .select_related('categoria')
            .only(*PRODUCTO_DETAIL_FIELDS)
            .get()
        )

    @staticmethod
    def get_by_id(empresa_id: int, producto_id: int):
        """Obtiene un producto por PK interno solo para payloads ya validados."""
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
    def get_detail(empresa_id: int, servicio_uuid):
        """
        QuerySet optimizado para DETALLE de Servicio.
        """
        return (
            Servicio.objects
            .filter(empresa_id=empresa_id, uuid=servicio_uuid)
            .select_related('categoria')
            .only(*SERVICIO_DETAIL_FIELDS)
            .get()
        )

    @staticmethod
    def get_by_id(empresa_id: int, servicio_id: int):
        """Obtiene un servicio por PK interno solo para payloads ya validados."""
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
    def get_detail(empresa_id: int, activo_uuid):
        """
        QuerySet optimizado para DETALLE de Activo Fijo.
        """
        return (
            ActivoFijo.objects
            .filter(empresa_id=empresa_id, uuid=activo_uuid)
            .select_related('categoria')
            .only(*ACTIVO_DETAIL_FIELDS)
            .get()
        )

    @staticmethod
    def get_by_id(empresa_id: int, activo_id: int):
        """Obtiene un activo por PK interno solo para payloads ya validados."""
        return (
            ActivoFijo.objects
            .filter(empresa_id=empresa_id, pk=activo_id)
            .select_related('categoria')
            .only(*ACTIVO_DETAIL_FIELDS)
            .get()
        )


class MovimientoInventarioSelector:
    @staticmethod
    def get_list(empresa_id: int, search: str = None, sede_ids=None):
        """
        QuerySet optimizado para LISTAR Movimientos de Inventario (Kardex).

        [OSF Fase F7] `sede_ids=None` (default) no restringe por sede -
        comportamiento identico al de antes de esta fase. El 100% de los
        MovimientoInventario reales tiene sede=NULL hoy (verificado
        empiricamente, el campo era puramente informativo, DT-SEDE-05) - un
        registro sin sede queda visible para todos los alcances (filtro
        NULL-safe), para no ocultar datos existentes al activar el filtrado.
        """
        qs = (
            MovimientoInventario.objects
            .filter(empresa_id=empresa_id)
            .select_related('producto', 'activo_fijo')
            .only(*MOVIMIENTO_LIST_FIELDS)
        )
        if sede_ids is not None:
            qs = qs.filter(Q(sede_id__isnull=True) | Q(sede_id__in=sede_ids))
        if search:
            qs = qs.filter(
                Q(producto__codigo__icontains=search) |
                Q(producto__nombre__icontains=search) |
                Q(activo_fijo__codigo__icontains=search) |
                Q(activo_fijo__nombre__icontains=search) |
                Q(origen_referencia__icontains=search) |
                Q(observaciones__icontains=search)
            )
        return qs

    @staticmethod
    def get_detail(empresa_id: int, movimiento_uuid, sede_ids=None):
        """
        QuerySet optimizado para DETALLE de Movimiento.

        [OSF Fase F13] `sede_ids=None` (default) no restringe - mismo
        criterio NULL-safe de F7 (get_list). Antes de esta fase,
        `MovimientoInventarioViewSet.get_object()` (retrieve/update/
        partial_update/destroy) y `service_movimiento_get_offcanvas_context()`
        solo filtraban por empresa_id - mismo gap que F11/F13(gastos/
        cotizaciones) encontraron y corrigieron.
        """
        qs = (
            MovimientoInventario.objects
            .filter(empresa_id=empresa_id, uuid=movimiento_uuid)
            .select_related('producto', 'activo_fijo')
            .only(*MOVIMIENTO_DETAIL_FIELDS)
        )
        if sede_ids is not None:
            qs = qs.filter(Q(sede_id__isnull=True) | Q(sede_id__in=sede_ids))
        return qs.get()

    @staticmethod
    def get_kardex_for_producto(empresa_id: int, producto_id: int):
        """Retorna movimientos de Kardex para un producto ya validado."""
        return (
            MovimientoInventario.objects
            .filter(empresa_id=empresa_id, producto_id=producto_id)
            .select_related('producto')
            .only(*MOVIMIENTO_LIST_FIELDS)
            .order_by('-created_at')
        )


class StockPorSedeSelector:
    """
    F21: resuelve "stock por sede" via agregacion de MovimientoInventario.sede,
    sin persistir un campo nuevo en Producto. Decision registrada en
    documentacion/F21_ORGANIZATIONAL_DECISIONS.md: Producto sigue siendo
    Empresa->Producto (stock_actual agregado); la dimension Sede solo vive en
    el movimiento, resuelta en lectura (mismo criterio que Kardex.calcular_stock,
    aplicado con un filtro adicional de sede_id).
    """
    TIPOS_ENTRADA_SEDE = (
        MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
        MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
        MovimientoInventario.TipoMovimiento.ENTRADA_DEVOLUCION,
        MovimientoInventario.TipoMovimiento.TRASLADO_ENTRADA,
    )
    TIPOS_SALIDA_SEDE = (
        MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
        MovimientoInventario.TipoMovimiento.SALIDA_BAJA,
        MovimientoInventario.TipoMovimiento.SALIDA_CONSUMO,
        MovimientoInventario.TipoMovimiento.TRASLADO_SALIDA,
    )

    @staticmethod
    def calcular_stock_sede(empresa_id: int, producto_id: int, sede_id: int) -> Decimal:
        """
        Stock de un producto en una sede especifica.

        Movimientos historicos con sede=NULL (anteriores a la adopcion de F21,
        o registrados sin sede porque "aplica a toda la empresa") deliberadamente
        NO se cuentan aqui — no se les asigna una sede inventada (prohibido
        explicitamente por el prompt maestro F21 §39/§52). Ver
        calcular_stock_sin_asignar() para ese resto.
        """
        entradas = MovimientoInventario.objects.filter(
            empresa_id=empresa_id, producto_id=producto_id, sede_id=sede_id,
            tipo__in=StockPorSedeSelector.TIPOS_ENTRADA_SEDE,
        ).aggregate(total=Sum('cantidad'))['total'] or Decimal('0')
        salidas = MovimientoInventario.objects.filter(
            empresa_id=empresa_id, producto_id=producto_id, sede_id=sede_id,
            tipo__in=StockPorSedeSelector.TIPOS_SALIDA_SEDE,
        ).aggregate(total=Sum('cantidad'))['total'] or Decimal('0')
        return entradas - salidas

    @staticmethod
    def calcular_stock_sin_asignar(empresa_id: int, producto_id: int) -> Decimal:
        """Stock proveniente de movimientos sin sede asignada (sede_id NULL)."""
        entradas = MovimientoInventario.objects.filter(
            empresa_id=empresa_id, producto_id=producto_id, sede_id__isnull=True,
            tipo__in=StockPorSedeSelector.TIPOS_ENTRADA_SEDE,
        ).aggregate(total=Sum('cantidad'))['total'] or Decimal('0')
        salidas = MovimientoInventario.objects.filter(
            empresa_id=empresa_id, producto_id=producto_id, sede_id__isnull=True,
            tipo__in=StockPorSedeSelector.TIPOS_SALIDA_SEDE,
        ).aggregate(total=Sum('cantidad'))['total'] or Decimal('0')
        return entradas - salidas

    @staticmethod
    def calcular_en_transito(empresa_id: int, producto_id: int, sede_origen_id: int = None) -> Decimal:
        """
        Cantidad en transito de un producto: suma de TrasladoInventario en
        estado EN_TRANSITO. Se resuelve contra el estado real del traslado
        (no re-derivado desde MovimientoInventario) para no crear una segunda
        fuente de verdad sobre en que estado esta el traslado.
        """
        from apps.tenant.inventario.models import TrasladoInventario
        qs = TrasladoInventario.objects.filter(
            empresa_id=empresa_id,
            producto_id=producto_id,
            estado=TrasladoInventario.Estado.EN_TRANSITO,
        )
        if sede_origen_id is not None:
            qs = qs.filter(sede_origen_id=sede_origen_id)
        return qs.aggregate(total=Sum('cantidad'))['total'] or Decimal('0')


TRASLADO_LIST_FIELDS = (
    'id', 'uuid', 'cantidad', 'estado', 'motivo', 'empresa_id',
    'producto_id', 'sede_origen_id', 'sede_destino_id', 'area_origen_id', 'area_destino_id',
    'usuario_solicita_id', 'usuario_aprueba_id', 'usuario_recibe_id',
    'fecha_solicitud', 'fecha_aprobacion', 'fecha_envio', 'fecha_recepcion', 'created_at',
)


class TrasladoInventarioSelector:
    """Selectores de solo lectura para TrasladoInventario (F21)."""

    @staticmethod
    def get_list(empresa_id: int, estado: str = None, sede_ids=None):
        qs = (
            TrasladoInventario.objects
            .filter(empresa_id=empresa_id)
            .select_related('producto', 'sede_origen', 'sede_destino', 'area_origen', 'area_destino')
            .only(
                *TRASLADO_LIST_FIELDS,
                'producto__codigo', 'producto__nombre',
                'sede_origen__nombre', 'sede_destino__nombre',
                'area_origen__nombre', 'area_destino__nombre',
            )
        )
        if sede_ids is not None:
            qs = qs.filter(Q(sede_origen_id__in=sede_ids) | Q(sede_destino_id__in=sede_ids))
        if estado:
            qs = qs.filter(estado=estado)
        return qs.order_by('-created_at')

    @staticmethod
    def get_detail(empresa_id: int, traslado_uuid: str):
        return (
            TrasladoInventario.objects
            .filter(empresa_id=empresa_id, uuid=traslado_uuid)
            .select_related('producto', 'sede_origen', 'sede_destino', 'area_origen', 'area_destino')
        )


class CategoriaItemSelector:
    @staticmethod
    def get_list(empresa_id: int, search: str = None):
        """
        QuerySet optimizado para LISTAR Categorias (tabla Tabulator).
        """
        if not empresa_id:
            raise ValidationError("empresa_id es obligatorio para listar categorias.")
        qs = CategoriaItem.objects.filter(empresa_id=empresa_id).only(*CATEGORIA_LIST_FIELDS)
        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) |
                Q(descripcion__icontains=search)
            )
        return qs

    @staticmethod
    def get_detail(empresa_id: int, categoria_uuid):
        """
        QuerySet optimizado para DETALLE de Categoria.
        """
        return (
            CategoriaItem.objects
            .filter(empresa_id=empresa_id, uuid=categoria_uuid)
            .only(*CATEGORIA_DETAIL_FIELDS)
            .get()
        )

    @staticmethod
    def get_by_id(empresa_id: int, categoria_id: int):
        """Obtiene una categoria por PK interno solo para payloads ya validados."""
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
                'id', 'uuid', 'fecha_registro', 'cantidad', 'valor_cobrado',
                'origen_referencia', 'cliente_referencia', 'observaciones',
                'servicio', 'servicio__uuid', 'servicio__codigo', 'servicio__nombre',
                'proyecto_uuid', 'proyecto_nombre',
            )
            .order_by('-fecha_registro')
        )


# ==============================================================================
# 4. TIMELINE UNIFICADO — Ledger Universal (v3.9.0)
# ==============================================================================

import datetime as _dt


def _normalizar_fecha(val):
    """Convierte datetime/date a datetime naive para ordenamiento uniforme."""
    if val is None:
        return _dt.datetime.min
    if isinstance(val, _dt.datetime):
        return val.replace(tzinfo=None) if val.tzinfo is not None else val
    if isinstance(val, _dt.date):
        return _dt.datetime(val.year, val.month, val.day)
    return _dt.datetime.min


def get_movimientos_timeline(empresa_id: int, search: str = None, desde=None) -> list:
    """
    Combina MovimientoInventario (PRODUCTO/ACTIVO_FIJO) y HistorialServicio (SERVICIO)
    en una lista unificada ordenada cronologicamente descendente.
    Retorna lista de dicts con estructura comun para MovimientoUnificadoListSerializer.
    Patron: Ledger Universal — trazabilidad completa del modulo Inventario.

    Args:
        desde: [PERF-M2] fecha/datetime opcional -- si se provee, acota ambos
            querysets a created_at >= desde. None (default) preserva el
            comportamiento historico sin filtro para los llamadores existentes
            (p.ej. la UI de "ver historial completo" de inventario).
    """
    qs_mov = (
        MovimientoInventario.objects
        .filter(empresa_id=empresa_id)
        .select_related('producto', 'activo_fijo')
        .only(*MOVIMIENTO_LIST_FIELDS)
    )
    if desde:
        qs_mov = qs_mov.filter(created_at__gte=desde)
    if search:
        qs_mov = qs_mov.filter(
            Q(producto__nombre__icontains=search) |
            Q(activo_fijo__nombre__icontains=search) |
            Q(origen_referencia__icontains=search) |
            Q(observaciones__icontains=search)
        )

    qs_hist = (
        HistorialServicio.objects
        .filter(empresa_id=empresa_id)
        .select_related('servicio')
        .only(
            'id', 'uuid', 'fecha_registro', 'cantidad', 'valor_cobrado',
            'origen_referencia', 'cliente_referencia', 'observaciones',
            'servicio', 'servicio__uuid', 'servicio__codigo', 'servicio__nombre',
            'proyecto_uuid', 'proyecto_nombre',
        )
    )
    if desde:
        qs_hist = qs_hist.filter(fecha_registro__gte=desde)
    if search:
        qs_hist = qs_hist.filter(
            Q(servicio__nombre__icontains=search) |
            Q(origen_referencia__icontains=search) |
            Q(cliente_referencia__icontains=search) |
            Q(observaciones__icontains=search)
        )

    resultado = []

    for mov in qs_mov:
        if mov.producto_id:
            modulo = 'PRODUCTO'
            p = mov.producto
            item_nombre = p.nombre if p else ''
            item_codigo = p.codigo if p else ''
            item_uuid = str(p.uuid) if p else ''
        else:
            modulo = 'ACTIVO_FIJO'
            a = mov.activo_fijo
            item_nombre = a.nombre if a else ''
            item_codigo = a.codigo if a else ''
            item_uuid = str(a.uuid) if a else ''

        fecha_dt = mov.created_at
        resultado.append({
            '_sort': _normalizar_fecha(fecha_dt),
            'uuid': str(mov.uuid),
            'documento_id': mov.id,
            'modelo_origen': 'MovimientoInventario',
            'fecha': fecha_dt.isoformat() if fecha_dt else '',
            'modulo_origen': modulo,
            'item_uuid': item_uuid,
            'item_codigo': item_codigo,
            'item_nombre': item_nombre,
            'tipo_accion': mov.tipo,
            'tipo_accion_display': mov.get_tipo_display(),
            'cantidad': str(mov.cantidad or 0),
            'valor_costo': str(mov.costo_unitario or 0),
            'referencia': mov.origen_referencia or '',
            'observaciones': mov.observaciones or '',
        })

    for hist in qs_hist:
        svc = hist.servicio
        fecha_dt = _dt.datetime.combine(hist.fecha_registro, _dt.time.min) if hist.fecha_registro else None
        resultado.append({
            '_sort': _normalizar_fecha(fecha_dt),
            'uuid': str(hist.uuid),
            'documento_id': hist.id,
            'modelo_origen': 'HistorialServicio',
            'fecha': hist.fecha_registro.isoformat() if hist.fecha_registro else '',
            'modulo_origen': 'SERVICIO',
            'item_uuid': str(svc.uuid) if svc else '',
            'item_codigo': svc.codigo if svc else '',
            'item_nombre': svc.nombre if svc else '',
            'tipo_accion': 'VENTA_SERVICIO',
            'tipo_accion_display': 'Venta de Servicio',
            'cantidad': str(hist.cantidad or 0),
            'valor_costo': str(hist.valor_cobrado or 0),
            'referencia': hist.origen_referencia or '',
            'observaciones': hist.observaciones or '',
            'proyecto_uuid': str(hist.proyecto_uuid) if hist.proyecto_uuid else '',
            'proyecto_nombre': hist.proyecto_nombre or '',
        })

    resultado.sort(key=lambda x: x['_sort'], reverse=True)
    for item in resultado:
        del item['_sort']

    return resultado
