# apps/tenant/contabilidad/integracion/extractores/inventario.py
"""
Extractor for MovimientoInventario (F22).

Pull Model: Contabilidad reads from apps.tenant.inventario.models.MovimientoInventario.
Inventario never imports contabilidad, never calls Contabilizador. Ver
documentacion/F22_ACCOUNTING_CONTRACT.md para el contrato completo (matriz de
movimientos, reglas contables ya seedeadas, resolucion de tercero, documento
origen).

Alcance: solo movimientos con producto no nulo (Kardex de mercancia).
Movimientos de ActivoFijo, y TRASLADO_SALIDA/TRASLADO_ENTRADA (transferencia
interna entre sedes, sin impacto economico externo), quedan fuera de
extraccion deliberadamente.
"""
import logging
from datetime import date
from decimal import Decimal

from apps.tenant.contabilidad.models import AsientoContable
from apps.tenant.inventario.models import MovimientoInventario

from ..dtos import (
    DocumentoOrigen,
    LineaTransaccion,
    TerceroSnapshot,
    TipoTercero,
    TipoTransaccion,
    TransaccionEconomica,
)
from .base import AbstractExtractor, DocumentoEnriquecido, MovimientoResumen

logger = logging.getLogger(__name__)

_TM = MovimientoInventario.TipoMovimiento

# Mapeo tipo de movimiento -> tipo de transaccion contable (F22_ACCOUNTING_CONTRACT.md S1).
# Deliberadamente NO incluye TRASLADO_SALIDA/TRASLADO_ENTRADA (S5: sin impacto
# economico externo, nunca se extraen) ni los tipos de ActivoFijo (fuera de
# alcance F22, dominio distinto).
_TIPOS_CONTABILIZABLES = {
    _TM.ENTRADA_COMPRA: TipoTransaccion.COMPRA_INVENTARIO,
    _TM.SALIDA_VENTA: TipoTransaccion.SALIDA_INVENTARIO_VENTA,
    _TM.ENTRADA_AJUSTE: TipoTransaccion.AJUSTE_INVENTARIO,
    _TM.SALIDA_BAJA: TipoTransaccion.BAJA_INVENTARIO,
    _TM.SALIDA_CONSUMO: TipoTransaccion.BAJA_INVENTARIO,
    _TM.ENTRADA_DEVOLUCION: TipoTransaccion.AJUSTE_INVENTARIO,
}

# Lineas (concepto, lado) por tipo de movimiento. Los conceptos usan los
# nombres ya seedeados en seed_reglas_contables.py (F22_ACCOUNTING_CONTRACT.md
# S2) -- no se inventan conceptos nuevos.
_LINEAS_POR_TIPO = {
    _TM.ENTRADA_COMPRA: (
        ('INVENTARIO_PRODUCTO', 'DEBE'),
        ('PASIVO_COMPRA_INVENTARIO', 'HABER'),
    ),
    _TM.SALIDA_VENTA: (
        ('COSTO_VENTA_PRODUCTO', 'DEBE'),
        ('INVENTARIO_PRODUCTO', 'HABER'),
    ),
    _TM.ENTRADA_AJUSTE: (
        ('INVENTARIO_PRODUCTO', 'DEBE'),
        ('INGRESO_AJUSTE_INVENTARIO', 'HABER'),
    ),
    _TM.SALIDA_BAJA: (
        ('GASTO_DETERIORO_INVENTARIO', 'DEBE'),
        ('INVENTARIO_PRODUCTO', 'HABER'),
    ),
    _TM.SALIDA_CONSUMO: (
        ('GASTO_CONSUMO_INTERNO', 'DEBE'),
        ('INVENTARIO_PRODUCTO', 'HABER'),
    ),
    _TM.ENTRADA_DEVOLUCION: (
        ('INVENTARIO_PRODUCTO', 'DEBE'),
        ('COSTO_VENTA_DEVOLUCION', 'HABER'),
    ),
}


