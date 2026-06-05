"""
business_service.py - Inventario v3.5

Capa de logica de negocio (Business Logic Layer) para el modulo de Inventario.
Contiene: calculos de stock, validaciones semanticas, movimientos de Kardex,
ingesta masiva de datos y Service Mixins para ViewSets.

Reglas:
- Toda mutacion de stock usa @transaction.atomic.
- Toda validacion de pertenencia al tenant pasa por selectors.py (Zero Trust).
- Los Service Mixins inyectan metodos a los ViewSets via herencia.
- PROHIBIDO queries directas en Mixins sin pasar por selectors.
"""

from decimal import Decimal
from typing import Optional, List, Dict, Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import (
    ActivoFijo,
    CategoriaItem,
    HistorialServicio,
    MovimientoInventario,
    Producto,
    Servicio,
)
from apps.tenant.inventario.services.selectors import (
    MOVIMIENTO_LIST_FIELDS,
    ActivoFijoSelector,
    CategoriaItemSelector,
    MovimientoInventarioSelector,
    ProductoSelector,
    ServicioSelector,
)

# ==============================================================================
# 1. MOTOR DE KARDEX (Stock Calculation Engine)
# ==============================================================================

class KardexService:
    """Motor transaccional append-only para movimientos y stock de productos."""

    TIPOS_ENTRADA = (
        MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
        MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
        MovimientoInventario.TipoMovimiento.ENTRADA_DEVOLUCION,
    )
    TIPOS_SALIDA = (
        MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
        MovimientoInventario.TipoMovimiento.SALIDA_BAJA,
        MovimientoInventario.TipoMovimiento.SALIDA_CONSUMO,
    )

    @staticmethod
    def calcular_stock(producto_id: int, empresa_id: int) -> Decimal:
        """Calcula entradas menos salidas para un producto del tenant."""
        if not Producto.objects.filter(pk=producto_id, empresa_id=empresa_id).only('id').exists():
            return Decimal("0")

        suma_entradas = MovimientoInventario.objects.filter(
            empresa_id=empresa_id,
            producto_id=producto_id,
            tipo__in=KardexService.TIPOS_ENTRADA,
        ).aggregate(total=Sum("cantidad"))["total"] or Decimal("0")

        suma_salidas = MovimientoInventario.objects.filter(
            empresa_id=empresa_id,
            producto_id=producto_id,
            tipo__in=KardexService.TIPOS_SALIDA,
        ).aggregate(total=Sum("cantidad"))["total"] or Decimal("0")

        return suma_entradas - suma_salidas

    @staticmethod
    def recalcular_stock_producto(producto_id: int, empresa_id: int) -> Decimal:
        """
        Recalcula `stock_actual` bajo lock de fila para evitar carreras concurrentes.
        """
        producto = (
            Producto.objects
            .select_for_update()
            .only('id', 'empresa_id', 'stock_actual')
            .get(id=producto_id, empresa_id=empresa_id)
        )
        nuevo_stock = KardexService.calcular_stock(producto.id, empresa_id)
        producto.stock_actual = nuevo_stock
        producto.save(update_fields=['stock_actual', 'updated_at'])
        return nuevo_stock

    @staticmethod
    @transaction.atomic
    def registrar_movimiento(
        *,
        empresa_id: int,
        producto_id: int,
        tipo: str,
        cantidad: Decimal,
        costo_unitario: Decimal = Decimal("0"),
        origen_referencia: str = None,
        cliente_referencia: str = None,
        observaciones: str = None,
    ) -> MovimientoInventario:
        """Registra un movimiento append-only y actualiza stock en la misma transaccion."""
        cantidad = Decimal(str(cantidad or "0"))
        if cantidad <= 0:
            raise ValidationError("La cantidad del movimiento debe ser positiva.")

        producto = (
            Producto.objects
            .select_for_update()
            .only('id', 'empresa_id', 'stock_actual')
            .filter(pk=producto_id, empresa_id=empresa_id, activo=True)
            .first()
        )
        if not producto:
            raise ValidationError("El producto no existe, esta inactivo o no pertenece a este tenant.")

        if tipo not in KardexService.TIPOS_ENTRADA and tipo not in KardexService.TIPOS_SALIDA:
            raise ValidationError(f"Tipo de movimiento invalido: {tipo}")

        if tipo in KardexService.TIPOS_SALIDA and producto.stock_actual < cantidad:
            raise ValidationError(
                f"Stock insuficiente. Disponible: {producto.stock_actual}, Solicitado: {cantidad}"
            )

        movimiento = MovimientoInventario.objects.create(
            empresa_id=empresa_id,
            producto=producto,
            tipo=tipo,
            cantidad=cantidad,
            costo_unitario=Decimal(str(costo_unitario or "0")),
            origen_referencia=origen_referencia,
            cliente_referencia=cliente_referencia,
            observaciones=observaciones,
        )
        KardexService.recalcular_stock_producto(producto.id, empresa_id)
        return movimiento

    @staticmethod
    def registrar_entrada(**kwargs) -> MovimientoInventario:
        """Registra una entrada de inventario."""
        kwargs.setdefault('tipo', MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA)
        return KardexService.registrar_movimiento(**kwargs)

    @staticmethod
    def registrar_salida(**kwargs) -> MovimientoInventario:
        """Registra una salida de inventario."""
        kwargs.setdefault('tipo', MovimientoInventario.TipoMovimiento.SALIDA_VENTA)
        return KardexService.registrar_movimiento(**kwargs)

    @staticmethod
    def ajustar_stock(producto_id: int, empresa_id: int, cantidad_ajuste: Decimal, observaciones: str = None):
        """Crea un movimiento de ajuste positivo o negativo."""
        cantidad_ajuste = Decimal(str(cantidad_ajuste or "0"))
        tipo = (
            MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE
            if cantidad_ajuste > 0
            else MovimientoInventario.TipoMovimiento.SALIDA_BAJA
        )
        return KardexService.registrar_movimiento(
            empresa_id=empresa_id,
            producto_id=producto_id,
            tipo=tipo,
            cantidad=abs(cantidad_ajuste),
            observaciones=observaciones or f"Ajuste de inventario: {cantidad_ajuste} unidades",
        )

    # Mapeo de tipo de movimiento de activo fijo al nuevo estado del activo
    _TRANSICION_ESTADO_ACTIVO = {
        MovimientoInventario.TipoMovimiento.TRASLADO_MANTENIMIENTO: ActivoFijo.Estado.MANTENIMIENTO,
        MovimientoInventario.TipoMovimiento.RETORNO_MANTENIMIENTO: ActivoFijo.Estado.ACTIVO,
        MovimientoInventario.TipoMovimiento.SALIDA_BAJA_ACTIVO: ActivoFijo.Estado.BAJA,
    }

    _TIPOS_ACTIVO = (
        MovimientoInventario.TipoMovimiento.ASIGNACION_RESPONSABLE,
        MovimientoInventario.TipoMovimiento.TRASLADO_MANTENIMIENTO,
        MovimientoInventario.TipoMovimiento.RETORNO_MANTENIMIENTO,
        MovimientoInventario.TipoMovimiento.SALIDA_BAJA_ACTIVO,
    )

    @staticmethod
    @transaction.atomic
    def registrar_movimiento_activo(
        *,
        empresa_id: int,
        activo_fijo_id: int,
        tipo: str,
        costo_unitario: Decimal = Decimal("0"),
        origen_referencia: str = None,
        cliente_referencia: str = None,
        observaciones: str = None,
    ) -> MovimientoInventario:
        """Registra un evento de Activo Fijo y actualiza su estado atomicamente."""
        if tipo not in KardexService._TIPOS_ACTIVO:
            raise ValidationError(f"Tipo de movimiento no valido para Activo Fijo: {tipo}")

        activo = (
            ActivoFijo.objects
            .select_for_update()
            .only('id', 'empresa_id', 'estado')
            .filter(pk=activo_fijo_id, empresa_id=empresa_id)
            .first()
        )
        if not activo:
            raise ValidationError("El activo fijo no existe o no pertenece a este tenant.")

        movimiento = MovimientoInventario.objects.create(
            empresa_id=empresa_id,
            activo_fijo=activo,
            tipo=tipo,
            cantidad=Decimal("1"),
            costo_unitario=Decimal(str(costo_unitario or "0")),
            origen_referencia=origen_referencia,
            cliente_referencia=cliente_referencia,
            observaciones=observaciones,
        )

        nuevo_estado = KardexService._TRANSICION_ESTADO_ACTIVO.get(tipo)
        if nuevo_estado:
            activo.estado = nuevo_estado
            activo.save(update_fields=['estado', 'updated_at'])

        return movimiento

    @staticmethod
    @transaction.atomic
    def actualizar_movimiento(
        *,
        movimiento: 'MovimientoInventario',
        empresa_id: int,
        nueva_cantidad: Decimal = None,
        nuevo_tipo: str = None,
        nuevo_costo: Decimal = None,
        nuevo_origen: str = None,
        nuevas_observaciones: str = None,
    ) -> 'MovimientoInventario':
        """
        Actualiza un movimiento de Producto y recalcula stock atomicamente.
        select_for_update() en recalcular_stock_producto previene carreras concurrentes.
        Solo actua sobre MovimientoInventario con producto_id (no Activos).
        """
        recalcular = False

        if nueva_cantidad is not None:
            nueva_cantidad = Decimal(str(nueva_cantidad))
            if nueva_cantidad <= 0:
                raise ValidationError("La cantidad debe ser mayor a cero.")
            if nueva_cantidad != movimiento.cantidad:
                movimiento.cantidad = nueva_cantidad
                recalcular = True

        if nuevo_tipo is not None and nuevo_tipo != movimiento.tipo:
            movimiento.tipo = nuevo_tipo
            recalcular = True

        if nuevo_costo is not None:
            movimiento.costo_unitario = Decimal(str(nuevo_costo))

        if nuevo_origen is not None:
            movimiento.origen_referencia = nuevo_origen

        if nuevas_observaciones is not None:
            movimiento.observaciones = nuevas_observaciones

        movimiento.save()

        if recalcular and movimiento.producto_id:
            KardexService.recalcular_stock_producto(movimiento.producto_id, empresa_id)

        return movimiento

    @staticmethod
    @transaction.atomic
    def eliminar_movimiento(
        *,
        movimiento: 'MovimientoInventario',
        empresa_id: int,
    ) -> None:
        """
        Elimina un movimiento y recalcula stock atomicamente.
        El recalculo ejecuta select_for_update() sobre el Producto afectado.
        """
        producto_id = movimiento.producto_id
        movimiento.delete()
        if producto_id:
            KardexService.recalcular_stock_producto(producto_id, empresa_id)


