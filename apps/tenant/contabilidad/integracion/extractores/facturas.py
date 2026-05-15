# apps/tenant/contabilidad/integracion/extractores/facturas.py
from typing import Dict, List, Optional
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
)

logger = logging.getLogger(__name__)


class ExtractorFacturas(AbstractExtractor):
    """
    Extractor para Facturas Electronicas y Notas de Credito.

    Arquitectura Pull: extrae VENTAS (emitidas) y COMPRAS (recibidas).
    Zero Waste: solo extrae registros ACEPTADOS y no contabilizados.
    v3.7.1: usa cuenta_contable_uuid de Factura/Cliente/Proveedor como cuenta_hint.
    Retenciones: leidas desde Contabilidad.Retencion via @property Pull Model.
    """

    def extraer_pendientes(self) -> List[TransaccionEconomica]:
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

        facturas = list(Factura.objects.filter(
            empresa_id=self.empresa_id,
            estado='ACEPTADA',
            tipo='FE',
        ).exclude(
            id__in=facturas_contabilizadas,
        ).only(
            'id', 'numero', 'fecha_emision', 'naturaleza',
            'subtotal', 'impuestos', 'total', 'cuenta_contable_uuid',
            'emisor_nit', 'emisor_razon_social',
            'receptor_nit', 'receptor_razon_social',
        ))

        # Batch-load account UUIDs from Cliente/Proveedor (evita N+1 queries)
        venta_nits = {f.receptor_nit for f in facturas if f.naturaleza == 'VENTA'}
        compra_nits = {f.emisor_nit for f in facturas if f.naturaleza != 'VENTA'}
        cliente_cuentas = self._cargar_cuentas_terceros('clientes', 'Cliente', venta_nits)
        proveedor_cuentas = self._cargar_cuentas_terceros('proveedores', 'Proveedor', compra_nits)

        notas = list(NotaCredito.objects.filter(
            empresa_id=self.empresa_id,
            factura__estado='ACEPTADA',
        ).exclude(
            id__in=notas_contabilizadas,
        ).select_related('factura').only(
            'id', 'numero', 'fecha_emision',
            'subtotal', 'impuestos', 'total',
            'retefuente', 'reteica', 'reteiva',
            'factura__naturaleza', 'factura__numero',
            'factura__emisor_nit', 'factura__emisor_razon_social',
            'factura__receptor_nit', 'factura__receptor_razon_social',
        ))

        dtos = [self._mapear_factura_a_dto(f, cliente_cuentas, proveedor_cuentas) for f in facturas]
        dtos += [self._mapear_nota_a_dto(n) for n in notas]
        return dtos

    def _cargar_cuentas_terceros(self, app: str, modelo: str, nits: set) -> Dict[str, Optional[str]]:
        """
        Batch lookup numero_documento -> cuenta_contable_uuid para Cliente o Proveedor.
        Una sola query por tipo de tercero en lugar de N queries en el loop.
        """
        if not nits:
            return {}
        from django.apps import apps as django_apps
        Modelo = django_apps.get_model(app, modelo)
        qs = Modelo.objects.filter(
            empresa_id=self.empresa_id,
            numero_documento__in=nits,
        ).values('numero_documento', 'cuenta_contable_uuid')
        return {
            row['numero_documento']: str(row['cuenta_contable_uuid'])
            if row['cuenta_contable_uuid'] else None
            for row in qs
        }

    def _mapear_factura_a_dto(
        self,
        fact: Factura,
        cliente_cuentas: Dict[str, Optional[str]],
        proveedor_cuentas: Dict[str, Optional[str]],
    ) -> TransaccionEconomica:
        es_venta = fact.naturaleza == 'VENTA'

        tercero = TerceroSnapshot(
            tipo=TipoTercero.CLIENTE if es_venta else TipoTercero.PROVEEDOR,
            id_origen=0,
            nit=fact.receptor_nit if es_venta else fact.emisor_nit,
            razon_social=fact.receptor_razon_social if es_venta else fact.emisor_razon_social,
        )

        # v3.7.1 Pull Model: retenciones desde Contabilidad.Retencion via @property
        retefuente = fact.total_retencion_fuente
        reteica = fact.total_reteica
        reteiva = fact.total_reteiva

        cuenta_factura = str(fact.cuenta_contable_uuid) if fact.cuenta_contable_uuid else None
        lineas = []

        if es_venta:
            cuenta_cxc = cliente_cuentas.get(fact.receptor_nit)
            lineas.append(LineaTransaccion(
                concepto='INGRESO_PRINCIPAL',
                monto=fact.subtotal,
                lado='HABER',
                cuenta_hint=cuenta_factura,
            ))
            if fact.impuestos > 0:
                lineas.append(LineaTransaccion(concepto='IVA_GENERADO', monto=fact.impuestos, lado='HABER'))
            if retefuente > 0:
                lineas.append(LineaTransaccion(concepto='RETEFUENTE', monto=retefuente, lado='DEBE'))
            if reteica > 0:
                lineas.append(LineaTransaccion(concepto='RETEICA', monto=reteica, lado='DEBE'))
            if reteiva > 0:
                lineas.append(LineaTransaccion(concepto='RETEIVA', monto=reteiva, lado='DEBE'))
            neto = fact.total - retefuente - reteica - reteiva
            lineas.append(LineaTransaccion(
                concepto='CXC_CLIENTES',
                monto=neto,
                lado='DEBE',
                cuenta_hint=cuenta_cxc,
            ))
            tipo_tx = TipoTransaccion.VENTA_FACTURA
        else:
            cuenta_cxp = proveedor_cuentas.get(fact.emisor_nit)
            lineas.append(LineaTransaccion(
                concepto='GASTO_GENERAL',
                monto=fact.subtotal,
                lado='DEBE',
                cuenta_hint=cuenta_factura,
            ))
            if fact.impuestos > 0:
                lineas.append(LineaTransaccion(concepto='IVA_DESCONTABLE', monto=fact.impuestos, lado='DEBE'))
            if retefuente > 0:
                lineas.append(LineaTransaccion(concepto='RETEFUENTE', monto=retefuente, lado='HABER'))
            if reteica > 0:
                lineas.append(LineaTransaccion(concepto='RETEICA', monto=reteica, lado='HABER'))
            if reteiva > 0:
                lineas.append(LineaTransaccion(concepto='RETEIVA', monto=reteiva, lado='HABER'))
            neto = fact.total - retefuente - reteica - reteiva
            lineas.append(LineaTransaccion(
                concepto='PASIVO_COMPRA_GASTO',
                monto=neto,
                lado='HABER',
                cuenta_hint=cuenta_cxp,
            ))
            tipo_tx = TipoTransaccion.COMPRA_GASTO

        return TransaccionEconomica(
            tipo=tipo_tx,
            fecha=fact.fecha_emision.date() if hasattr(fact.fecha_emision, 'date') else fact.fecha_emision,
            descripcion=f"{'Factura Venta' if es_venta else 'Compra Electronica'} {fact.numero}",
            tercero=tercero,
            lineas=lineas,
            documento_origen=DocumentoOrigen(
                app_label='facturas',
                modelo='Factura',
                id=fact.id,
                numero=fact.numero,
            ),
        )

    def _mapear_nota_a_dto(self, nota: NotaCredito) -> TransaccionEconomica:
        es_venta = nota.factura.naturaleza == 'VENTA'

        tercero = TerceroSnapshot(
            tipo=TipoTercero.CLIENTE if es_venta else TipoTercero.PROVEEDOR,
            id_origen=0,
            nit=nota.factura.receptor_nit if es_venta else nota.factura.emisor_nit,
            razon_social=nota.factura.receptor_razon_social if es_venta else nota.factura.emisor_razon_social,
        )

        retefuente = nota.retefuente or Decimal('0')
        reteica = nota.reteica or Decimal('0')
        reteiva = nota.reteiva or Decimal('0')
        lineas = []

        if es_venta:
            lineas.append(LineaTransaccion(concepto='DEVOLUCION_VENTA', monto=nota.subtotal, lado='DEBE'))
            if nota.impuestos > 0:
                lineas.append(LineaTransaccion(concepto='IVA_GENERADO', monto=nota.impuestos, lado='DEBE'))
            if retefuente > 0:
                lineas.append(LineaTransaccion(concepto='RETEFUENTE', monto=retefuente, lado='HABER'))
            if reteica > 0:
                lineas.append(LineaTransaccion(concepto='RETEICA', monto=reteica, lado='HABER'))
            if reteiva > 0:
                lineas.append(LineaTransaccion(concepto='RETEIVA', monto=reteiva, lado='HABER'))
            neto = nota.total - retefuente - reteica - reteiva
            lineas.append(LineaTransaccion(concepto='CXC_CLIENTES', monto=neto, lado='HABER'))
            tipo_tx = TipoTransaccion.VENTA_NOTA_CREDITO
        else:
            lineas.append(LineaTransaccion(concepto='DEVOLUCION_COMPRA', monto=nota.subtotal, lado='HABER'))
            if nota.impuestos > 0:
                lineas.append(LineaTransaccion(concepto='IVA_DESCONTABLE', monto=nota.impuestos, lado='HABER'))
            if retefuente > 0:
                lineas.append(LineaTransaccion(concepto='RETEFUENTE', monto=retefuente, lado='DEBE'))
            if reteica > 0:
                lineas.append(LineaTransaccion(concepto='RETEICA', monto=reteica, lado='DEBE'))
            if reteiva > 0:
                lineas.append(LineaTransaccion(concepto='RETEIVA', monto=reteiva, lado='DEBE'))
            neto = nota.total - retefuente - reteica - reteiva
            lineas.append(LineaTransaccion(concepto='PASIVO_COMPRA_GASTO', monto=neto, lado='DEBE'))
            tipo_tx = TipoTransaccion.COMPRA_NOTA_CREDITO

        return TransaccionEconomica(
            tipo=tipo_tx,
            fecha=nota.fecha_emision.date() if hasattr(nota.fecha_emision, 'date') else nota.fecha_emision,
            descripcion=f"Nota Credito {nota.numero} (Ref: {nota.factura.numero})",
            tercero=tercero,
            lineas=lineas,
            documento_origen=DocumentoOrigen(
                app_label='facturas',
                modelo='NotaCredito',
                id=nota.id,
                numero=nota.numero,
            ),
        )
