"""
business_service.py - Inventario v3.5

Capa de logica de negocio (Business Logic Layer) para el modulo de Inventario.
Contiene: calculos de stock, validaciones semanticas, movimientos de Kardex
e ingesta masiva de datos.

[ARQ-C2] Los Service Mixins para ViewSets viven en services/api_mixins.py
(no en este archivo), igual que en el resto de apps tenant.

Reglas:
- Toda mutacion de stock usa @transaction.atomic.
- Toda validacion de pertenencia al tenant pasa por selectors.py (Zero Trust).
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

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
    # F21: traslado entre sedes. Deliberadamente FUERA de TIPOS_ENTRADA/TIPOS_SALIDA:
    # el stock_actual (agregado por empresa) no debe cambiar por un traslado interno,
    # solo la distribucion por sede cambia. Ver StockPorSedeSelector.
    TIPOS_TRASLADO = (
        MovimientoInventario.TipoMovimiento.TRASLADO_SALIDA,
        MovimientoInventario.TipoMovimiento.TRASLADO_ENTRADA,
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
        sede_id: int = None,
        documento_origen_app: str = None,
        documento_origen_modelo: str = None,
        documento_origen_id: int = None,
    ) -> MovimientoInventario:
        """
        Registra un movimiento append-only y actualiza stock en la misma transaccion.

        Idempotencia (F21, mismo patron que AsientoContable/Contabilizador): si se
        pasa documento_origen_app/modelo/id, un segundo llamado con la misma tripleta
        + tipo devuelve el movimiento ya existente en vez de duplicarlo. Doble defensa:
        chequeo previo (rapido, cubre el caso normal de reintento) + UniqueConstraint
        de BD como respaldo ante condicion de carrera concurrente real.
        """
        cantidad = Decimal(str(cantidad or "0"))
        if cantidad <= 0:
            raise ValidationError("La cantidad del movimiento debe ser positiva.")

        if documento_origen_id is not None:
            existente = MovimientoInventario.objects.filter(
                empresa_id=empresa_id,
                documento_origen_app=documento_origen_app,
                documento_origen_modelo=documento_origen_modelo,
                documento_origen_id=documento_origen_id,
                tipo=tipo,
            ).first()
            if existente is not None:
                return existente

        producto = (
            Producto.objects
            .select_for_update()
            .only('id', 'empresa_id', 'stock_actual')
            .filter(pk=producto_id, empresa_id=empresa_id, activo=True)
            .first()
        )
        if not producto:
            raise ValidationError("El producto no existe, esta inactivo o no pertenece a este tenant.")

        tipos_validos = KardexService.TIPOS_ENTRADA + KardexService.TIPOS_SALIDA + KardexService.TIPOS_TRASLADO
        if tipo not in tipos_validos:
            raise ValidationError(f"Tipo de movimiento invalido: {tipo}")

        # Traslado: la suficiencia de stock se valida por sede en el llamador
        # (StockPorSedeSelector), no aqui — stock_actual es agregado por empresa.
        if tipo in KardexService.TIPOS_SALIDA and producto.stock_actual < cantidad:
            raise ValidationError(
                f"Stock insuficiente. Disponible: {producto.stock_actual}, Solicitado: {cantidad}"
            )

        try:
            with transaction.atomic():
                movimiento = MovimientoInventario.objects.create(
                    empresa_id=empresa_id,
                    producto=producto,
                    tipo=tipo,
                    cantidad=cantidad,
                    costo_unitario=Decimal(str(costo_unitario or "0")),
                    origen_referencia=origen_referencia,
                    cliente_referencia=cliente_referencia,
                    observaciones=observaciones,
                    sede_id=sede_id,
                    documento_origen_app=documento_origen_app,
                    documento_origen_modelo=documento_origen_modelo,
                    documento_origen_id=documento_origen_id,
                )
        except IntegrityError as exc:
            if 'uniq_movimiento_documento_origen_tipo' in str(exc):
                return MovimientoInventario.objects.get(
                    empresa_id=empresa_id,
                    documento_origen_app=documento_origen_app,
                    documento_origen_modelo=documento_origen_modelo,
                    documento_origen_id=documento_origen_id,
                    tipo=tipo,
                )
            raise

        if tipo in KardexService.TIPOS_ENTRADA or tipo in KardexService.TIPOS_SALIDA:
            KardexService.recalcular_stock_producto(producto.id, empresa_id)
        return movimiento

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


class TrasladoInventarioService:
    """
    Orquesta el flujo de traslado de stock entre sedes (F21):
    SOLICITADO -> APROBADO -> EN_TRANSITO -> RECIBIDO (o CANCELADO en
    cualquier punto anterior a EN_TRANSITO).

    No modifica MovimientoInventario.sede directamente: genera movimientos
    append-only reales (TRASLADO_SALIDA al enviar, TRASLADO_ENTRADA al
    recibir) via KardexService.registrar_movimiento(), con
    documento_origen_modelo='TrasladoInventario' para idempotencia — mismo
    patron que RecepcionCompraBusinessService (apps/tenant/compras).
    """

    @staticmethod
    @transaction.atomic
    def solicitar(
        *,
        empresa_id: int,
        producto_id: int,
        cantidad: Decimal,
        sede_origen_id: int,
        sede_destino_id: int,
        usuario_id: int,
        area_origen_id: int = None,
        area_destino_id: int = None,
        motivo: str = '',
    ):
        """Crea el TrasladoInventario en estado SOLICITADO. Sin efecto en stock todavia."""
        if sede_origen_id == sede_destino_id:
            raise ValidationError("La sede de origen y la sede de destino no pueden ser la misma.")

        cantidad = Decimal(str(cantidad or "0"))
        if cantidad <= 0:
            raise ValidationError("La cantidad a trasladar debe ser positiva.")

        producto = (
            Producto.objects
            .filter(pk=producto_id, empresa_id=empresa_id, activo=True)
            .only('id')
            .first()
        )
        if not producto:
            raise ValidationError("El producto no existe, esta inactivo o no pertenece a este tenant.")

        from apps.tenant.empresa.models import Sede
        sede_origen = Sede.objects.filter(pk=sede_origen_id, empresa_id=empresa_id).only('id').first()
        sede_destino = Sede.objects.filter(pk=sede_destino_id, empresa_id=empresa_id).only('id').first()
        if not sede_origen or not sede_destino:
            raise ValidationError("La sede de origen o de destino no pertenece a esta empresa.")

        from apps.tenant.inventario.models import TrasladoInventario
        traslado = TrasladoInventario.objects.create(
            empresa_id=empresa_id,
            producto=producto,
            cantidad=cantidad,
            sede_origen=sede_origen,
            sede_destino=sede_destino,
            area_origen_id=area_origen_id,
            area_destino_id=area_destino_id,
            estado=TrasladoInventario.Estado.SOLICITADO,
            motivo=motivo,
            usuario_solicita_id=usuario_id,
            fecha_solicitud=timezone.now(),
        )
        return traslado

    @staticmethod
    @transaction.atomic
    def aprobar(*, traslado_uuid: str, empresa_id: int, usuario_id: int):
        from apps.tenant.inventario.models import TrasladoInventario
        traslado = (
            TrasladoInventario.objects.select_for_update()
            .filter(uuid=traslado_uuid, empresa_id=empresa_id)
            .first()
        )
        if not traslado:
            raise ValidationError("El traslado no existe o no pertenece a esta empresa.")
        if traslado.estado != TrasladoInventario.Estado.SOLICITADO:
            raise ValidationError(
                f"Solo se puede aprobar un traslado en estado SOLICITADO (actual: {traslado.estado})."
            )
        traslado.estado = TrasladoInventario.Estado.APROBADO
        traslado.usuario_aprueba_id = usuario_id
        traslado.fecha_aprobacion = timezone.now()
        traslado.save(update_fields=['estado', 'usuario_aprueba', 'fecha_aprobacion'])
        return traslado

    @staticmethod
    @transaction.atomic
    def enviar(*, traslado_uuid: str, empresa_id: int):
        """
        Transiciona a EN_TRANSITO y genera TRASLADO_SALIDA (decrementa el
        stock de la sede origen). Idempotente: reintentar sobre un traslado
        ya EN_TRANSITO es un no-op exitoso.
        """
        from apps.tenant.inventario.models import MovimientoInventario, TrasladoInventario
        from apps.tenant.inventario.services.selectors import StockPorSedeSelector

        traslado = (
            TrasladoInventario.objects.select_for_update()
            .filter(uuid=traslado_uuid, empresa_id=empresa_id)
            .first()
        )
        if not traslado:
            raise ValidationError("El traslado no existe o no pertenece a esta empresa.")
        if traslado.estado == TrasladoInventario.Estado.EN_TRANSITO:
            return traslado
        if traslado.estado != TrasladoInventario.Estado.APROBADO:
            raise ValidationError(
                f"Solo se puede enviar un traslado APROBADO (actual: {traslado.estado})."
            )

        stock_origen = StockPorSedeSelector.calcular_stock_sede(
            empresa_id, traslado.producto_id, traslado.sede_origen_id
        )
        if stock_origen < traslado.cantidad:
            raise ValidationError(
                f"Stock insuficiente en la sede de origen. Disponible: {stock_origen}, "
                f"solicitado: {traslado.cantidad}."
            )

        KardexService.registrar_movimiento(
            empresa_id=empresa_id,
            producto_id=traslado.producto_id,
            tipo=MovimientoInventario.TipoMovimiento.TRASLADO_SALIDA,
            cantidad=traslado.cantidad,
            sede_id=traslado.sede_origen_id,
            origen_referencia=f"Traslado #{traslado.id} -> sede {traslado.sede_destino_id}",
            documento_origen_app='inventario',
            documento_origen_modelo='TrasladoInventario',
            documento_origen_id=traslado.id,
        )
        traslado.estado = TrasladoInventario.Estado.EN_TRANSITO
        traslado.fecha_envio = timezone.now()
        traslado.save(update_fields=['estado', 'fecha_envio'])
        return traslado

    @staticmethod
    @transaction.atomic
    def recibir(*, traslado_uuid: str, empresa_id: int, usuario_id: int):
        """
        Transiciona a RECIBIDO y genera TRASLADO_ENTRADA (incrementa el
        stock de la sede destino). Idempotente igual que enviar().
        """
        from apps.tenant.inventario.models import MovimientoInventario, TrasladoInventario

        traslado = (
            TrasladoInventario.objects.select_for_update()
            .filter(uuid=traslado_uuid, empresa_id=empresa_id)
            .first()
        )
        if not traslado:
            raise ValidationError("El traslado no existe o no pertenece a esta empresa.")
        if traslado.estado == TrasladoInventario.Estado.RECIBIDO:
            return traslado
        if traslado.estado != TrasladoInventario.Estado.EN_TRANSITO:
            raise ValidationError(
                f"Solo se puede recibir un traslado EN_TRANSITO (actual: {traslado.estado})."
            )

        KardexService.registrar_movimiento(
            empresa_id=empresa_id,
            producto_id=traslado.producto_id,
            tipo=MovimientoInventario.TipoMovimiento.TRASLADO_ENTRADA,
            cantidad=traslado.cantidad,
            sede_id=traslado.sede_destino_id,
            origen_referencia=f"Traslado #{traslado.id} <- sede {traslado.sede_origen_id}",
            documento_origen_app='inventario',
            documento_origen_modelo='TrasladoInventario',
            documento_origen_id=traslado.id,
        )
        traslado.estado = TrasladoInventario.Estado.RECIBIDO
        traslado.usuario_recibe_id = usuario_id
        traslado.fecha_recepcion = timezone.now()
        traslado.save(update_fields=['estado', 'usuario_recibe', 'fecha_recepcion'])
        return traslado

    @staticmethod
    @transaction.atomic
    def cancelar(*, traslado_uuid: str, empresa_id: int):
        """
        Cancela un traslado. Solo permitido antes de EN_TRANSITO: una vez en
        transito el stock ya salio de la sede origen (movimiento append-only
        real) — cancelarlo requeriria una reversion explicita, deliberadamente
        fuera de alcance de F21 (mismo limite que RecepcionCompra tras
        CONFIRMADA).
        """
        from apps.tenant.inventario.models import TrasladoInventario

        traslado = (
            TrasladoInventario.objects.select_for_update()
            .filter(uuid=traslado_uuid, empresa_id=empresa_id)
            .first()
        )
        if not traslado:
            raise ValidationError("El traslado no existe o no pertenece a esta empresa.")
        if traslado.estado in (TrasladoInventario.Estado.EN_TRANSITO, TrasladoInventario.Estado.RECIBIDO):
            raise ValidationError(f"No se puede cancelar un traslado en estado {traslado.estado}.")
        traslado.estado = TrasladoInventario.Estado.CANCELADO
        traslado.save(update_fields=['estado'])
        return traslado




