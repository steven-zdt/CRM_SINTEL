"""
Extractor de Gastos para Dashboard v3.9.5 — datos reales.
Pull Model: usa DocumentoSelector, no importa models.py directamente.
"""
import logging
from decimal import Decimal

from apps.tenant.dashboard.services.dtos import WidgetGastosDTO

_ZERO = Decimal('0.00')
logger = logging.getLogger(__name__)


class GastosExtractor:

    @staticmethod
    def extraer_metricas(empresa_id: int) -> WidgetGastosDTO:
        try:
            from apps.tenant.gastos.services.selectors import DocumentoSelector

            summary = DocumentoSelector.get_summary(empresa_id)

            total_gastos_mes = Decimal(str(summary.get('total_gastos_mes', '0') or '0'))
            documentos_emitidos = summary.get('documentos_emitidos', 0) or 0

            # Gastos anulados (total acumulado, sin filtro de mes)
            qs = DocumentoSelector.get_list(empresa_id)
            gastos_anulados = qs.filter(anulado=True).count()
            gastos_activos = qs.filter(anulado=False).count()

            gasto_promedio = total_gastos_mes / max(documentos_emitidos, 1)

            return WidgetGastosDTO(
                total_gastos_mes=total_gastos_mes.quantize(Decimal('0.01')),
                gastos_pendientes=gastos_activos,
                gastos_anulados=gastos_anulados,
                gasto_promedio=gasto_promedio.quantize(Decimal('0.01')),
            )

        except Exception:
            logger.exception("GastosExtractor: fallo calculando metricas (empresa_id=%s)", empresa_id)
            return WidgetGastosDTO(_ZERO, 0, 0, _ZERO)