def calcular_stock(producto_id: int) -> Decimal:
    """
    Calcula el stock actual de un producto basado en sus movimientos (solo lectura).
    No actualiza el campo stock_actual. Usar recalcular_stock_producto() para actualizar.

    Returns:
        Decimal: Stock calculado (entradas - salidas + ajustes).
    """
    producto = Producto.objects.filter(pk=producto_id).only('id', 'empresa_id').first()
    if not producto:
        return Decimal("0")
    return KardexService.calcular_stock(producto.id, producto.empresa_id)


def recalcular_stock_producto(producto_id: int) -> Decimal:
    """
    Recalcula el stock fisico de un producto y actualiza el campo desnormalizado
    `stock_actual`. Usa select_for_update() para lock optimista.

    Returns:
        Decimal: El nuevo stock calculado.
    """
    with transaction.atomic():
        producto = Producto.objects.only('id', 'empresa_id').get(id=producto_id)
        return KardexService.recalcular_stock_producto(producto.id, producto.empresa_id)


# ==============================================================================
# 2. OPERACIONES DE MOVIMIENTO (Transaccionales)
# ==============================================================================

@transaction.atomic
def registrar_entrada(
    producto_id: int,
    empresa_id: int,
    cantidad: Decimal,
    tipo_movimiento: Optional[str] = None,
    costo_unitario: Optional[Decimal] = None,
    origen_referencia: Optional[str] = None,
    observaciones: Optional[str] = None,
) -> MovimientoInventario:
    """
    Registra una entrada de producto (compra, devolucion, ajuste positivo) con Zero Trust.

    Raises:
        ValidationError: Si la cantidad es negativa o el producto no pertenece al tenant.
    """
    return KardexService.registrar_movimiento(
        empresa_id=empresa_id,
        producto_id=producto_id,
        tipo=tipo_movimiento or MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
        cantidad=cantidad,
        costo_unitario=costo_unitario or Decimal('0'),
        origen_referencia=origen_referencia,
        observaciones=observaciones,
    )


