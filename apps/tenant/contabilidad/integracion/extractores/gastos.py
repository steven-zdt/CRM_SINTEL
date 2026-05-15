# apps/tenant/contabilidad/integracion/extractores/gastos.py
from typing import List
from decimal import Decimal

from apps.tenant.gastos.models import DocumentoSoporte
from .base import AbstractExtractor
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
        from apps.tenant.contabilidad.models import AsientoContable

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
            'id', 'fecha', 'subtotal', 'retefuente', 'retefuente_porcentaje',
            'reteica', 'reteica_porcentaje', 'total', 'consecutivo',
            'resolucion_dian__prefijo',
            'observaciones', 'proveedor__numero_documento', 'proveedor__razon_social',
            'proveedor__cuenta_contable_uuid',
            'proveedor_id', 'categoria_contable', 'cuenta_gasto_uuid',
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

        # 1. Main expense line (DEBIT) — cuenta_gasto_uuid como hint si esta configurado
        concepto_gasto = doc.categoria_contable or 'GASTO_GENERAL'
        cuenta_gasto_hint = str(doc.cuenta_gasto_uuid) if doc.cuenta_gasto_uuid else None
        lineas.append(LineaTransaccion(
            concepto=concepto_gasto,
            monto=doc.subtotal,
            lado='DEBE',
            cuenta_hint=cuenta_gasto_hint,
        ))

        # 2. Retentions (CREDIT) — leer desde campo DEPRECATED que aun existe en DB
        retefuente = doc.retefuente or Decimal('0')
        reteica = doc.reteica or Decimal('0')
        if retefuente > 0:
            lineas.append(LineaTransaccion(concepto='RETEFUENTE', monto=retefuente, lado='HABER'))
        if reteica > 0:
            lineas.append(LineaTransaccion(concepto='RETEICA', monto=reteica, lado='HABER'))

        # 3. Balancing line (CREDIT) — cuenta_contable_uuid del Proveedor como hint
        cuenta_proveedor_hint = (
            str(doc.proveedor.cuenta_contable_uuid)
            if doc.proveedor.cuenta_contable_uuid else None
        )
        lineas.append(LineaTransaccion(
            concepto='PASIVO_COMPRA_GASTO',
            monto=doc.total,
            lado='HABER',
            cuenta_hint=cuenta_proveedor_hint,
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
