# apps/tenant/contabilidad/integracion/extractores/inventario.py
from typing import List
from decimal import Decimal
import logging

from apps.tenant.inventario.models import MovimientoInventario
from .base import AbstractExtractor
from ..dtos import (
    TransaccionEconomica,
    TipoTransaccion,
    TerceroSnapshot,
    TipoTercero,
    LineaTransaccion,
    DocumentoOrigen
)

logger = logging.getLogger(__name__)

class ExtractorInventario(AbstractExtractor):
    """
    Extractor especializado para Movimientos de Inventario (Kardex).
    
    # WARNING: ARQUITECTURA PULL: Extrae movimientos que afectan el costo de ventas.
    # WARNING: ZERO WASTE: Solo extrae movimientos no contabilizados.
    """

    def extraer_pendientes(self) -> List[TransaccionEconomica]:
        """
        Extrae movimientos de inventario pendientes de contabilizar.
        Enfocado en Salidas por Venta (Costo de Ventas) y Ajustes.
        """
        from apps.tenant.contabilidad.models import AsientoContable

        mov_contabilizados = set(
            AsientoContable.objects.filter(
                empresa_id=self.empresa_id,
                documento_origen_app='inventario',
                documento_origen_modelo='MovimientoInventario',
                documento_origen_reversado=False,
            ).values_list('documento_origen_id', flat=True)
        )

        # Tipos que generan asiento contable directo desde el Kardex
        tipos_contabilizables = [
            MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
            MovimientoInventario.TipoMovimiento.SALIDA_BAJA,
            MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
        ]

        registros = MovimientoInventario.objects.filter(
            empresa_id=self.empresa_id,
            tipo__in=tipos_contabilizables,
        ).exclude(
            id__in=mov_contabilizados,
        ).select_related('producto').only(
            'id', 'tipo', 'cantidad', 'costo_unitario', 'created_at',
            'producto__nombre', 'producto__codigo', 'origen_referencia'
        )

        return [self._mapear_a_dto(r) for r in registros]

    def _mapear_a_dto(self, mov: MovimientoInventario) -> TransaccionEconomica:
        """
        Mapea un movimiento de inventario al DTO unificado.
        """
        # Para inventario, el tercero es opcional o es la propia empresa
        tercero = TerceroSnapshot(
            tipo=TipoTercero.OTRO,
            id_origen=0,
            nit="VARIOS",
            razon_social="MOVIMIENTO INTERNO INVENTARIO"
        )

        lineas = []
        valor_total = (mov.cantidad * mov.costo_unitario).quantize(Decimal('0.01'))
        
        if mov.tipo == MovimientoInventario.TipoMovimiento.SALIDA_VENTA:
            # Debito al Costo, Crédito al Activo
            lineas.append(LineaTransaccion(concepto="COSTO_VENTAS", monto=valor_total, lado='DEBE'))
            lineas.append(LineaTransaccion(concepto="INVENTARIO_MERCANCIAS", monto=valor_total, lado='HABER'))
            tipo_tx = TipoTransaccion.INVENTARIO_COSTO_VENTA
        elif mov.tipo == MovimientoInventario.TipoMovimiento.SALIDA_BAJA:
            # Debito al Gasto (Ajuste/Baja), Crédito al Activo
            lineas.append(LineaTransaccion(concepto="GASTO_BAJA_INVENTARIO", monto=valor_total, lado='DEBE'))
            lineas.append(LineaTransaccion(concepto="INVENTARIO_MERCANCIAS", monto=valor_total, lado='HABER'))
            tipo_tx = TipoTransaccion.AJUSTE_INVENTARIO
        else: # ENTRADA_AJUSTE
            # Debito al Activo, Crédito al Ingreso/Ajuste
            lineas.append(LineaTransaccion(concepto="INVENTARIO_MERCANCIAS", monto=valor_total, lado='DEBE'))
            lineas.append(LineaTransaccion(concepto="AJUSTE_INVENTARIO_INGRESO", monto=valor_total, lado='HABER'))
            tipo_tx = TipoTransaccion.AJUSTE_INVENTARIO

        return TransaccionEconomica(
            tipo=tipo_tx,
            fecha=mov.created_at.date(),
            descripcion=f"{mov.get_tipo_display()} - {mov.producto.nombre}",
            tercero=tercero,
            lineas=lineas,
            documento_origen=DocumentoOrigen(
                app_label='inventario',
                modelo='MovimientoInventario',
                id=mov.id,
                numero=mov.origen_referencia or f"MOV-{mov.id}"
            )
        )