@transaction.atomic
def registrar_salida(
    producto_id: int,
    empresa_id: int,
    cantidad: Decimal,
    tipo_movimiento: Optional[str] = None,
    costo_unitario: Optional[Decimal] = None,
    origen_referencia: Optional[str] = None,
    cliente_referencia: Optional[str] = None,
    observaciones: Optional[str] = None,
) -> MovimientoInventario:
    """
    Registra una salida de producto (venta, baja, consumo) con Zero Trust.

    Raises:
        ValidationError: Si stock insuficiente o el producto no pertenece al tenant.
    """
    return KardexService.registrar_movimiento(
        empresa_id=empresa_id,
        producto_id=producto_id,
        tipo=tipo_movimiento or MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
        cantidad=cantidad,
        costo_unitario=costo_unitario or Decimal('0'),
        origen_referencia=origen_referencia,
        cliente_referencia=cliente_referencia,
        observaciones=observaciones,
    )


@transaction.atomic
def ajustar_stock(
    producto_id: int,
    empresa_id: int,
    cantidad_ajuste: Decimal,
    observaciones: str = None,
) -> MovimientoInventario:
    """
    Ajusta el stock de un producto (positivo o negativo). Zero Trust.

    Raises:
        ValidationError: Si el ajuste resultaria en stock negativo o producto no existe.
    """
    return KardexService.ajustar_stock(producto_id, empresa_id, cantidad_ajuste, observaciones)


