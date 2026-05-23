"""
Extractor de Inventario para Dashboard v3.9.4
Pull Model: Consulta selectors.py de inventario, nunca importa models.py
Zero-Waste: Usa .aggregate() para métricas Kardex.
"""
from decimal import Decimal

from django.db.models import Count, Sum

from apps.tenant.dashboard.services.dtos import WidgetInventarioDTO


class InventarioExtractor:
    """Extrae métricas de Inventario (Kardex universal)."""

    @staticmethod
    def extraer_metricas(empresa_id: int) -> WidgetInventarioDTO:
        """
        Extrae métricas de Inventario usando selectors.py
        Incluye Productos, Activos, Servicios bajo un Kardex unificado.

        Args:
            empresa_id: ID de la empresa (Double Semantic Verification)

        Returns:
            WidgetInventarioDTO con métricas consolidadas
        """
        try:
            from apps.tenant.inventario.services.selectors import InventarioSelectors

            # Obtener queryset base (Productos + Activos + Servicios)
            qs = InventarioSelectors.qs_kardex(empresa_id)

            # Métrica 1: Total de items en inventario
            total_productos = qs.count()

            # Métrica 2: Items bajo stock mínimo
            productos_bajo_stock = qs.filter(
                cantidad_stock__lt=Sum('cantidad_minima')
            ).count()

            # Métrica 3: Movimientos del mes (desde tabla MovimientoKardex)
            try:
                from apps.tenant.inventario.services.selectors import InventarioSelectors
                qs_movimientos = InventarioSelectors.qs_movimientos_mes(empresa_id)
                movimientos_mes = qs_movimientos.count()
            except:
                movimientos_mes = 0

            # Métrica 4: Valor total de inventario
            valor_inventario = qs.aggregate(
                total=Sum('valor_unitario_promedio_ponderado', output_field=Decimal('0.00'))
            )['total'] or Decimal('0.00')

            # Métrica 5: Rotación promedio (movimientos / items)
            rotacion_promedio = Decimal(movimientos_mes) / max(total_productos, 1)

            return WidgetInventarioDTO(
                total_productos=total_productos,
                productos_bajo_stock=productos_bajo_stock,
                movimientos_mes=movimientos_mes,
                valor_inventario=valor_inventario,
                rotacion_promedio=rotacion_promedio
            )

        except Exception as e:
            return WidgetInventarioDTO(
                total_productos=0,
                productos_bajo_stock=0,
                movimientos_mes=0,
                valor_inventario=Decimal('0.00'),
                rotacion_promedio=Decimal('0.00')
            )
