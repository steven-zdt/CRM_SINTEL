"""
Extractor de Inventario para Dashboard v3.9.5 — datos reales.
Pull Model: usa ProductoSelector, ActivoFijoSelector, ServicioSelector,
MovimientoInventarioSelector. No importa models.py directamente.
"""
import logging
from decimal import Decimal

from django.db.models import F, Sum

from apps.tenant.dashboard.services.dtos import WidgetInventarioDTO

_ZERO = Decimal('0.00')
logger = logging.getLogger(__name__)


class InventarioExtractor:

    @staticmethod
    def extraer_metricas(empresa_id: int) -> WidgetInventarioDTO:
        try:
            from apps.tenant.inventario.services.selectors import (
                ActivoFijoSelector,
                MovimientoInventarioSelector,
                ProductoSelector,
                ServicioSelector,
            )

            prod_qs     = ProductoSelector.get_list(empresa_id)
            activo_qs   = ActivoFijoSelector.get_list(empresa_id)
            servicio_qs = ServicioSelector.get_list(empresa_id)

            total_productos = prod_qs.count() + activo_qs.count() + servicio_qs.count()

            # Productos con stock por debajo del mínimo
            productos_bajo_stock = prod_qs.filter(
                stock_actual__lt=F('stock_minimo'),
                activo=True,
            ).count()

            # Movimientos totales registrados en el kardex
            movimientos_mes = MovimientoInventarioSelector.get_list(empresa_id).count()

            # Valor de inventario = Σ(stock_actual × costo_promedio) de productos
            agg = prod_qs.filter(activo=True).aggregate(
                valor=Sum(F('stock_actual') * F('costo_promedio'))
            )
            valor_inventario = Decimal(str(agg['valor'] or 0)).quantize(Decimal('0.01'))

            rotacion_promedio = Decimal(movimientos_mes) / max(total_productos, 1)

            return WidgetInventarioDTO(
                total_productos=total_productos,
                productos_bajo_stock=productos_bajo_stock,
                movimientos_mes=movimientos_mes,
                valor_inventario=valor_inventario,
                rotacion_promedio=rotacion_promedio.quantize(Decimal('0.01')),
            )

        except Exception:
            logger.exception("InventarioExtractor: fallo calculando metricas (empresa_id=%s)", empresa_id)
            return WidgetInventarioDTO(0, 0, 0, _ZERO, _ZERO)