def registrar_movimiento(
    producto_id: int,
    tipo: str,
    cantidad: Decimal,
    empresa: Empresa,
    costo_unitario: Decimal = 0,
    origen_referencia: str = None,
    cliente_referencia: str = None,
    observaciones: str = None,
    usuario=None,
) -> MovimientoInventario:
    """
    Funcion generica para registrar un movimiento desde APIs externas (Ventas, Compras).
    Para entradas simples, preferir registrar_entrada().
    """
    return KardexService.registrar_movimiento(
        empresa_id=empresa.id,
        producto_id=producto_id,
        tipo=tipo,
        cantidad=cantidad,
        costo_unitario=costo_unitario,
        origen_referencia=origen_referencia,
        cliente_referencia=cliente_referencia,
        observaciones=observaciones,
    )




# ==============================================================================
# 4. SERVICE MIXINS (Inyeccion por Herencia - Regla 4.4 SINTEL)
# ==============================================================================

class CategoriaItemServiceMixin:
    """Mixin para inyectar logica de negocio de Categorias en ViewSets."""

    def service_categoria_destroy(self, instance):
        """Elimina la categoria desvinculando items relacionados (set NULL)."""
        with transaction.atomic():
            Producto.objects.filter(empresa_id=instance.empresa_id, categoria=instance).update(categoria=None)
            Servicio.objects.filter(empresa_id=instance.empresa_id, categoria=instance).update(categoria=None)
            ActivoFijo.objects.filter(empresa_id=instance.empresa_id, categoria=instance).update(categoria=None)
            instance.delete()
        return True

    def service_categoria_get_resumen(self, instance):
        """Retorna conteo de items asociados a la categoria."""
        conteo_productos = Producto.objects.filter(
            empresa_id=instance.empresa_id, categoria=instance
        ).only('id').count()
        conteo_servicios = Servicio.objects.filter(
            empresa_id=instance.empresa_id, categoria=instance
        ).only('id').count()
        conteo_activos = ActivoFijo.objects.filter(
            empresa_id=instance.empresa_id, categoria=instance
        ).only('id').count()
        return {
            "id": instance.id,
            "nombre": instance.nombre,
            "activo": instance.activo,
            "conteo_productos": conteo_productos,
            "conteo_servicios": conteo_servicios,
            "conteo_activos": conteo_activos,
            "total_items": conteo_productos + conteo_servicios + conteo_activos,
        }

    def service_categoria_get_offcanvas_context(self, empresa, id_instancia=None):
        """Contexto para formulario de categoria (HTMX Offcanvas)."""
        categoria = None
        if id_instancia:
            categoria = CategoriaItemSelector.get_detail(empresa_id=empresa.id, categoria_uuid=id_instancia)
        return {
            'categoria': categoria,
            'empresa': empresa,
            'aplicaciones': CategoriaItem.Aplicacion.choices,
        }


