"""
Extractor de Facturas para Dashboard v3.9.5 — datos reales.
Pull Model: usa FacturaSelectors, no importa models.py directamente.
"""
import logging
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from apps.tenant.dashboard.services.dtos import WidgetFacturasDTO

_ZERO = Decimal('0.00')
logger = logging.getLogger(__name__)


class FacturasExtractor:

    @staticmethod
    def extraer_metricas(empresa_id: int) -> WidgetFacturasDTO:
        try:
            from apps.tenant.facturas.services.selectors import FacturaSelectors

            qs = FacturaSelectors.qs_list(empresa_id).filter(estado='ACEPTADA')
            total_facturas = qs.count()

            # Pendientes = no pagadas completamente
            facturas_pendientes = qs.filter(
                estado_pago__in=['NO_PAGADA', 'PAGO_PARCIAL']
            ).count()

            # Vencidas = fecha de vencimiento pasada y sin pagar
            hoy = timezone.now().date()
            facturas_vencidas = qs.filter(
                fecha_vencimiento__lt=hoy,
                estado_pago__in=['NO_PAGADA', 'PAGO_PARCIAL']
            ).count()

            # Ingresos del mes actual (facturas ACEPTADA emitidas este mes)
            inicio_mes = hoy.replace(day=1)
            ingresos_mes = qs.filter(
                fecha_emision__date__gte=inicio_mes,
                estado='ACEPTADA',
            ).aggregate(t=Sum('total'))['t'] or _ZERO

            ingresos_promedio = ingresos_mes / max(total_facturas, 1)

            return WidgetFacturasDTO(
                total_facturas=total_facturas,
                facturas_pendientes=facturas_pendientes,
                facturas_vencidas=facturas_vencidas,
                ingresos_mes=Decimal(str(ingresos_mes)).quantize(Decimal('0.01')),
                ingresos_promedio=Decimal(str(ingresos_promedio)).quantize(Decimal('0.01')),
            )

        except Exception:
            logger.exception("FacturasExtractor: fallo calculando metricas (empresa_id=%s)", empresa_id)
            return WidgetFacturasDTO(0, 0, 0, _ZERO, _ZERO)