class ExtractorInventario(AbstractExtractor):
    """
    Extractor for MovimientoInventario records (F22).

    Solo extrae movimientos de Producto (no ActivoFijo) cuyo tipo este en
    _TIPOS_CONTABILIZABLES. No resuelve cuentas, no persiste AsientoContable,
    no llama Contabilizador directamente (eso lo hace
    AbstractExtractor.contabilizar_pendientes(), heredado sin cambios).
    """

    def extraer_pendientes(self) -> list[TransaccionEconomica]:
        """
        Extrae MovimientoInventario no contabilizados aun, limitados a
        empresa_id (Zero Trust) y a los tipos contabilizables reales.
        """
        ya_contabilizados = set(
            AsientoContable.objects.filter(
                empresa_id=self.empresa_id,
                documento_origen_app='inventario',
                documento_origen_modelo='MovimientoInventario',
                documento_origen_reversado=False,
            ).values_list('documento_origen_id', flat=True)
        )

        movimientos = (
            MovimientoInventario.objects.filter(
                empresa_id=self.empresa_id,
                producto__isnull=False,
                tipo__in=_TIPOS_CONTABILIZABLES.keys(),
            )
            .exclude(id__in=ya_contabilizados)
            .select_related('producto')
            .only(
                'id', 'empresa_id', 'tipo', 'cantidad', 'costo_unitario', 'created_at',
                'documento_origen_id', 'documento_origen_app', 'documento_origen_modelo',
                'origen_referencia', 'cliente_referencia',
                'producto_id', 'producto__nombre', 'producto__codigo',
            )
            .order_by('created_at', 'id')
        )

        return [self._mapear_a_dto(mov) for mov in movimientos]

    def _mapear_a_dto(self, mov: MovimientoInventario) -> TransaccionEconomica:
        tipo_transaccion = _TIPOS_CONTABILIZABLES[mov.tipo]
        monto = (mov.cantidad * mov.costo_unitario).quantize(Decimal('0.01'))
        lineas = [
            LineaTransaccion(concepto=concepto, monto=monto, lado=lado)
            for concepto, lado in _LINEAS_POR_TIPO[mov.tipo]
        ]

        return TransaccionEconomica(
            tipo=tipo_transaccion,
            fecha=mov.created_at.date(),
            descripcion=(
                f"Movimiento de inventario {mov.get_tipo_display()} - "
                f"{mov.producto.codigo if mov.producto else 'N/A'}"
            ),
            tercero=self._resolver_tercero(mov),
            lineas=lineas,
            documento_origen=DocumentoOrigen(
                app_label='inventario',
                modelo='MovimientoInventario',
                id=mov.id,
                numero=f"MOV-{mov.id}",
            ),
            observaciones=mov.origen_referencia or '',
        )

    def _resolver_tercero(self, mov: MovimientoInventario) -> TerceroSnapshot:
        """
        Resuelve el tercero real cuando es posible (proveedor de una compra,
        via la misma soft-reference que F21 ya usa para idempotencia de
        Inventario). Fuera de ese caso no hay FK estructurada a un tercero en
        MovimientoInventario (solo texto libre) -- se usa un tercero generico
        en vez de bloquear la contabilizacion o inventar un NIT.
        Ver F22_ACCOUNTING_CONTRACT.md S3.
        """
        if mov.tipo == _TM.ENTRADA_COMPRA and mov.documento_origen_id:
            proveedor = self._resolver_proveedor_compra(mov)
            if proveedor is not None:
                return TerceroSnapshot(
                    tipo=TipoTercero.PROVEEDOR,
                    id_origen=proveedor.id,
                    nit=proveedor.numero_documento,
                    razon_social=proveedor.razon_social,
                )

        referencia = mov.cliente_referencia or mov.origen_referencia or 'N/A'
        return TerceroSnapshot(
            tipo=TipoTercero.OTRO,
            id_origen=mov.producto_id or 0,
            nit='',
            razon_social=f"Movimiento de inventario: {referencia}",
        )

    def _resolver_proveedor_compra(self, mov: MovimientoInventario):
        """
        Bridge de lectura contabilidad -> compras (mismo patron ya
        establecido: ExtractorGastos lee gastos.models, ExtractorNomina lee
        empleados.models -- Contabilidad puede leer de cualquier app fuente
        en el modelo Pull). Import local para no acoplar a nivel de modulo.
        """
        if mov.documento_origen_modelo != 'RecepcionCompraItem':
            return None
        from apps.tenant.compras.models import RecepcionCompraItem

        item = (
            RecepcionCompraItem.objects
            .filter(id=mov.documento_origen_id, empresa_id=mov.empresa_id)
            .select_related('recepcion__orden_compra__proveedor')
            .first()
        )
        if item is None:
            return None
        return item.recepcion.orden_compra.proveedor

    def get_documentos_enriquecidos(
        self, empresa_id: int, fecha_inicio: date, fecha_fin: date
    ) -> list[DocumentoEnriquecido]:
        movimientos = (
            MovimientoInventario.objects.filter(
                empresa_id=empresa_id,
                producto__isnull=False,
                tipo__in=_TIPOS_CONTABILIZABLES.keys(),
                created_at__date__range=(fecha_inicio, fecha_fin),
            )
            .select_related('producto')
            .order_by('created_at', 'id')
        )
        ids = [m.id for m in movimientos]

        asientos = {
            a.documento_origen_id: a
            for a in AsientoContable.objects.filter(
                empresa_id=empresa_id,
                documento_origen_app='inventario',
                documento_origen_modelo='MovimientoInventario',
                documento_origen_id__in=ids,
            ).prefetch_related('movimientos', 'movimientos__cuenta')
        }

        res = []
        for mov in movimientos:
            asiento = asientos.get(mov.id)
            monto = (mov.cantidad * mov.costo_unitario).quantize(Decimal('0.01'))

            dto = DocumentoEnriquecido(
                app_label='inventario',
                app_display='Inventario',
                modelo='MovimientoInventario',
                documento_id=mov.id,
                numero=f"MOV-{mov.id}",
                fecha=mov.created_at.date(),
                tipo_comprobante='CC',
                tipo_comprobante_display='Comprobante de Contabilidad',
                tercero_nit='',
                tercero_nombre=mov.producto.nombre if mov.producto else '',
                subtotal=monto,
                impuestos=Decimal('0'),
                total=monto,
                cuentas_asignadas=[],
            )

            if asiento:
                dto.estado_contable = 'CONTABILIZADO'
                dto.asiento_uuid = str(asiento.uuid)
                dto.asiento_numero = asiento.numero
                dto.movimientos = [
                    MovimientoResumen(
                        cuenta_codigo=m.cuenta_codigo or (m.cuenta.codigo if m.cuenta else 'SIN_CUENTA'),
                        cuenta_nombre=(m.cuenta.nombre if m.cuenta else (m.descripcion or '')),
                        debe=m.debe,
                        haber=m.haber,
                    )
                    for m in asiento.movimientos.all()
                ]
                # debe_total/haber_total son los campos que Contabilizador
                # realmente puebla (ver contabilizador.py:_construir_asiento) --
                # no total_debe/total_haber (legado, no poblados por este flujo).
                dto.cuadra = (asiento.debe_total == asiento.haber_total)

            res.append(dto)

        return res
