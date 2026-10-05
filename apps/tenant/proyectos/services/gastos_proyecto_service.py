"""
GastosProyectoService (PLAN_PROYECTOS_FASE_3_EJECUCION_TIEMPOS_GASTOS_NO_
FACTURABLES, Seccion 10/42): unica orquestacion de lectura del bloque
"Gastos No Facturables" en la Fase 3 (Ejecucion) del Proyecto.

Estrictamente de solo lectura (pull model, Gastos sigue siendo la SSoT real
-- ver apps/tenant/gastos/models.py DocumentoSoporte.proyecto_uuid). No
crea, copia ni cachea gastos dentro de Proyectos; cada llamada consulta a
Gastos en vivo via DocumentoSelector.get_by_proyecto(facturable=False).
"""

import logging
from decimal import Decimal

from apps.tenant.gastos.services.selectors import DocumentoSelector

logger = logging.getLogger(__name__)

_TWO = Decimal("0.01")


class GastosProyectoService:
    """Lectura del bloque "Gastos No Facturables" de un Proyecto."""

    @staticmethod
    def get_gastos_no_facturables(proyecto):
        """QuerySet de DocumentoSoporte no facturables asociados al proyecto."""
        return DocumentoSelector.get_by_proyecto(
            proyecto.empresa_id, proyecto.uuid, facturable=False
        )

    @staticmethod
    def get_resumen_gastos_no_facturables(proyecto) -> dict:
        """
        Resumen listo para el endpoint GET .../gastos-no-facturables/ y para
        el serializer de detalle de Proyecto -- misma forma exacta en ambos
        (Seccion 42 del plan): {visible, count, total, ultimo_gasto_fecha,
        results}. `visible=False` cuando count=0 -- el frontend oculta la
        seccion entera, nunca muestra una tabla vacia.
        """
        gastos_qs = GastosProyectoService.get_gastos_no_facturables(proyecto)
        items = list(gastos_qs)

        total = sum((g.subtotal or Decimal("0.00")) for g in items)
        total = total.quantize(_TWO) if isinstance(total, Decimal) else Decimal("0.00")

        results = [
            {
                "uuid": str(g.uuid),
                "fecha": g.fecha.isoformat() if g.fecha else None,
                "numero_documento": f"{g.resolucion_dian.prefijo} {g.consecutivo}"
                if g.resolucion_dian_id
                else str(g.consecutivo),
                "proveedor_nombre": g.proveedor.razon_social if g.proveedor_id else None,
                "descripcion": g.descripcion,
                "categoria_contable": g.categoria_contable,
                "subtotal": str((g.subtotal or Decimal("0.00")).quantize(_TWO)),
            }
            for g in items
        ]

        return {
            "visible": len(items) > 0,
            "count": len(items),
            "total": str(total),
            "ultimo_gasto_fecha": results[0]["fecha"] if results else None,
            "results": results,
        }