class ProductoServiceMixin:
    """Mixin para inyectar logica de negocio de Productos en ViewSets."""

    def service_producto_destroy(self, instance):
        """Validacion de seguridad: no se eliminan productos activos."""
        if instance.activo:
            raise ValidationError(
                "No se puede eliminar un item activo. Cambielo a 'Inactivo' antes de borrar."
            )
        with transaction.atomic():
            instance.delete()
        return True

    def service_producto_ajustar_stock(self, producto_id, empresa_id, cantidad, observaciones):
        """Wrapper para ajustar stock desde el ViewSet."""
        return ajustar_stock(producto_id, empresa_id, cantidad, observaciones)

    def service_producto_get_stock(self, empresa, pk):
        """Retorna solo campos de stock (id, nombre, stock_actual)."""
        producto = (
            Producto.objects
            .filter(empresa=empresa, uuid=pk)
            .only('id', 'uuid', 'nombre', 'stock_actual')
            .first()
        )
        if not producto:
            from rest_framework.exceptions import NotFound
            raise NotFound('Producto no encontrado')
        return producto

    def service_producto_get_kardex(self, empresa, pk):
        """Obtiene producto y sus movimientos de Kardex optimizados."""
        producto = (
            Producto.objects
            .filter(empresa=empresa, uuid=pk)
            .only('id', 'uuid', 'codigo', 'nombre', 'stock_actual')
            .first()
        )
        if not producto:
            from rest_framework.exceptions import NotFound
            raise NotFound('Producto no encontrado')

        movimientos = MovimientoInventarioSelector.get_kardex_for_producto(empresa.id, producto.id)
        return producto, movimientos

    def service_producto_get_offcanvas_context(self, empresa, id_instancia=None, tipo_formulario='producto'):
        """Centraliza la carga de datos para formularios HTMX de productos."""
        producto = None
        if id_instancia:
            producto = ProductoSelector.get_detail(empresa_id=empresa.id, producto_uuid=id_instancia)

        categorias = (
            CategoriaItem.objects
            .filter(empresa_id=empresa.id, activo=True)
            .only('id', 'nombre', 'aplicacion')
            .order_by('nombre')[:100]
        )

        tipos_movimiento = []
        if tipo_formulario == 'ajuste':
            tipos_movimiento = MovimientoInventario.TipoMovimiento.choices

        return {
            'producto': producto,
            'categorias': categorias,
            'tipo_formulario': tipo_formulario,
            'empresa': empresa,
            'tipos_movimiento': tipos_movimiento,
        }


class ServicioServiceMixin:
    """Mixin para inyectar logica de negocio de Servicios en ViewSets."""

    def service_servicio_destroy(self, instance):
        """Validacion de seguridad: no se eliminan servicios activos."""
        if instance.activo:
            raise ValidationError(
                "No se puede eliminar un servicio activo. Cambielo a 'Inactivo' antes de borrar."
            )
        with transaction.atomic():
            instance.delete()
        return True

    def service_servicio_get_offcanvas_context(self, empresa, id_instancia=None):
        """Centraliza la carga de datos para formularios HTMX de servicios."""
        servicio = None
        if id_instancia:
            servicio = ServicioSelector.get_detail(empresa_id=empresa.id, servicio_uuid=id_instancia)

        categorias = (
            CategoriaItem.objects
            .filter(
                empresa_id=empresa.id,
                activo=True,
                aplicacion__in=[CategoriaItem.Aplicacion.SERVICIO, CategoriaItem.Aplicacion.TODO]
            )
            .only('id', 'nombre', 'aplicacion')
            .order_by('nombre')[:100]
        )
        return {
            'servicio': servicio,
            'categorias': categorias,
            'empresa': empresa,
        }

    def service_servicio_get_historial_context(self, empresa):
        """Contexto para el formulario de historial de servicio."""
        return {'empresa': empresa}


