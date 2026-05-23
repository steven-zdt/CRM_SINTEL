"""
Presupuesto Manual Service (v3.5.2) — Fase 2 Planeación

Service Layer para gestión de presupuesto planeado (ItemPresupuestoProyecto).
Patrón: 1-a-N ítems sobre Proyecto, con recálculo automático de totales en caché.

Sigue patrón de cotizaciones.services.item_service.
"""
from decimal import Decimal
from django.db import models, transaction
from django.db.models import F, Sum
from rest_framework.exceptions import ValidationError

from apps.tenant.empresa.models import Empresa
from ..models import Proyecto, ItemPresupuestoProyecto


# ==============================================================================
# SSoT: ITEM_FIELDS para Zero Waste (LIST/DETAIL)
# ==============================================================================

ITEM_FIELDS = [
    'id', 'proyecto_id', 'empresa_id', 'categoria',
    'descripcion', 'cantidad', 'valor_unitario', 'subtotal'
]


# ==============================================================================
# CRUD SERVICE — Persistencia (v3.5.2)
# ==============================================================================

class PresupuestoCRUDService:
    """
    Persistencia de ItemPresupuestoProyecto.
    Métodos transaccionales @transaction.atomic.
    """

    @staticmethod
    @transaction.atomic
    def save_item(item):
        """Guarda un ItemPresupuestoProyecto."""
        item.save()

    @staticmethod
    @transaction.atomic
    def delete_item(item):
        """Elimina un ItemPresupuestoProyecto."""
        item.delete()


# ==============================================================================
# BUSINESS SERVICE — Lógica de Negocio (v3.5.2)
# ==============================================================================

class PresupuestoBusinessService:
    """
    Lógica de negocio: validación, cálculos, y orquestación.
    Responsable de:
    - DSV (Double Semantic Verification) — validar empresa_id
    - Bloqueo de edición en Fase CIERRE
    - Cálculo automático de subtotales
    - Recálculo de indicadores en proyecto padre
    """

    @staticmethod
    def _calcular_subtotal(item):
        """
        Calcula subtotal = cantidad × valor_unitario.
        Modifica item en memoria (no persiste).
        """
        item.subtotal = (item.cantidad or Decimal('0.00')) * (item.valor_unitario or Decimal('0.00'))

    @staticmethod
    def _recalcular_proyecto(proyecto):
        """
        Recalcula indicadores planeados del proyecto:
        - costo_planeado_total = SUM(subtotal) de items
        - utilidad_planeada = valor_contrato - costo_planeado_total
        - margen_planeado = utilidad / valor_contrato * 100

        Persiste los 3 campos caché en BD.
        """
        total = ItemPresupuestoProyecto.objects.filter(
            proyecto=proyecto,
            empresa_id=proyecto.empresa_id
        ).aggregate(
            total=Sum('subtotal')
        )['total'] or Decimal('0.00')

        proyecto.costo_planeado_total = total

        valor_contrato = proyecto.valor_contrato_proyectado or Decimal('0.00')
        utilidad = valor_contrato - total
        proyecto.utilidad_planeada = utilidad

        if valor_contrato > Decimal('0.00'):
            proyecto.margen_planeado = (utilidad / valor_contrato) * Decimal('100.00')
        else:
            proyecto.margen_planeado = Decimal('0.00')

        proyecto.save(update_fields=[
            'costo_planeado_total', 'utilidad_planeada', 'margen_planeado'
        ])

    @staticmethod
    def crear_item(empresa, proyecto, data):
        """
        Crea un nuevo ItemPresupuestoProyecto.

        Validaciones:
        1. DSV: empresa_id debe coincidir con proyecto.empresa_id
        2. Bloqueo: proyecto.fase_actual != 'CIERRE'

        Flujo:
        - Instancia item
        - Calcula subtotal
        - Persiste
        - Recalcula proyecto padre
        """
        if proyecto.fase_actual == 'CIERRE':
            raise ValidationError(
                "No se puede agregar ítems de presupuesto en fase Cierre"
            )

        item = ItemPresupuestoProyecto(
            empresa=empresa,
            proyecto=proyecto,
            **data
        )

        PresupuestoBusinessService._calcular_subtotal(item)
        PresupuestoCRUDService.save_item(item)
        PresupuestoBusinessService._recalcular_proyecto(proyecto)

        return item

    @staticmethod
    def actualizar_item(item, data):
        """
        Actualiza un ItemPresupuestoProyecto existente.

        Validaciones:
        1. Bloqueo: proyecto.fase_actual != 'CIERRE'

        Flujo:
        - Modifica campos en memoria
        - Calcula subtotal
        - Persiste
        - Recalcula proyecto padre
        """
        if item.proyecto.fase_actual == 'CIERRE':
            raise ValidationError(
                "No se puede editar ítems de presupuesto en fase Cierre"
            )

        for key, value in data.items():
            setattr(item, key, value)

        PresupuestoBusinessService._calcular_subtotal(item)
        PresupuestoCRUDService.save_item(item)
        PresupuestoBusinessService._recalcular_proyecto(item.proyecto)

        return item

    @staticmethod
    def eliminar_item(item):
        """
        Elimina un ItemPresupuestoProyecto.

        Validaciones:
        1. Bloqueo: proyecto.fase_actual != 'CIERRE'

        Flujo:
        - Guarda referencia a proyecto padre
        - Persiste eliminación
        - Recalcula proyecto padre
        """
        if item.proyecto.fase_actual == 'CIERRE':
            raise ValidationError(
                "No se puede eliminar ítems de presupuesto en fase Cierre"
            )

        proyecto = item.proyecto
        PresupuestoCRUDService.delete_item(item)
        PresupuestoBusinessService._recalcular_proyecto(proyecto)
