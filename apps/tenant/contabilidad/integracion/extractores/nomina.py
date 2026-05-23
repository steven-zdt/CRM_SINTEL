# apps/tenant/contabilidad/integracion/extractores/nomina.py
from typing import List
from decimal import Decimal
import logging

from apps.tenant.empleados.models import Devengo
from .base import AbstractExtractor, DocumentoEnriquecido, CuentaAsignada, MovimientoResumen
from apps.tenant.contabilidad.services.selectors import CuentaContableSelector
from datetime import date
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
            cuenta_contable_uuid__isnull=False,  # Solo devengos con cuenta PUC asignada
        ).exclude(
            id__in=nomina_contabilizada,
        ).select_related('empleado').only(
            'id', 'fecha_pago', 'periodo_mes',
            'salario_base', 'auxilio_transporte', 'otros_devengos',
            'salud_empleado', 'pension_empleado', 'prestamos', 'descuentos_operativos',
            'neto_pagar', 'cuenta_contable_uuid',
            'empleado__numero_documento', 'empleado__primer_nombre', 'empleado__primer_apellido',
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

        # 3. Neto a Pagar (HABER - Pasivo) — cuenta_contable_uuid del Devengo (SSoT Fase1)
        cuenta_devengo_hint = str(nomina.cuenta_contable_uuid) if nomina.cuenta_contable_uuid else None
        lineas.append(LineaTransaccion(
            concepto='PASIVO_NOMINA_POR_PAGAR',
            monto=nomina.neto_pagar,
            lado='HABER',
            cuenta_hint=cuenta_devengo_hint,
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

    def get_documentos_enriquecidos(self, empresa_id: int, fecha_inicio: date, fecha_fin: date) -> List[DocumentoEnriquecido]:
        from apps.tenant.contabilidad.models import AsientoContable
        
        # 1. Obtener devengos del periodo (anulado=False para el Libro Diario activo)
        registros = Devengo.objects.filter(
            empresa_id=empresa_id,
            anulado=False,
            fecha_pago__range=(fecha_inicio, fecha_fin)
        ).select_related('empleado').only(
            'id', 'uuid', 'fecha_pago', 'periodo_mes',
            'salario_base', 'auxilio_transporte', 'otros_devengos',
            'salud_empleado', 'pension_empleado', 'prestamos', 'descuentos_operativos',
            'neto_pagar', 'cuenta_contable_uuid',
            'empleado__numero_documento', 'empleado__primer_nombre', 'empleado__primer_apellido',
        ).order_by('fecha_pago', 'id')
        
        # 2. Mapear asientos
        asientos = {
            (a.documento_origen_modelo, a.documento_origen_id): a 
            for a in AsientoContable.objects.filter(
                empresa_id=empresa_id,
                documento_origen_app='empleados',
                documento_origen_modelo='Devengo',
                documento_origen_id__in=[r.id for r in registros]
            ).prefetch_related('movimientos', 'movimientos__cuenta')
        }
        
        res = []
        for r in registros:
            asiento = asientos.get(('Devengo', r.id))
            
            cuentas_asignadas = []
            if r.cuenta_contable_uuid:
                cod, nom = CuentaContableSelector.resolve_label_by_uuid(r.cuenta_contable_uuid, empresa_id)
                cuentas_asignadas.append(CuentaAsignada(
                    concepto='Pasivo Nómina (Haber)',
                    uuid=str(r.cuenta_contable_uuid),
                    codigo_puc=cod,
                    nombre=nom,
                    monto=r.neto_pagar
                ))

            dto = DocumentoEnriquecido(
                app_label='empleados',
                app_display='Nómina',
                modelo='Devengo',
                documento_id=r.id,
                numero=f"NOM-{r.periodo_mes}-{r.id}",
                fecha=r.fecha_pago,
                tipo_comprobante='CN', # Nómina
                tipo_comprobante_display='Comprobante de Nómina',
                tercero_nit=r.empleado.numero_documento,
                tercero_nombre=f"{r.empleado.primer_nombre} {r.empleado.primer_apellido}",
                subtotal=r.neto_pagar,
                impuestos=Decimal('0'),
                total=r.neto_pagar,
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