class ActivoFijoServiceMixin:
    """Mixin para inyectar logica de negocio de Activos Fijos en ViewSets."""

    def service_activo_destroy(self, instance):
        """Elimina el activo fijo."""
        instance.delete()
        return True

    def service_activo_list_all(self, empresa):
        """QuerySet optimizado para DataTables ajax directo."""
        return ActivoFijoSelector.get_list(empresa_id=empresa.id).order_by('nombre')

    def service_activo_get_offcanvas_context(self, empresa, id_instancia=None):
        """Contexto para formulario de activo fijo (HTMX Offcanvas)."""
        activo = None
        if id_instancia:
            activo = ActivoFijoSelector.get_detail(empresa_id=empresa.id, activo_uuid=id_instancia)

        categorias = (
            CategoriaItem.objects
            .filter(
                empresa_id=empresa.id,
                activo=True,
                aplicacion__in=[CategoriaItem.Aplicacion.ACTIVO, CategoriaItem.Aplicacion.TODO]
            )
            .only('id', 'nombre', 'aplicacion')
            .order_by('nombre')[:100]
        )
        return {
            'activo': activo,
            'categorias': categorias,
            'empresa': empresa,
        }


class MovimientoServiceMixin:
    """Mixin para logica de Movimientos de Inventario (Kardex)."""

    def service_movimiento_perform_create(self, serializer, empresa):
        """Guarda el movimiento y recalcula stock atomicamente (v3.8.1: soporta Activo Fijo)."""
        data = serializer.validated_data
        producto = data.get('producto')
        activo_fijo = data.get('activo_fijo')

        if producto:
            movimiento = KardexService.registrar_movimiento(
                empresa_id=empresa.id,
                producto_id=producto.id,
                tipo=data['tipo'],
                cantidad=data['cantidad'],
                costo_unitario=data.get('costo_unitario') or Decimal('0'),
                origen_referencia=data.get('origen_referencia'),
                cliente_referencia=data.get('cliente_referencia'),
                observaciones=data.get('observaciones'),
            )
        elif activo_fijo:
            movimiento = KardexService.registrar_movimiento_activo(
                empresa_id=empresa.id,
                activo_fijo_id=activo_fijo.id,
                tipo=data['tipo'],
                costo_unitario=data.get('costo_unitario') or Decimal('0'),
                origen_referencia=data.get('origen_referencia'),
                cliente_referencia=data.get('cliente_referencia'),
                observaciones=data.get('observaciones'),
            )
        else:
            raise ValidationError("Debe especificar un Producto o un Activo Fijo.")

        serializer.instance = movimiento
        return movimiento

    def service_movimiento_perform_update(self, instance, validated_data, empresa):
        """Actualiza movimiento delegando recalculo atomico a KardexService."""
        return KardexService.actualizar_movimiento(
            movimiento=instance,
            empresa_id=empresa.id,
            nueva_cantidad=validated_data.get('cantidad'),
            nuevo_tipo=validated_data.get('tipo'),
            nuevo_costo=validated_data.get('costo_unitario'),
            nuevo_origen=validated_data.get('origen_referencia'),
            nuevas_observaciones=validated_data.get('observaciones'),
        )

    def service_movimiento_perform_destroy(self, instance, empresa):
        """Elimina movimiento delegando recalculo atomico a KardexService."""
        KardexService.eliminar_movimiento(movimiento=instance, empresa_id=empresa.id)

    def service_movimiento_get_offcanvas_context(self, empresa, id_instancia=None):
        """Contexto para formulario de registro/edicion de movimiento (Kardex)."""
        movimiento = None
        if id_instancia:
            from apps.tenant.inventario.services.selectors import MovimientoInventarioSelector
            try:
                movimiento = MovimientoInventarioSelector.get_detail(
                    empresa_id=empresa.id,
                    movimiento_uuid=id_instancia
                )
            except MovimientoInventario.DoesNotExist:
                movimiento = None
        return {
            'movimiento': movimiento,
            'tipos': MovimientoInventario.TipoMovimiento.choices,
            'empresa': empresa,
        }


class HistorialServiceMixin:
    """Mixin para logica de Historial de Servicios."""

    def service_historial_get_queryset(self, empresa):
        """QuerySet optimizado con select_related y campos explicitos."""
        return (
            HistorialServicio.objects
            .select_related('servicio')
            .filter(empresa=empresa)
            .only(
                'id', 'uuid', 'fecha_registro', 'cantidad', 'valor_cobrado',
                'origen_referencia', 'cliente_referencia', 'observaciones',
                'servicio', 'servicio__uuid', 'servicio__codigo', 'servicio__nombre',
            )
            .order_by('-fecha_registro')
        )
