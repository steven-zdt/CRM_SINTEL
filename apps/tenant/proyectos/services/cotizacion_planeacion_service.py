"""
ProyectoCotizacionPlaneacionService (PLAN_PROYECTOS_FASE_2_COTIZACION_
RECURSOS_PRESUPUESTO, Fase 36): unica capa de orquestacion del caso de uso
"Proyecto -> Fase 2 Planeacion -> Cotizacion aceptada -> Recursos y
Presupuesto". Centraliza vincular/desvincular/consultar-resumen/sincronizar
-- el ViewSet, el serializer y el JavaScript delegan aqui, nunca
reimplementan estas reglas (Fase 36: "No repartir estas reglas entre
ViewSet/Serializer/JavaScript/Template").

Retorna tuplas (ok: bool, resultado, status_code), mismo patron ya usado
por ProjectOrderAssignmentService (apps/tenant/compras/services/
project_assignment_service.py) para dar codigos HTTP granulares sin
reimplementar ese contrato.
"""

import logging
from decimal import Decimal

from django.db import transaction

from ..models import ItemPresupuestoProyecto, Proyecto
from .crud_service import save_proyecto

logger = logging.getLogger(__name__)

_TWO = Decimal("0.01")

# Fase 6 del plan: SSoT del mapeo CotizacionItem.tipo_item -> categoria de
# ItemPresupuestoProyecto. El cuerpo real de CotizacionItem (PRODUCTO/
# MATERIAL/SERVICIO) no tiene todavia un tipo MANO_OBRA -- este mapeo
# funcional es la unica fuente de verdad, reutilizada por el resumen de
# recursos (obtener_resumen_cotizacion) Y por la sincronizacion
# (PresupuestoBusinessService.sincronizar_desde_cotizacion) -- nunca
# duplicado en JavaScript/template/ViewSet (Fase 6: "Esta regla debe
# centralizarse").
_MAPA_TIPO_ITEM_A_RECURSO = {
    "PRODUCTO": ItemPresupuestoProyecto.Categoria.EQUIPOS,
    "MATERIAL": ItemPresupuestoProyecto.Categoria.MATERIALES,
    "SERVICIO": ItemPresupuestoProyecto.Categoria.MANO_OBRA,
}


def mapear_tipo_item_a_recurso(tipo_item: str) -> str:
    """SSoT Fase 6 del plan -- unico lugar que conoce este mapeo."""
    try:
        return _MAPA_TIPO_ITEM_A_RECURSO[tipo_item]
    except KeyError as exc:
        raise ValueError(
            f"Tipo de item de cotizacion sin mapeo de recursos conocido: {tipo_item!r}"
        ) from exc


def _q(value) -> Decimal:
    return (value or Decimal("0.00")).quantize(_TWO)


