"""
Presupuesto Manual Service (v3.5.2) - Fase 2 Planeacion

Service Layer para gestion de presupuesto planeado (ItemPresupuestoProyecto).
Patron: 1-a-N items sobre Proyecto, con recalculo automatico de totales en cache.

Sigue patron de cotizaciones.services.item_service.
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from ..models import ItemPresupuestoProyecto

# ==============================================================================
# SSoT: ITEM_FIELDS para Zero Waste (LIST/DETAIL)
# ==============================================================================

ITEM_FIELDS = [
    "id",
    "uuid",
    "proyecto_id",
    "empresa_id",
    "categoria",
    "descripcion",
    "cantidad",
    "valor_unitario",
    "subtotal",
    "origen",
    "cotizacion_item_uuid",
]


# ==============================================================================
# CRUD SERVICE - Persistencia (v3.5.2)
# ==============================================================================


class PresupuestoCRUDService:
    """
    Persistencia de ItemPresupuestoProyecto.
    Metodos transaccionales @transaction.atomic.
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
# BUSINESS SERVICE - Logica de Negocio (v3.5.2)
# ==============================================================================


class PresupuestoBusinessService:
    """
    Logica de negocio: validacion, calculos, y orquestacion.
    Responsable de:
    - DSV (Double Semantic Verification) - validar empresa_id
    - Bloqueo de edicion en Fase CIERRE
    - Calculo automatico de subtotales
    - Recalculo de indicadores en proyecto padre
    """

    @staticmethod
    def _calcular_subtotal(item):
        """
        Calcula subtotal = cantidad x valor_unitario.
        Modifica item en memoria (no persiste).
        """
        item.subtotal = (item.cantidad or Decimal("0.00")) * (
            item.valor_unitario or Decimal("0.00")
        )

    @staticmethod
    def _recalcular_proyecto(proyecto):
        """
        Recalcula indicadores planeados del proyecto:
        - costo_planeado_total = SUM(subtotal) de items
        - utilidad_planeada = valor_contrato - costo_planeado_total
        - margen_planeado = utilidad / valor_contrato * 100

        Persiste los 3 campos cache en BD.
        """
        total = ItemPresupuestoProyecto.objects.filter(
            proyecto=proyecto, empresa_id=proyecto.empresa_id
        ).aggregate(total=Sum("subtotal"))["total"] or Decimal("0.00")

        proyecto.costo_planeado_total = total

        valor_contrato = proyecto.valor_contrato_proyectado or Decimal("0.00")
        utilidad = valor_contrato - total
        proyecto.utilidad_planeada = utilidad

        if valor_contrato > Decimal("0.00"):
            proyecto.margen_planeado = (utilidad / valor_contrato) * Decimal("100.00")
        else:
            proyecto.margen_planeado = Decimal("0.00")

        proyecto.save(
            update_fields=["costo_planeado_total", "utilidad_planeada", "margen_planeado"]
        )

    @staticmethod
    @transaction.atomic
    def crear_item(empresa, proyecto, data):
        """
        [PERF-M1] @transaction.atomic: la escritura del item y el recalculo del
        proyecto padre ahora son una sola transaccion -- antes, si _recalcular_proyecto
        fallaba, el item ya habia quedado persistido (via save_item, atomico por
        separado) pero los totales cacheados del proyecto quedaban desactualizados.

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
        if proyecto.empresa_id != empresa.id:
            raise ValidationError(
                "La empresa del item no coincide con la empresa del proyecto (DSV fallo)"
            )

        if proyecto.fase_actual == "CIERRE":
            raise ValidationError("No se puede agregar items de presupuesto en fase Cierre")

        # Creacion manual SIEMPRE es origen=MANUAL -- origen=COTIZACION solo
        # lo asigna sincronizar_desde_cotizacion() mas abajo, nunca este
        # endpoint (evita que el usuario fabrique un item "de cotizacion"
        # sin que exista de verdad en la Cotizacion vinculada).
        data.pop("origen", None)
        data.pop("cotizacion_item_uuid", None)
        item = ItemPresupuestoProyecto(
            empresa=empresa,
            proyecto=proyecto,
            origen=ItemPresupuestoProyecto.Origen.MANUAL,
            **data,
        )

        PresupuestoBusinessService._calcular_subtotal(item)
        PresupuestoCRUDService.save_item(item)
        PresupuestoBusinessService._recalcular_proyecto(proyecto)

        return item

    @staticmethod
    @transaction.atomic
    def actualizar_item(item, data):
        """
        [PERF-M1] @transaction.atomic -- ver nota en crear_item().

        Actualiza un ItemPresupuestoProyecto existente. Valido para
        cualquier `origen` (MANUAL o COTIZACION, PLAN_PROYECTOS_FASE_2_
        COTIZACION_RECURSOS_PRESUPUESTO: decision explicita del usuario de
        reemplazar la restriccion original de la Fase 33 del plan -- el
        Desglose de Costos Planeados es editable/borrable libremente de
        forma manual por defecto, "Sincronizar costos de cotizacion" es
        solo una conveniencia opcional, no la unica via de cambio). `origen`/
        `cotizacion_item_uuid` del item nunca se alteran por esta via (se
        preservan los que ya tenia) -- solo
        `sincronizar_desde_cotizacion()` los asigna.

        Validaciones:
        1. Bloqueo: proyecto.fase_actual != 'CIERRE'

        Flujo:
        - Modifica campos en memoria
        - Calcula subtotal
        - Persiste
        - Recalcula proyecto padre
        """
        if item.proyecto.fase_actual == "CIERRE":
            raise ValidationError("No se puede editar items de presupuesto en fase Cierre")

        data.pop("origen", None)
        data.pop("cotizacion_item_uuid", None)
        for key, value in data.items():
            setattr(item, key, value)

        PresupuestoBusinessService._calcular_subtotal(item)
        PresupuestoCRUDService.save_item(item)
        PresupuestoBusinessService._recalcular_proyecto(item.proyecto)

        return item

    @staticmethod
    @transaction.atomic
    def eliminar_item(item):
        """
        [PERF-M1] @transaction.atomic -- ver nota en crear_item().

        Elimina un ItemPresupuestoProyecto. Valido para cualquier `origen`
        (MANUAL o COTIZACION, ver nota en actualizar_item() -- decision
        explicita del usuario). Si el item eliminado era origen=COTIZACION
        y la Cotizacion sigue vinculada, una sincronizacion posterior puede
        volver a crearlo (comportamiento esperado: sincronizar siempre
        refleja el estado actual de la Cotizacion, no "recuerda" que el
        usuario borro esa linea).

        Validaciones:
        1. Bloqueo: proyecto.fase_actual != 'CIERRE'

        Flujo:
        - Guarda referencia a proyecto padre
        - Persiste eliminacion
        - Recalcula proyecto padre
        """
        if item.proyecto.fase_actual == "CIERRE":
            raise ValidationError("No se puede eliminar items de presupuesto en fase Cierre")

        proyecto = item.proyecto
        PresupuestoCRUDService.delete_item(item)
        PresupuestoBusinessService._recalcular_proyecto(proyecto)

    @staticmethod
    @transaction.atomic
    def sincronizar_desde_cotizacion(empresa, proyecto, cotizacion):
        """
        PLAN_PROYECTOS_FASE_2_COTIZACION_RECURSOS_PRESUPUESTO Fase 13/14/15:
        upsert idempotente de los items origen=COTIZACION del presupuesto
        del Proyecto, a partir del cuerpo real de `CotizacionItem` de la
        Cotizacion vinculada. Nunca toca origen=MANUAL. Reutiliza este mismo
        servicio (SSoT de persistencia de ItemPresupuestoProyecto) -- no es
        un segundo motor de presupuesto.

        Sincronizacion diferencial por `cotizacion_item_uuid` (mismo patron
        ya probado en `OrdenCompraCRUDService.actualizar_orden()` para items
        de Orden de Compra): UPDATE de los que ya existen, INSERT de los
        nuevos, DELETE de los que ya no estan en la Cotizacion -- nunca
        DELETE-todos + INSERT-todos (eso si duplicaria historial/UUIDs en
        cada sincronizacion).
        """
        from apps.tenant.cotizaciones.models import CotizacionItem

        from .cotizacion_planeacion_service import mapear_tipo_item_a_recurso

        items_cotizacion = list(
            CotizacionItem.objects.filter(cotizacion_id=cotizacion.id, empresa_id=empresa.id).only(
                "id", "uuid", "tipo_item", "descripcion", "cantidad", "costo_unitario"
            )
        )

        existentes = {
            str(item.cotizacion_item_uuid): item
            for item in ItemPresupuestoProyecto.objects.filter(
                proyecto=proyecto,
                empresa_id=empresa.id,
                origen=ItemPresupuestoProyecto.Origen.COTIZACION,
            )
        }

        uuids_entrantes = set()
        a_crear = []
        a_actualizar = []

        for item in items_cotizacion:
            uuid_str = str(item.uuid)
            uuids_entrantes.add(uuid_str)
            recurso = mapear_tipo_item_a_recurso(item.tipo_item)
            cantidad = item.cantidad or Decimal("0.00")
            costo_unitario = item.costo_unitario or Decimal("0.00")
            costo_base = cantidad * costo_unitario

            existente = existentes.get(uuid_str)
            if existente:
                existente.categoria = recurso
                existente.descripcion = item.descripcion or ""
                existente.cantidad = cantidad
                existente.valor_unitario = costo_unitario
                existente.subtotal = costo_base
                a_actualizar.append(existente)
            else:
                a_crear.append(
                    ItemPresupuestoProyecto(
                        empresa=empresa,
                        proyecto=proyecto,
                        categoria=recurso,
                        descripcion=item.descripcion or "",
                        cantidad=cantidad,
                        valor_unitario=costo_unitario,
                        subtotal=costo_base,
                        origen=ItemPresupuestoProyecto.Origen.COTIZACION,
                        cotizacion_item_uuid=item.uuid,
                    )
                )

        uuids_a_eliminar = set(existentes.keys()) - uuids_entrantes
        if uuids_a_eliminar:
            ItemPresupuestoProyecto.objects.filter(
                proyecto=proyecto, cotizacion_item_uuid__in=uuids_a_eliminar
            ).delete()
        if a_crear:
            ItemPresupuestoProyecto.objects.bulk_create(a_crear)
        if a_actualizar:
            ItemPresupuestoProyecto.objects.bulk_update(
                a_actualizar, ["categoria", "descripcion", "cantidad", "valor_unitario", "subtotal"]
            )

        manuales_preservados = ItemPresupuestoProyecto.objects.filter(
            proyecto=proyecto,
            empresa_id=empresa.id,
            origen=ItemPresupuestoProyecto.Origen.MANUAL,
        ).count()

        PresupuestoBusinessService._recalcular_proyecto(proyecto)

        return {
            "cotizacion_uuid": str(cotizacion.uuid),
            "items_creados": len(a_crear),
            "items_actualizados": len(a_actualizar),
            "items_eliminados": len(uuids_a_eliminar),
            "items_manuales_preservados": manuales_preservados,
        }
