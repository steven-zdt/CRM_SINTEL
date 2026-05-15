# apps/tenant/contabilidad/integracion/extractores/nomina.py
from typing import List
from decimal import Decimal
import logging

from apps.tenant.empleados.models import Devengo
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

class ExtractorNomina(AbstractExtractor):
    """
    Extractor especializado para registros de Nómina (Devengos).
    
    # WARNING: ARQUITECTURA PULL: Extrae registros de la app empleados.
    # WARNING: ZERO WASTE: Solo extrae registros no anulados y no contabilizados.
    """

    def extraer_pendientes(self) -> List[TransaccionEconomica]:
        """
        Extrae registros de nómina pendientes de contabilizar.
        """
        from apps.tenant.contabilidad.models import AsientoContable

        nomina_contabilizada = set(
            AsientoContable.objects.filter(
                empresa_id=self.empresa_id,
                documento_origen_app='empleados',
                documento_origen_modelo='Devengo',
                documento_origen_reversado=False,
            ).values_list('documento_origen_id', flat=True)
        )

        registros = Devengo.objects.filter(
            empresa_id=self.empresa_id,
            anulado=False,
        ).exclude(
            id__in=nomina_contabilizada,
        ).select_related('empleado').only(
            'id', 'fecha_pago', 'periodo_mes',
            'salario_base', 'auxilio_transporte', 'otros_devengos',
            'salud_empleado', 'pension_empleado', 'prestamos', 'descuentos_operativos',
            'neto_pagar',
            'empleado__numero_documento', 'empleado__primer_nombre', 'empleado__primer_apellido',
            'empleado__cuenta_contable_uuid',
        )

        return [self._mapear_a_dto(r) for r in registros]

    def _mapear_a_dto(self, nomina: Devengo) -> TransaccionEconomica:
        """
        Mapea un registro de Devengo al DTO unificado.
        """
        tercero = TerceroSnapshot(
            tipo=TipoTercero.EMPLEADO,
            id_origen=nomina.empleado_id,
            nit=nomina.empleado.numero_documento,
            razon_social=f"{nomina.empleado.primer_nombre} {nomina.empleado.primer_apellido}"
        )

        lineas = []
        
        # 1. Devengos (DEBE - Gasto)
        if nomina.salario_base > 0:
            lineas.append(LineaTransaccion(
                concepto="NOMINA_SUELDOS",
                monto=nomina.salario_base,
                lado='DEBE'
            ))
            
        if nomina.auxilio_transporte > 0:
            lineas.append(LineaTransaccion(
                concepto="NOMINA_AUXILIO_TRANSPORTE",
                monto=nomina.auxilio_transporte,
                lado='DEBE'
            ))

        if nomina.otros_devengos > 0:
            lineas.append(LineaTransaccion(
                concepto="NOMINA_OTROS_DEVENGOS",
                monto=nomina.otros_devengos,
                lado='DEBE'
            ))

        # 2. Deducciones (HABER - Pasivo/Activo)
        if nomina.salud_empleado > 0:
            lineas.append(LineaTransaccion(
                concepto="NOMINA_APORTE_SALUD",
                monto=nomina.salud_empleado,
                lado='HABER'
            ))

        if nomina.pension_empleado > 0:
            lineas.append(LineaTransaccion(
                concepto="NOMINA_APORTE_PENSION",
                monto=nomina.pension_empleado,
                lado='HABER'
            ))

        if nomina.prestamos > 0:
            # Los préstamos suelen ser una CXC (Activo) que disminuye
            lineas.append(LineaTransaccion(
                concepto="NOMINA_PRESTAMOS",
                monto=nomina.prestamos,
                lado='HABER'
            ))

        if nomina.descuentos_operativos > 0:
            lineas.append(LineaTransaccion(
                concepto="NOMINA_DESCUENTOS",
                monto=nomina.descuentos_operativos,
                lado='HABER'
            ))

        # 3. Neto a Pagar (HABER - Pasivo) — cuenta_contable_uuid del empleado como hint
        cuenta_empleado_hint = (
            str(nomina.empleado.cuenta_contable_uuid)
            if nomina.empleado.cuenta_contable_uuid else None
        )
        lineas.append(LineaTransaccion(
            concepto='PASIVO_NOMINA_POR_PAGAR',
            monto=nomina.neto_pagar,
            lado='HABER',
            cuenta_hint=cuenta_empleado_hint,
        ))

        return TransaccionEconomica(
            tipo=TipoTransaccion.NOMINA_PAGO,
            fecha=nomina.fecha_pago,
            descripcion=f"Nómina Periodo {nomina.periodo_mes}",
            tercero=tercero,
            lineas=lineas,
            documento_origen=DocumentoOrigen(
                app_label='empleados',
                modelo='Devengo',
                id=nomina.id,
                numero=f"{nomina.periodo_mes}-{nomina.id}"
            )
        )
