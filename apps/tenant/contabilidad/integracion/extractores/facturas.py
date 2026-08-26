# apps/tenant/contabilidad/integracion/extractores/facturas.py
import logging
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from apps.tenant.contabilidad.models import AsientoContable
from apps.tenant.facturas.models import Factura, NotaCredito
from .base import AbstractExtractor, DocumentoEnriquecido, CuentaAsignada, MovimientoResumen
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
    v3.10.2: cuenta_hint eliminado — cuentas resueltas via ReglaContable (Pure Pull Model).
    Retenciones: leidas desde Contabilidad.Retencion via @property Pull Model.
    """

    def extraer_pendientes(self) -> List[TransaccionEconomica]:
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
            'subtotal', 'impuestos', 'total',
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
        Placeholder — cuenta_contable_uuid fue eliminado de Cliente/Proveedor (v3.10.2 Pull Model).
        Retorna dict vacío; el Contabilizador resuelve cuentas via ReglaContable.
        """
        return {}

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

        lineas = []

        if es_venta:
            lineas.append(LineaTransaccion(
                concepto='INGRESO_PRINCIPAL',
                monto=fact.subtotal,
                lado='HABER',
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
            lineas.append(LineaTransaccion(concepto='CXC_CLIENTES', monto=neto, lado='DEBE'))
            tipo_tx = TipoTransaccion.VENTA_FACTURA
        else:
            lineas.append(LineaTransaccion(
                concepto='GASTO_GENERAL',
                monto=fact.subtotal,
                lado='DEBE',
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
            lineas.append(LineaTransaccion(concepto='PASIVO_COMPRA_GASTO', monto=neto, lado='HABER'))
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

    def get_documentos_enriquecidos(self, empresa_id: int, fecha_inicio: date, fecha_fin: date) -> List[DocumentoEnriquecido]:
        # 1. Obtener Facturas y Notas
        facturas = Factura.objects.filter(
            empresa_id=empresa_id,
            fecha_emision__date__range=(fecha_inicio, fecha_fin)
        ).order_by('fecha_emision', 'id')
        
        notas = NotaCredito.objects.filter(
            empresa_id=empresa_id,
            fecha_emision__date__range=(fecha_inicio, fecha_fin)
        ).select_related('factura').order_by('fecha_emision', 'id')
        
        # 3. Mapear asientos
        asientos = {
            (a.documento_origen_modelo, a.documento_origen_id): a 
            for a in AsientoContable.objects.filter(
                empresa_id=empresa_id,
                documento_origen_app='facturas',
                documento_origen_id__in=[f.id for f in facturas] + [n.id for n in notas]
            ).prefetch_related('movimientos', 'movimientos__cuenta')
        }
        
        res = []
        
        # Mapear Facturas
        for f in facturas:
            asiento = asientos.get(('Factura', f.id))
            es_venta = f.naturaleza == 'VENTA'
            tercero_nit = f.receptor_nit if es_venta else f.emisor_nit
            cuentas_asignadas = []

            dto = DocumentoEnriquecido(
                app_label='facturas',
                app_display='Ventas/Compras',
                modelo='Factura',
                documento_id=f.id,
                numero=f.numero,
                fecha=f.fecha_emision.date() if hasattr(f.fecha_emision, 'date') else f.fecha_emision,
                tipo_comprobante='CI' if es_venta else 'CE',
                tipo_comprobante_display='Factura de Venta' if es_venta else 'Factura de Compra',
                tercero_nit=tercero_nit,
                tercero_nombre=f.receptor_razon_social if es_venta else f.emisor_razon_social,
                subtotal=f.subtotal,
                impuestos=f.impuestos,
                total=f.total,
                cuentas_asignadas=cuentas_asignadas
            )
            self._completar_estado_asiento(dto, asiento)
            res.append(dto)
            
        # Mapear Notas
        for n in notas:
            asiento = asientos.get(('NotaCredito', n.id))
            es_venta = n.factura.naturaleza == 'VENTA'
            
            dto = DocumentoEnriquecido(
                app_label='facturas',
                app_display='Ventas/Compras',
                modelo='NotaCredito',
                documento_id=n.id,
                numero=n.numero,
                fecha=n.fecha_emision.date() if hasattr(n.fecha_emision, 'date') else n.fecha_emision,
                tipo_comprobante='NC',
                tipo_comprobante_display='Nota Crédito',
                tercero_nit=n.factura.receptor_nit if es_venta else n.factura.emisor_nit,
                tercero_nombre=n.factura.receptor_razon_social if es_venta else n.factura.emisor_razon_social,
                subtotal=n.subtotal,
                impuestos=n.impuestos,
                total=n.total,
                cuentas_asignadas=[]
            )
            self._completar_estado_asiento(dto, asiento)
            res.append(dto)
            
        return res

    def _completar_estado_asiento(self, dto: DocumentoEnriquecido, asiento):
        if asiento:
            dto.estado_contable = 'CONTABILIZADO'
            dto.asiento_uuid = str(asiento.uuid)
            dto.asiento_numero = asiento.numero
            dto.movimientos = [
                # WARNING: BUGFIX: Contabilizador._construir_asiento() solo llena
                # cuenta_codigo (string), nunca el FK legacy `cuenta` -- leer solo
                # m.cuenta.codigo mostraba SIN_CUENTA para TODO movimiento real
                # (verificado: Balance de Prueba y Estado de Resultados tambien
                # excluian estas filas por completo). cuenta_codigo tiene prioridad.
                MovimientoResumen(
                    cuenta_codigo=m.cuenta_codigo or (m.cuenta.codigo if m.cuenta else 'SIN_CUENTA'),
                    cuenta_nombre=(m.cuenta.nombre if m.cuenta else (m.descripcion or 'Sin Cuenta')),
                    debe=m.debe,
                    haber=m.haber
                ) for m in asiento.movimientos.all()
            ]
            dto.cuadra = (asiento.total_debe == asiento.total_haber)