class ProyectoCotizacionPlaneacionService:
    """Orquestacion del vinculo Proyecto <-> Cotizacion y su sincronizacion
    con el Presupuesto Planeado (Fase 2 del ciclo de vida del Proyecto)."""

    @staticmethod
    @transaction.atomic
    def vincular_cotizacion(
        *, proyecto, cotizacion_uuid, empresa_id, request=None, confirmar_reemplazo=False
    ):
        """
        Reglas aplicadas (Fase 3/9/17/19 del plan):
          1. Cotizacion existe y pertenece a `empresa_id` (DSV).
          2. Alcance organizacional (sede) cuando la Cotizacion tenga sede.
          3. Cliente compatible si el Proyecto ya tiene cliente asignado.
          4. Solo Cotizacion.Estado.APROBADA (SSoT real -- el plan la llama
             "ACEPTADA" conceptualmente, pero el estado real del modelo tras
             COTIZACIONES-02 es APROBADA; no se crea un estado duplicado).
          5. Idempotente si ya esta vinculada a ESTE proyecto.
          6. Nunca deja una Cotizacion como principal de 2 proyectos (unique
             a nivel de BD en Proyecto.cotizacion es la red de seguridad;
             aqui se valida antes para dar un mensaje claro).
          7. Reemplazar una cotizacion ya vinculada requiere
             `confirmar_reemplazo=True` explicito (Fase 19: "no silenciosamente").
        """
        from apps.tenant.cotizaciones.models import Cotizacion

        if not cotizacion_uuid:
            return (
                False,
                {"error": "missing_cotizacion_uuid", "message": "cotizacion_uuid es requerido."},
                400,
            )

        # [FIX] select_related('cliente')/('sede') + select_for_update() en
        # la misma consulta falla en Postgres ("FOR UPDATE cannot be applied
        # to the nullable side of an outer join") porque ambas son FK
        # nullable -> LEFT OUTER JOIN -- mismo hallazgo que
        # ProjectOrderAssignmentService.asociar_orden_a_proyecto()
        # (apps/tenant/compras/services/project_assignment_service.py). Se
        # bloquea solo Cotizacion (sin joins); `cliente_id`/`sede_id` ya
        # estan en la fila bloqueada, no hace falta el objeto relacionado
        # completo para las validaciones de abajo.
        cotizacion = (
            Cotizacion.objects.select_for_update()
            .filter(uuid=cotizacion_uuid, empresa_id=empresa_id)
            .first()
        )
        if not cotizacion:
            return (
                False,
                {
                    "error": "cotizacion_no_encontrada",
                    "message": "La cotizacion no existe o no pertenece a la empresa.",
                },
                404,
            )

        if request is not None and cotizacion.sede_id:
            from apps.tenant.core.services.organizational_scope import sede_esta_en_alcance

            if not sede_esta_en_alcance(cotizacion.sede_id, request):
                return (
                    False,
                    {
                        "error": "fuera_de_alcance",
                        "message": (
                            "No tiene permiso para vincular esta cotizacion "
                            "(fuera de su alcance organizacional)."
                        ),
                    },
                    403,
                )

        if proyecto.cliente_id and cotizacion.cliente_id and proyecto.cliente_id != cotizacion.cliente_id:
            return (
                False,
                {
                    "error": "cliente_incompatible",
                    "message": (
                        "El cliente de la cotizacion no coincide con el cliente ya "
                        "asignado a este proyecto."
                    ),
                },
                422,
            )

        if cotizacion.estado != Cotizacion.Estado.APROBADA:
            return (
                False,
                {
                    "error": "estado_invalido",
                    "message": (
                        f"Solo se pueden vincular cotizaciones en estado APROBADA "
                        f"(estado actual: {cotizacion.estado})."
                    ),
                },
                422,
            )

        # Regla E (idempotencia): ya vinculada a ESTE proyecto -> no-op exitoso.
        if proyecto.cotizacion_id == cotizacion.id:
            return True, proyecto, 200

        # Nunca sobrescribir silenciosamente la cotizacion de OTRO proyecto.
        otro_proyecto = (
            Proyecto.objects.filter(cotizacion_id=cotizacion.id).exclude(pk=proyecto.pk).first()
        )
        if otro_proyecto:
            return (
                False,
                {
                    "error": "cotizacion_ya_vinculada_otro_proyecto",
                    "message": (
                        f"Esta cotizacion ya esta vinculada como cotizacion principal "
                        f"del proyecto '{otro_proyecto.nombre}'."
                    ),
                },
                409,
            )

        # Fase 19: reemplazar una cotizacion ya vinculada en ESTE proyecto
        # requiere confirmacion explicita.
        if proyecto.cotizacion_id and not confirmar_reemplazo:
            cotizacion_actual = proyecto.cotizacion
            return (
                False,
                {
                    "error": "requiere_confirmacion_reemplazo",
                    "message": (
                        f"Este proyecto ya posee la cotizacion vinculada "
                        f"'{cotizacion_actual.numero_cotizacion}'. Los costos sincronizados "
                        f"actualmente pertenecen a esa cotizacion. Reenvie con "
                        f"confirmar_reemplazo=true para reemplazarla."
                    ),
                    "cotizacion_actual_uuid": str(cotizacion_actual.uuid),
                    "cotizacion_actual_numero": cotizacion_actual.numero_cotizacion,
                },
                409,
            )

        proyecto.cotizacion = cotizacion
        save_proyecto(proyecto, update_fields=["cotizacion", "updated_at"])
        logger.info(
            "[ProyectoCotizacionPlaneacion] Proyecto id=%s vinculado a Cotizacion id=%s",
            proyecto.id,
            cotizacion.id,
        )
        return True, proyecto, 200

    @staticmethod
    @transaction.atomic
    def desvincular_cotizacion(*, proyecto):
        """
        Fase 18 del plan: retira UNICAMENTE el vinculo. Nunca borra la
        Cotizacion, nunca borra items de presupuesto origen=COTIZACION --
        quedan como historico (siguen filtrables/visibles por `origen` y
        `cotizacion_item_uuid`, aunque ya no haya cotizacion activa que los
        respalde).
        """
        if not proyecto.cotizacion_id:
            return (
                False,
                {
                    "error": "sin_cotizacion",
                    "message": "Este proyecto no tiene una cotizacion vinculada.",
                },
                404,
            )

        proyecto.cotizacion = None
        save_proyecto(proyecto, update_fields=["cotizacion", "updated_at"])
        logger.info("[ProyectoCotizacionPlaneacion] Proyecto id=%s desvinculado de cotizacion", proyecto.id)
        return True, proyecto, 200

    @staticmethod
    def obtener_resumen_cotizacion(proyecto):
        """
        Fase 5/7/8/9 del plan: resumen de recursos (Mano de Obra/Materiales/
        Equipos) por "Valor cotizado antes de IVA" (cantidad x
        precio_unitario_venta, = CotizacionItem.subtotal_linea ya calculado
        por CotizacionItemBusinessService) y "Costo base antes de IVA"
        (cantidad x costo_unitario, calculado aqui). Nunca usa
        total_con_impuestos ni aplica IVA (Fase 7/27).

        Retorna None si el proyecto no tiene cotizacion vinculada (estado
        "Sin cotizacion" de la UI, Fase 21).
        """
        if not proyecto.cotizacion_id:
            return None

        from apps.tenant.cotizaciones.models import Cotizacion, CotizacionItem

        cotizacion = (
            Cotizacion.objects.filter(pk=proyecto.cotizacion_id, empresa_id=proyecto.empresa_id)
            .select_related("cliente")
            .only(
                "id",
                "uuid",
                "numero_cotizacion",
                "estado",
                "fecha_emision",
                "cliente_id",
                "cliente__razon_social",
                "porcentaje_aiu_admin",
                "porcentaje_aiu_imprevistos",
                "porcentaje_aiu_utilidad",
                "empresa_id",
            )
            .first()
        )
        if not cotizacion:
            return None

        items = list(
            CotizacionItem.objects.filter(cotizacion_id=cotizacion.id, empresa_id=proyecto.empresa_id)
            .only(
                "id",
                "uuid",
                "tipo_item",
                "descripcion",
                "cantidad",
                "costo_unitario",
                "precio_unitario_venta",
                "subtotal_linea",
                "orden",
            )
            .order_by("orden")
        )

        recursos = {
            ItemPresupuestoProyecto.Categoria.MANO_OBRA: {
                "cotizado": Decimal("0.00"),
                "costo_base": Decimal("0.00"),
            },
            ItemPresupuestoProyecto.Categoria.MATERIALES: {
                "cotizado": Decimal("0.00"),
                "costo_base": Decimal("0.00"),
            },
            ItemPresupuestoProyecto.Categoria.EQUIPOS: {
                "cotizado": Decimal("0.00"),
                "costo_base": Decimal("0.00"),
            },
        }
        items_detalle = []
        for item in items:
            recurso = mapear_tipo_item_a_recurso(item.tipo_item)
            cantidad = item.cantidad or Decimal("0.00")
            costo_unitario = item.costo_unitario or Decimal("0.00")
            costo_base_linea = cantidad * costo_unitario
            cotizado_linea = item.subtotal_linea or Decimal("0.00")

            recursos[recurso]["cotizado"] += cotizado_linea
            recursos[recurso]["costo_base"] += costo_base_linea

            items_detalle.append(
                {
                    "cotizacion_item_uuid": str(item.uuid),
                    "recurso": recurso,
                    "descripcion": item.descripcion or "",
                    "cantidad": str(cantidad),
                    "costo_unitario": str(_q(costo_unitario)),
                    "costo_base_linea": str(_q(costo_base_linea)),
                    "precio_unitario_venta": str(_q(item.precio_unitario_venta)),
                    "cotizado_linea": str(_q(cotizado_linea)),
                }
            )

        total_cotizado_items = sum((v["cotizado"] for v in recursos.values()), Decimal("0.00"))
        total_costo_base = sum((v["costo_base"] for v in recursos.values()), Decimal("0.00"))

        # "Valor cotizado antes de IVA" a nivel de cabecera (Fase 8/26 UI):
        # subtotal de items + AIU (administracion/imprevistos/utilidad),
        # SIN IVA -- misma formula que CotizacionService.calcular_totales()
        # usa para `base_iva`, sin duplicar ese calculo (se deriva aqui
        # porque Cotizacion no persiste `base_iva` como campo propio).
        pct_aiu_total = (
            (cotizacion.porcentaje_aiu_admin or Decimal("0.00"))
            + (cotizacion.porcentaje_aiu_imprevistos or Decimal("0.00"))
            + (cotizacion.porcentaje_aiu_utilidad or Decimal("0.00"))
        )
        aiu_total = total_cotizado_items * (pct_aiu_total / Decimal("100.00"))
        valor_antes_iva = total_cotizado_items + aiu_total

        return {
            "cotizacion": {
                "uuid": str(cotizacion.uuid),
                "numero": cotizacion.numero_cotizacion,
                "estado": cotizacion.estado,
                "cliente": cotizacion.cliente.razon_social if cotizacion.cliente_id else None,
                "fecha_emision": cotizacion.fecha_emision.isoformat()
                if cotizacion.fecha_emision
                else None,
                "valor_antes_iva": str(_q(valor_antes_iva)),
            },
            "resumen": {
                "mano_obra": {
                    "cotizado": str(_q(recursos[ItemPresupuestoProyecto.Categoria.MANO_OBRA]["cotizado"])),
                    "costo_base": str(
                        _q(recursos[ItemPresupuestoProyecto.Categoria.MANO_OBRA]["costo_base"])
                    ),
                },
                "materiales": {
                    "cotizado": str(_q(recursos[ItemPresupuestoProyecto.Categoria.MATERIALES]["cotizado"])),
                    "costo_base": str(
                        _q(recursos[ItemPresupuestoProyecto.Categoria.MATERIALES]["costo_base"])
                    ),
                },
                "equipos": {
                    "cotizado": str(_q(recursos[ItemPresupuestoProyecto.Categoria.EQUIPOS]["cotizado"])),
                    "costo_base": str(_q(recursos[ItemPresupuestoProyecto.Categoria.EQUIPOS]["costo_base"])),
                },
                "total_cotizado_items": str(_q(total_cotizado_items)),
                "total_costo_base": str(_q(total_costo_base)),
            },
            "items": items_detalle,
        }

    @staticmethod
    @transaction.atomic
    def sincronizar_costos(*, proyecto, empresa):
        """
        Fase 16/25 del plan: accion explicita (nunca automatica al vincular,
        Fase 11). Bloqueada en fase CIERRE (Fase 25) y si la cotizacion ya
        no esta APROBADA (pudo cambiar de estado despues de vincularse,
        aunque Fase 26 la trata como terminal/inmutable en la practica).
        """
        from apps.tenant.cotizaciones.models import Cotizacion

        from .presupuesto_service import PresupuestoBusinessService

        if not proyecto.cotizacion_id:
            return (
                False,
                {
                    "error": "sin_cotizacion",
                    "message": "Este proyecto no tiene una cotizacion vinculada.",
                },
                404,
            )

        if proyecto.fase_actual == "CIERRE":
            return (
                False,
                {
                    "error": "fase_cierre",
                    "message": "No se pueden sincronizar costos de una cotizacion en fase Cierre.",
                },
                422,
            )

        cotizacion = Cotizacion.objects.filter(
            pk=proyecto.cotizacion_id, empresa_id=empresa.id
        ).first()
        if not cotizacion or cotizacion.estado != Cotizacion.Estado.APROBADA:
            estado_actual = cotizacion.estado if cotizacion else "desconocido"
            return (
                False,
                {
                    "error": "cotizacion_invalida",
                    "message": (
                        f"La cotizacion vinculada ya no esta en estado APROBADA "
                        f"(estado actual: {estado_actual})."
                    ),
                },
                422,
            )

        resultado = PresupuestoBusinessService.sincronizar_desde_cotizacion(
            empresa=empresa, proyecto=proyecto, cotizacion=cotizacion
        )
        resultado["resumen"] = ProyectoCotizacionPlaneacionService.obtener_resumen_cotizacion(
            proyecto
        )["resumen"]
        return True, resultado, 200
