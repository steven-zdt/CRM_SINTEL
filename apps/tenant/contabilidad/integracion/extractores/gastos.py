# apps/tenant/contabilidad/integracion/extractores/gastos.py
from typing import List
from decimal import Decimal
from datetime import date

from apps.tenant.contabilidad.models import AsientoContable
from apps.tenant.gastos.models import DocumentoSoporte
from .base import AbstractExtractor, DocumentoEnriquecido, CuentaAsignada, MovimientoResumen
from ..dtos import (
    TransaccionEconomica,
    TipoTransaccion,
    TerceroSnapshot,
    TipoTercero,
    LineaTransaccion,
    ImpuestoLinea,
    DocumentoOrigen
)


class ExtractorGastos(AbstractExtractor):
    """
    Extractor for DocumentoSoporte (Gastos/Compras).
    """

    def extraer_pendientes(self) -> List[TransaccionEconomica]:
        """
        Extract non-journalized DocumentoSoporte records.
        """
        ya_contabilizados = set(
            AsientoContable.objects.filter(
                empresa_id=self.empresa_id,
                documento_origen_app='gastos',
                documento_origen_modelo='DocumentoSoporte',
                documento_origen_reversado=False,
            ).values_list('documento_origen_id', flat=True)
        )

        documentos = DocumentoSoporte.objects.filter(
            empresa_id=self.empresa_id,
            anulado=False,
        ).exclude(
            id__in=ya_contabilizados,
        ).select_related('proveedor', 'resolucion_dian').only(
            'id', 'fecha', 'subtotal', 'total', 'consecutivo',
            # retefuente/reteica_porcentaje eliminados en v3.7.1 Pull Model
            # usar doc.total_retefuente / doc.total_reteica (@property → Retencion table)
            'resolucion_dian__prefijo',
            'observaciones', 'proveedor__numero_documento', 'proveedor__razon_social',
            'proveedor_id', 'categoria_contable', 'empresa_id',
        )

        return [self._mapear_a_dto(doc) for doc in documentos]

    def _mapear_a_dto(self, doc: DocumentoSoporte) -> TransaccionEconomica:
        """
        Convert DocumentoSoporte model instance to TransaccionEconomica DTO.
        """
        # Snapshot of the third party
        tercero = TerceroSnapshot(
            tipo=TipoTercero.PROVEEDOR,
            id_origen=doc.proveedor_id,
            nit=doc.proveedor.numero_documento,
            razon_social=doc.proveedor.razon_social
        )

        # Build lines
        lineas = []

        # 1. Main expense line (DEBIT) — ReglaContable resuelve cuenta via categoria_contable
        concepto_gasto = doc.categoria_contable or 'GASTO_GENERAL'
        lineas.append(LineaTransaccion(
            concepto=concepto_gasto,
            monto=doc.subtotal,
            lado='DEBE',
        ))

        # 2. Retentions (CREDIT) — Pull Model v3.7.1: leer desde Retencion via @property
        retefuente = doc.total_retefuente or Decimal('0')
        reteica = doc.total_reteica or Decimal('0')
        if retefuente > 0:
            lineas.append(LineaTransaccion(concepto='RETEFUENTE', monto=retefuente, lado='HABER'))
        if reteica > 0:
            lineas.append(LineaTransaccion(concepto='RETEICA', monto=reteica, lado='HABER'))

        # 3. Balancing line (CREDIT) — ReglaContable resuelve cuenta via NIT proveedor
        lineas.append(LineaTransaccion(
            concepto='PASIVO_COMPRA_GASTO',
            monto=doc.total,
            lado='HABER',
        ))

        return TransaccionEconomica(
            tipo=TipoTransaccion.COMPRA_GASTO,
            fecha=doc.fecha,
            descripcion=f"Documento Soporte {doc.numero_documento} - {doc.proveedor.razon_social}",
            tercero=tercero,
            lineas=lineas,
            documento_origen=DocumentoOrigen(
                app_label='gastos',
                modelo='DocumentoSoporte',
                id=doc.id,
                numero=doc.numero_documento
            ),
            observaciones=doc.observaciones or ""
        )

    def get_documentos_enriquecidos(self, empresa_id: int, fecha_inicio: date, fecha_fin: date) -> List[DocumentoEnriquecido]:
        # 1. Obtener todos los documentos del periodo
        documentos = DocumentoSoporte.objects.filter(
            empresa_id=empresa_id,
            fecha__range=(fecha_inicio, fecha_fin)
        ).select_related('proveedor').order_by('fecha', 'id')
        
        # 2. Mapear asientos existentes para cruce
        asientos = {
            (a.documento_origen_modelo, a.documento_origen_id): a 
            for a in AsientoContable.objects.filter(
                empresa_id=empresa_id,
                documento_origen_app='gastos',
                documento_origen_modelo='DocumentoSoporte',
                documento_origen_id__in=[d.id for d in documentos]
            ).prefetch_related('movimientos', 'movimientos__cuenta')
        }
        
        res = []
        for doc in documentos:
            asiento = asientos.get(('DocumentoSoporte', doc.id))
            
            cuentas_asignadas = []

            # Construir DTO
            dto = DocumentoEnriquecido(
                app_label='gastos',
                app_display='Compras/Gastos',
                modelo='DocumentoSoporte',
                documento_id=doc.id,
                numero=doc.numero_documento,
                fecha=doc.fecha,
                tipo_comprobante='CE',
                tipo_comprobante_display='Comprobante de Egreso',
                tercero_nit=doc.proveedor.numero_documento,
                tercero_nombre=doc.proveedor.razon_social,
                subtotal=doc.subtotal,
                impuestos=doc.total - doc.subtotal,
                total=doc.total,
                cuentas_asignadas=cuentas_asignadas
            )
            
            if asiento:
                dto.estado_contable = 'CONTABILIZADO'
                dto.asiento_uuid = str(asiento.uuid)
                dto.asiento_numero = asiento.numero
                dto.movimientos = [
                    MovimientoResumen(
                        cuenta_codigo=m.cuenta.codigo if m.cuenta else 'SIN_CUENTA',
                        cuenta_nombre=m.cuenta.nombre if m.cuenta else 'Sin Cuenta',
                        debe=m.debe,
                        haber=m.haber
                    ) for m in asiento.movimientos.all()
                ]
                dto.cuadra = (asiento.total_debe == asiento.total_haber)
            
            res.append(dto)
            
        return res
