# apps/tenant/contabilidad/integracion/extractores/facturas.py
from typing import List
from decimal import Decimal
import logging

from apps.tenant.facturas.models import Factura, NotaCredito
from .base import AbstractExtractor
from ..dtos import (
    TransaccionEconomica,
    TipoTransaccion,
    TerceroSnapshot,
    TipoTercero,
    LineaTransaccion,
    DocumentoOrigen,
    ImpuestoLinea
)

logger = logging.getLogger(__name__)

class ExtractorFacturas(AbstractExtractor):
    """
    Extractor especializado para Facturas Electrónicas y Notas de Crédito.
    
    # WARNING: ARQUITECTURA PULL: Este extractor extrae tanto VENTAS (emitidas) 
    como COMPRAS (recibidas por el pipeline de facturas).
    # WARNING: ZERO WASTE: Solo extrae registros ACEPTADOS y no contabilizados.
    """

    def extraer_pendientes(self) -> List[TransaccionEconomica]:
        """
        Extrae facturas y notas crédito pendientes de contabilizar.
        """
        from apps.tenant.contabilidad.models import AsientoContable

        facturas_contabilizadas = set(
            AsientoContable.objects.filter(
                empresa_id=self.empresa_id,
                documento_origen_app='facturas',
                documento_origen_modelo='Factura',
                documento_origen_reversado=False,
            ).values_list('documento_origen_id', flat=True)
        )
        notas_contabilizadas = set(
            AsientoContable.objects.filter(
                empresa_id=self.empresa_id,
                documento_origen_app='facturas',
                documento_origen_modelo='NotaCredito',
                documento_origen_reversado=False,
            ).values_list('documento_origen_id', flat=True)
        )

        facturas = Factura.objects.filter(
            empresa_id=self.empresa_id,
            estado='ACEPTADA',
            tipo='FE',
        ).exclude(
            id__in=facturas_contabilizadas,
        ).only(
            'id', 'numero', 'fecha_emision', 'naturaleza',
            'subtotal', 'impuestos', 'total', 'retefuente', 'reteica', 'reteiva',
            'emisor_nit', 'emisor_razon_social',
            'receptor_nit', 'receptor_razon_social',
        )

        notas = NotaCredito.objects.filter(
            empresa_id=self.empresa_id,
            factura__estado='ACEPTADA',
        ).exclude(
            id__in=notas_contabilizadas,
        ).select_related('factura').only(
            'id', 'numero', 'fecha_emision',
            'subtotal', 'impuestos', 'total', 'retefuente', 'reteica', 'reteiva',
            'factura__naturaleza', 'factura__numero',
            'factura__emisor_nit', 'factura__emisor_razon_social',
            'factura__receptor_nit', 'factura__receptor_razon_social',
        )

        dtos = [self._mapear_factura_a_dto(f) for f in facturas]
        dtos += [self._mapear_nota_a_dto(n) for n in notas]
        return dtos

    def _mapear_factura_a_dto(self, fact: Factura) -> TransaccionEconomica:
        """
        Mapea una Factura (Venta o Compra) al DTO unificado.
        """
        es_venta = fact.naturaleza == 'VENTA'
        
        # En VENTAS, el tercero es el Receptor (Cliente).
        # En COMPRAS, el tercero es el Emisor (Proveedor).
        tercero = TerceroSnapshot(
            tipo=TipoTercero.CLIENTE if es_venta else TipoTercero.PROVEEDOR,
            id_origen=0, # No tenemos vínculo a tabla maestros aquí
            nit=fact.receptor_nit if es_venta else fact.emisor_nit,
            razon_social=fact.receptor_razon_social if es_venta else fact.emisor_razon_social
        )

        lineas = []
        
        retefuente = fact.retefuente or Decimal('0')
        reteica = fact.reteica or Decimal('0')
        reteiva = fact.reteiva or Decimal('0')

        if es_venta:
            lineas.append(LineaTransaccion(concepto="INGRESO_PRINCIPAL", monto=fact.subtotal, lado='HABER'))
            if fact.impuestos > 0:
                lineas.append(LineaTransaccion(concepto="IVA_GENERADO", monto=fact.impuestos, lado='HABER'))
            if retefuente > 0:
                lineas.append(LineaTransaccion(concepto="RETEFUENTE", monto=retefuente, lado='DEBE'))
            if reteica > 0:
                lineas.append(LineaTransaccion(concepto="RETEICA", monto=reteica, lado='DEBE'))
            if reteiva > 0:
                lineas.append(LineaTransaccion(concepto="RETEIVA", monto=reteiva, lado='DEBE'))
            neto = fact.total - retefuente - reteica - reteiva
            lineas.append(LineaTransaccion(concepto="CXC_CLIENTES", monto=neto, lado='DEBE'))
            tipo_tx = TipoTransaccion.VENTA_FACTURA
        else:
            lineas.append(LineaTransaccion(concepto="GASTO_GENERAL", monto=fact.subtotal, lado='DEBE'))
            if fact.impuestos > 0:
                lineas.append(LineaTransaccion(concepto="IVA_DESCONTABLE", monto=fact.impuestos, lado='DEBE'))
            if retefuente > 0:
                lineas.append(LineaTransaccion(concepto="RETEFUENTE", monto=retefuente, lado='HABER'))
            if reteica > 0:
                lineas.append(LineaTransaccion(concepto="RETEICA", monto=reteica, lado='HABER'))
            if reteiva > 0:
                lineas.append(LineaTransaccion(concepto="RETEIVA", monto=reteiva, lado='HABER'))
            neto = fact.total - retefuente - reteica - reteiva
            lineas.append(LineaTransaccion(concepto="PASIVO_COMPRA_GASTO", monto=neto, lado='HABER'))
            tipo_tx = TipoTransaccion.COMPRA_GASTO

        return TransaccionEconomica(
            tipo=tipo_tx,
            fecha=fact.fecha_emision.date(),
            descripcion=f"{'Factura Venta' if es_venta else 'Compra Electrónica'} {fact.numero}",
            tercero=tercero,
            lineas=lineas,
            documento_origen=DocumentoOrigen(
                app_label='facturas',
                modelo='Factura',
                id=fact.id,
                numero=fact.numero
            )
        )

    def _mapear_nota_a_dto(self, nota: NotaCredito) -> TransaccionEconomica:
        """
        Mapea una Nota Crédito (Reversión) al DTO unificado.
        """
        es_venta = nota.factura.naturaleza == 'VENTA'
        
        tercero = TerceroSnapshot(
            tipo=TipoTercero.CLIENTE if es_venta else TipoTercero.PROVEEDOR,
            id_origen=0,
            nit=nota.factura.receptor_nit if es_venta else nota.factura.emisor_nit,
            razon_social=nota.factura.receptor_razon_social if es_venta else nota.factura.emisor_razon_social
        )

        retefuente = nota.retefuente or Decimal('0')
        reteica = nota.reteica or Decimal('0')
        reteiva = nota.reteiva or Decimal('0')
        lineas = []

        if es_venta:
            lineas.append(LineaTransaccion(concepto="DEVOLUCION_VENTA", monto=nota.subtotal, lado='DEBE'))
            if nota.impuestos > 0:
                lineas.append(LineaTransaccion(concepto="IVA_GENERADO", monto=nota.impuestos, lado='DEBE'))
            if retefuente > 0:
                lineas.append(LineaTransaccion(concepto="RETEFUENTE", monto=retefuente, lado='HABER'))
            if reteica > 0:
                lineas.append(LineaTransaccion(concepto="RETEICA", monto=reteica, lado='HABER'))
            if reteiva > 0:
                lineas.append(LineaTransaccion(concepto="RETEIVA", monto=reteiva, lado='HABER'))
            neto = nota.total - retefuente - reteica - reteiva
            lineas.append(LineaTransaccion(concepto="CXC_CLIENTES", monto=neto, lado='HABER'))
            tipo_tx = TipoTransaccion.VENTA_NOTA_CREDITO
        else:
            lineas.append(LineaTransaccion(concepto="DEVOLUCION_COMPRA", monto=nota.subtotal, lado='HABER'))
            if nota.impuestos > 0:
                lineas.append(LineaTransaccion(concepto="IVA_DESCONTABLE", monto=nota.impuestos, lado='HABER'))
            if retefuente > 0:
                lineas.append(LineaTransaccion(concepto="RETEFUENTE", monto=retefuente, lado='DEBE'))
            if reteica > 0:
                lineas.append(LineaTransaccion(concepto="RETEICA", monto=reteica, lado='DEBE'))
            if reteiva > 0:
                lineas.append(LineaTransaccion(concepto="RETEIVA", monto=reteiva, lado='DEBE'))
            neto = nota.total - retefuente - reteica - reteiva
            lineas.append(LineaTransaccion(concepto="PASIVO_COMPRA_GASTO", monto=neto, lado='DEBE'))
            tipo_tx = TipoTransaccion.COMPRA_NOTA_CREDITO 

        return TransaccionEconomica(
            tipo=tipo_tx,
            fecha=nota.fecha_emision.date(),
            descripcion=f"Nota Crédito {nota.numero} (Ref: {nota.factura.numero})",
            tercero=tercero,
            lineas=lineas,
            documento_origen=DocumentoOrigen(
                app_label='facturas',
                modelo='NotaCredito',
                id=nota.id,
                numero=nota.numero
            )
        )
