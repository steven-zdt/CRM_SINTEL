"""
ProjectOrderAssignmentService (PLAN_INTEGRACION_PROYECTOS_ORDENES_COMPRA_
VENTA_OPCIONAL.md, Fase 1): unica implementacion de la regla de negocio que
incorpora una OrdenCompra APROBADA a un Proyecto en fase BORRADOR.

Vive en Compras (no en Proyectos) porque OrdenCompra.proyecto es su FK -- la
direccion de dependencia real siempre es compras -> proyectos, nunca al
reves (Proyecto permanece Zero-Coupling, sin FK hacia OrdenCompra). Tanto la
UI de Proyecto ("Agregar Orden de Compra") como cualquier otro consumidor
futuro desde Compras deben llamar a este mismo servicio -- nunca
reimplementar estas reglas en otro lugar (#12.3 del plan: "evitar doble
fuente de verdad").
"""

import logging

from django.db import transaction

from apps.tenant.compras.models import OrdenCompra

logger = logging.getLogger(__name__)

ESTADO_REQUERIDO_PARA_ASOCIAR = "APROBADA"
FASE_REQUERIDA_PARA_ASOCIAR = "BORRADOR"


class ProjectOrderAssignmentService:
    """Logica de negocio para `Proyecto -> Compras -> Agregar Orden de
    Compra` (Reglas A-G, Seccion 3.1 del plan)."""

    @staticmethod
    @transaction.atomic
    def asociar_orden_a_proyecto(*, orden_uuid, proyecto_uuid, empresa_id, request=None):
        """
        Orquesta la asociacion. Devuelve (ok: bool, resultado, status_code).

        Orden de validacion (select_for_update sobre la Orden serializa
        asociaciones concurrentes sobre la misma fila):
          1. Orden y Proyecto existen y pertenecen a `empresa_id` (Regla C).
          2. Regla D: la Orden esta dentro del alcance organizacional
             (sede/area) de quien hace la peticion, si se provee `request`.
          3. Regla E: idempotente si la Orden ya esta asociada a ESTE Proyecto.
          4. Regla F: rechazada (nunca sobrescrita silenciosamente) si la
             Orden ya pertenece a OTRO Proyecto.
          5. Regla A: la Orden debe estar en estado APROBADA.
          6. Regla B: el Proyecto debe estar en fase BORRADOR.
        """
        from apps.tenant.proyectos.models import Proyecto

        # [FIX] select_related('proyecto') + select_for_update() en la misma
        # consulta falla en Postgres ("FOR UPDATE cannot be applied to the
        # nullable side of an outer join") porque `proyecto` es nullable ->
        # LEFT OUTER JOIN. Se bloquea solo OrdenCompra (sin el join) y, si
        # hace falta el nombre del proyecto actual (Regla F, mensaje de
        # error), se resuelve aparte mas abajo.
        orden = (
            OrdenCompra.objects.select_for_update()
            .filter(uuid=orden_uuid, empresa_id=empresa_id)
            .first()
        )
        if not orden:
            return (
                False,
                {
                    "error": "orden_no_encontrada",
                    "message": "La orden de compra no existe o no pertenece a la empresa.",
                },
                404,
            )

        proyecto = (
            Proyecto.objects.filter(uuid=proyecto_uuid, empresa_id=empresa_id)
            .only("id", "uuid", "empresa_id", "fase_actual", "nombre")
            .first()
        )
        if not proyecto:
            return (
                False,
                {
                    "error": "proyecto_no_encontrado",
                    "message": "El proyecto no existe o no pertenece a la empresa.",
                },
                404,
            )

        # Regla D: alcance organizacional (mismo criterio OSF ya usado por
        # OrdenCompraServiceMixin.get_qs_list() -- sin scope resoluble, se
        # degrada a "sin restriccion", nunca a "todo bloqueado").
        if request is not None:
            from apps.tenant.core.services.organizational_scope import (
                OrganizationalScope,
                OrganizationalScopeError,
            )

            try:
                scope = OrganizationalScope.resolve(request)
                sede_ids, area_ids = scope.sede_ids, scope.area_ids
            except OrganizationalScopeError:
                sede_ids, area_ids = None, None

            fuera_de_alcance = (sede_ids is not None and orden.sede_id not in sede_ids) or (
                area_ids is not None and orden.area_id is not None and orden.area_id not in area_ids
            )
            if fuera_de_alcance:
                return (
                    False,
                    {
                        "error": "fuera_de_alcance",
                        "message": (
                            "No tiene permiso para asociar esta orden de compra "
                            "(fuera de su alcance organizacional)."
                        ),
                    },
                    403,
                )

        # Regla E: idempotencia -- ya asociada a ESTE proyecto, no-op exitoso.
        if orden.proyecto_id == proyecto.id:
            return True, orden, 200

        # Regla F: nunca sobrescribir silenciosamente el proyecto de otra Orden.
        if orden.proyecto_id is not None:
            proyecto_actual = Proyecto.objects.filter(pk=orden.proyecto_id).only("nombre").first()
            nombre_actual = proyecto_actual.nombre if proyecto_actual else orden.proyecto_id
            return (
                False,
                {
                    "error": "orden_ya_asociada",
                    "message": (
                        f"Esta orden de compra ya esta asociada al proyecto "
                        f"'{nombre_actual}'. No se puede reasignar desde este flujo."
                    ),
                },
                409,
            )

        # Regla A: solo Ordenes APROBADA.
        if orden.estado != ESTADO_REQUERIDO_PARA_ASOCIAR:
            return (
                False,
                {
                    "error": "estado_invalido",
                    "message": (
                        f"Solo se pueden asociar ordenes de compra en estado "
                        f"'{ESTADO_REQUERIDO_PARA_ASOCIAR}' (estado actual: '{orden.estado}')."
                    ),
                },
                422,
            )

        # Regla B: el Proyecto debe estar en BORRADOR.
        if proyecto.fase_actual != FASE_REQUERIDA_PARA_ASOCIAR:
            return (
                False,
                {
                    "error": "fase_invalida",
                    "message": (
                        f"Solo se pueden asociar ordenes de compra mientras el proyecto esta en "
                        f"'{FASE_REQUERIDA_PARA_ASOCIAR}' (fase actual: '{proyecto.fase_actual}')."
                    ),
                },
                422,
            )

        orden.proyecto = proyecto
        orden.save(update_fields=["proyecto", "updated_at"])
        logger.info(
            "[ProjectOrderAssignmentService] Orden id=%s asociada a Proyecto id=%s",
            orden.id,
            proyecto.id,
        )
        return True, orden, 200
