import logging
import uuid as uuid_lib
from decimal import Decimal
from typing import Any

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.tenant.compras.models import PlantillaOrdenCompra
from apps.tenant.compras.requisiciones.models import (
    RequisicionCompra,
    RequisicionCotizacion,
    RequisicionDocumento,
    RequisicionFactura,
)
from apps.tenant.compras.requisiciones.services.crud_service import RequisicionCompraCRUDService
from apps.tenant.compras.services.business_service import OrdenCompraBusinessService

logger = logging.getLogger(__name__)


class RequisicionCompraBusinessService:
    """
    Logica de negocio para Requisiciones de Compra: maquina de estados,
    DSV, y orquestacion de la generacion de OrdenCompra a partir de una
    requisicion APROBADA. Ver docs/compras/REQUISICIONES_DESIGN.md.
    """

    # Ver docs/compras/REQUISICIONES_DESIGN.md #4. EN_PROCESO_COMPRA/
    # PARCIALMENTE_ATENDIDA/ATENDIDA son derivados por recalcular_estado(),
    # nunca disparados manualmente por el usuario -- por eso no aparecen
    # como destino de una transicion "manual" salvo el self-loop.
    TRANSICIONES_VALIDAS = {
        "BORRADOR": {"BORRADOR", "PENDIENTE_APROBACION", "CANCELADA"},
        "PENDIENTE_APROBACION": {"PENDIENTE_APROBACION", "APROBADA", "RECHAZADA"},
        "APROBADA": {"APROBADA", "EN_PROCESO_COMPRA", "CANCELADA"},
        "EN_PROCESO_COMPRA": {
            "EN_PROCESO_COMPRA",
            "PARCIALMENTE_ATENDIDA",
            "ATENDIDA",
            "CANCELADA",
        },
        "PARCIALMENTE_ATENDIDA": {"PARCIALMENTE_ATENDIDA", "ATENDIDA", "CANCELADA"},
        "ATENDIDA": {"ATENDIDA"},
        "RECHAZADA": {"RECHAZADA"},
        "CANCELADA": {"CANCELADA"},
    }

    ESTADOS_CON_ORDENES_PERMITIDAS = {"APROBADA", "EN_PROCESO_COMPRA", "PARCIALMENTE_ATENDIDA"}

    @staticmethod
    def _obtener_entidad_por_id_o_uuid(model_class, lookup_value, empresa_id: int):
        """Mismo helper DSV anti-IDOR que OrdenCompraBusinessService (cada
        business_service de este proyecto lo mantiene autocontenido -- ver
        arquitectura Zero-Coupling de apps.tenant.proyectos.models)."""
        if not lookup_value:
            return None
        if isinstance(lookup_value, model_class):
            if getattr(lookup_value, "empresa_id", None) == empresa_id:
                return lookup_value
            return None
        if isinstance(lookup_value, uuid_lib.UUID):
            return model_class.objects.filter(uuid=lookup_value, empresa_id=empresa_id).first()

        is_uuid = False
        if isinstance(lookup_value, str) and len(lookup_value) >= 32:
            try:
                uuid_lib.UUID(str(lookup_value))
                is_uuid = True
            except (ValueError, TypeError):
                pass

        if is_uuid:
            return model_class.objects.filter(uuid=lookup_value, empresa_id=empresa_id).first()
        try:
            return model_class.objects.filter(id=int(lookup_value), empresa_id=empresa_id).first()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _validar_y_reservar_cotizacion(cotizacion, cliente=None):
        """PLAN_NUEVA_REQUISICION_FORMULARIO.md #2/#3: helper COMPARTIDO
        entre `crear_requisicion()` y `vincular_cotizacion()` -- una sola
        implementacion de la regla, nunca duplicada.

        #2 Exclusividad: una Cotizacion ya vinculada a CUALQUIER Requisicion
        (propia o ajena) deja de estar disponible. Se revalida con
        `select_for_update()` -- nunca basta con que el frontend ya la haya
        excluido de la busqueda, dos usuarios pueden seleccionarla casi
        simultaneamente. Debe invocarse dentro de un bloque
        @transaction.atomic.

        #3 Coherencia de Cliente: si la Cotizacion tiene Cliente propio
        (campo opcional, `cotizaciones/models.py:93`) y difiere del Cliente
        de la Requisicion, se bloquea -- nunca se reasigna el Cliente de la
        Requisicion automaticamente (la fuente de verdad es el Cliente
        elegido en Informacion General).

        Lanza ValidationError con mensaje de negocio (nunca un
        IntegrityError crudo) -- el caller lo deja propagar hasta el
        `except ValidationError` de mas afuera."""
        from apps.tenant.cotizaciones.models import Cotizacion

        cotizacion = Cotizacion.objects.select_for_update().get(pk=cotizacion.pk)
        if cotizacion.requisiciones_vinculadas.exists():
            raise ValidationError(
                {"cotizacion": "La cotización ya está asociada a otra requisición."}
            )
        if cliente is not None and cotizacion.cliente_id and cotizacion.cliente_id != cliente.id:
            raise ValidationError(
                {
                    "cotizacion": "La cotización seleccionada pertenece a un cliente diferente al cliente de la requisición."
                }
            )
        return cotizacion

    # ==================================================================
    # CRUD orquestado (DSV)
    # ==================================================================

    @staticmethod
    @transaction.atomic
    def crear_requisicion(
        data: dict, items_data: list, empresa: Any, sede: Any, solicitante: Any
    ) -> tuple[bool, Any, int]:
        """Orquesta la creacion de una RequisicionCompra. `sede` y
        `solicitante` son parametros explicitos (ADR-003 / mismo criterio
        que OrdenCompraBusinessService.crear_orden_compra) -- nunca
        re-derivados dentro de esta capa.

        Decision explicita del usuario (2026-09-26): la Cotizacion de origen
        pasa a ser OBLIGATORIA al crear -- ya no es solo trazabilidad
        opcional (contrasta con vincular_cotizacion(), que sigue existiendo
        para vincular cotizaciones ADICIONALES despues de creada). Se valida
        y se vincula (RequisicionCotizacion, tipo_relacion='ORIGEN',
        es_principal=True) dentro de la misma transaccion atomica que la
        creacion: si la cotizacion no es valida, no se crea nada."""
        try:
            if sede is None:
                return (
                    False,
                    {
                        "error": "sede_requerida",
                        "message": "No hay ninguna Sede activa para esta empresa.",
                    },
                    422,
                )
            if getattr(sede, "empresa_id", None) != empresa.id:
                return (
                    False,
                    {
                        "error": "sede_invalida",
                        "message": "La sede activa no pertenece a la empresa actual.",
                    },
                    422,
                )
            if solicitante is None:
                return (
                    False,
                    {
                        "error": "solicitante_requerido",
                        "message": "No se pudo determinar el perfil del usuario solicitante.",
                    },
                    422,
                )

            data = dict(data)
            data["solicitante"] = solicitante

            # DSV: Plantilla de Numeracion (OBLIGATORIA -- PLAN_NUEVA_
            # REQUISICION_NUMERACION_CLIENTE_COTIZACIONES.md Fase B). La
            # resolucion/DSV de la plantilla y la asignacion atomica del
            # consecutivo son UNA sola operacion en
            # OrdenCompraBusinessService._dsv_y_asignar_plantilla() (motor
            # compartido con OrdenCompra, select_for_update + F()+1) --
            # nunca se separan en dos pasos.
            plantilla_raw = data.pop("plantilla", None) or data.pop("plantilla_uuid", None)
            if not plantilla_raw:
                return (
                    False,
                    {
                        "error": "plantilla_requerida",
                        "message": "Debe seleccionar la plantilla de numeracion de esta requisicion.",
                    },
                    422,
                )
            plantilla, numero_documento, consecutivo = (
                OrdenCompraBusinessService._dsv_y_asignar_plantilla(
                    empresa.id,
                    plantilla_raw,
                    tipo_documento_esperado=PlantillaOrdenCompra.TipoDocumento.REQUISICION,
                )
            )
            data["plantilla"] = plantilla
            data["numero_documento"] = numero_documento
            data["consecutivo"] = consecutivo

            # DSV: Cliente (OBLIGATORIO -- Fase C del mismo plan). FK real
            # (nunca snapshot), mismo helper DSV que el resto de esta
            # funcion.
            from apps.tenant.clientes.models import Cliente

            cliente_raw = data.pop("cliente", None) or data.pop("cliente_uuid", None)
            if not cliente_raw:
                return (
                    False,
                    {
                        "error": "cliente_requerido",
                        "message": "Debe seleccionar el cliente de esta requisicion.",
                    },
                    422,
                )
            cliente = RequisicionCompraBusinessService._obtener_entidad_por_id_o_uuid(
                Cliente, cliente_raw, empresa.id
            )
            if not cliente:
                return (
                    False,
                    {
                        "error": "cliente_invalido",
                        "message": "El cliente especificado no es valido o no pertenece a la empresa.",
                    },
                    400,
                )
            data["cliente"] = cliente

            # DSV: Cotizaciones (0..N, ninguna obligatoria -- PLAN_NUEVA_
            # REQUISICION_FORMULARIO.md #1, revierte la decision del
            # 2026-09-26 "cotizacion de origen obligatoria"). Cada una se
            # revalida con select_for_update() + coherencia de Cliente via
            # el helper compartido con vincular_cotizacion() (#2/#3 del
            # mismo documento) -- se resuelven y validan ANTES de crear la
            # Requisicion (fail fast, nunca queda una Requisicion creada
            # con una cotizacion invalida a medias).
            from apps.tenant.cotizaciones.models import Cotizacion

            cotizaciones_raw = data.pop("cotizaciones", None) or []
            cotizaciones_validadas = []
            for cotizacion_raw in cotizaciones_raw:
                cot = RequisicionCompraBusinessService._obtener_entidad_por_id_o_uuid(
                    Cotizacion, cotizacion_raw, empresa.id
                )
                if not cot:
                    return (
                        False,
                        {
                            "error": "cotizacion_invalida",
                            "message": f"La cotización {cotizacion_raw} no es válida o no pertenece a la empresa.",
                        },
                        400,
                    )
                cot = RequisicionCompraBusinessService._validar_y_reservar_cotizacion(cot, cliente)
                cotizaciones_validadas.append(cot)

            # DSV: Area (opcional, misma regla sede/area que Compras)
            area_raw = data.get("area") or data.get("area_uuid")
            if area_raw:
                from apps.tenant.empresa.models import Area

                area = RequisicionCompraBusinessService._obtener_entidad_por_id_o_uuid(
                    Area, area_raw, empresa.id
                )
                if not area:
                    return (
                        False,
                        {
                            "error": "area_invalida",
                            "message": "El area especificada no es valida o no pertenece a la empresa.",
                        },
                        400,
                    )
                if area.sede_id != sede.id:
                    return (
                        False,
                        {
                            "error": "area_invalida",
                            "message": "El area especificada no pertenece a la sede de esta requisicion.",
                        },
                        400,
                    )
                data.pop("area_uuid", None)
                data["area"] = area
            else:
                data.pop("area_uuid", None)
                data["area"] = None

            # DSV: Proyecto (opcional)
            proyecto_raw = data.get("proyecto") or data.get("proyecto_uuid")
            if proyecto_raw:
                from apps.tenant.proyectos.models import Proyecto

                proyecto = RequisicionCompraBusinessService._obtener_entidad_por_id_o_uuid(
                    Proyecto, proyecto_raw, empresa.id
                )
                if not proyecto:
                    return (
                        False,
                        {
                            "error": "proyecto_invalido",
                            "message": "El proyecto especificado no es valido o no pertenece a la empresa.",
                        },
                        400,
                    )
                data.pop("proyecto_uuid", None)
                data["proyecto"] = proyecto
            else:
                data.pop("proyecto_uuid", None)
                data["proyecto"] = None

            # DSV: Responsable de Aprobacion (opcional)
            from apps.tenant.perfil.models import TenantProfile

            resp_raw = data.get("responsable_aprobacion") or data.get("responsable_aprobacion_uuid")
            if resp_raw:
                responsable = RequisicionCompraBusinessService._obtener_entidad_por_id_o_uuid(
                    TenantProfile, resp_raw, empresa.id
                )
                if not responsable:
                    return (
                        False,
                        {
                            "error": "responsable_invalido",
                            "message": "El responsable de aprobacion especificado no es valido.",
                        },
                        400,
                    )
                data.pop("responsable_aprobacion_uuid", None)
                data["responsable_aprobacion"] = responsable
            else:
                data.pop("responsable_aprobacion_uuid", None)
                data["responsable_aprobacion"] = None

            requisicion = RequisicionCompraCRUDService.crear_requisicion(
                data, items_data, empresa, sede
            )

            # La primera cotizacion vinculada con exito queda tipo_relacion=
            # 'ORIGEN' (compatibilidad con el snapshot de Aprobaciones y
            # `cotizacion_origen_numero` del serializer, ambos fuera de
            # alcance de este plan) -- el resto 'CONTEXTO'. Si no se
            # vinculo ninguna, no hay ORIGEN (ya manejado por esos lectores
            # con `.first()` -> None).
            for idx, cot in enumerate(cotizaciones_validadas):
                RequisicionCotizacion.objects.create(
                    empresa_id=empresa.id,
                    requisicion=requisicion,
                    cotizacion=cot,
                    tipo_relacion="ORIGEN" if idx == 0 else "CONTEXTO",
                    es_principal=(idx == 0),
                )

            # Hallazgo real (2026-09-25, pedido explicito del usuario): si la
            # requisicion nace con un Proyecto, se intenta encontrar y
            # vincular automaticamente su Cotizacion/Factura de origen
            # (trazabilidad de solo lectura, ver
            # _sincronizar_trazabilidad_desde_proyecto) -- best-effort,
            # nunca bloquea la creacion de la requisicion si no se
            # encuentra nada o si algo falla en la resolucion.
            if requisicion.proyecto_id:
                try:
                    RequisicionCompraBusinessService._sincronizar_trazabilidad_desde_proyecto(
                        requisicion
                    )
                except Exception as exc:
                    logger.warning(
                        "[RequisicionBS] No se pudo sincronizar trazabilidad desde proyecto para requisicion id=%s: %s",
                        requisicion.id,
                        exc,
                    )

            return True, requisicion, 201
        except ValidationError as e:
            return False, e.detail, 400
        except Exception as e:
            logger.error(f"Error en crear_requisicion: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500

    @staticmethod
    @transaction.atomic
    def actualizar_requisicion(
        requisicion_uuid: str, data: dict, items_data: list, empresa_id: int
    ) -> tuple[bool, Any, int]:
        try:
            requisicion = RequisicionCompra.objects.filter(
                uuid=requisicion_uuid, empresa_id=empresa_id
            ).first()
            if not requisicion:
                return (
                    False,
                    {"error": "requisicion_no_encontrada", "message": "La requisicion no existe."},
                    404,
                )

            data = dict(data)
            if "proyecto" in data or "proyecto_uuid" in data:
                proyecto_raw = data.get("proyecto") or data.get("proyecto_uuid")
                if proyecto_raw:
                    from apps.tenant.proyectos.models import Proyecto

                    proyecto = RequisicionCompraBusinessService._obtener_entidad_por_id_o_uuid(
                        Proyecto, proyecto_raw, empresa_id
                    )
                    if not proyecto:
                        return (
                            False,
                            {
                                "error": "proyecto_invalido",
                                "message": "El proyecto especificado no es valido.",
                            },
                            400,
                        )
                    data.pop("proyecto_uuid", None)
                    data["proyecto"] = proyecto
                else:
                    data.pop("proyecto_uuid", None)
                    data["proyecto"] = None

            # Cliente: editable en BORRADOR (documento original #13), pero a
            # diferencia de Proyecto es OBLIGATORIO -- nunca se acepta
            # vaciarlo via PATCH, solo reemplazarlo por otro Cliente valido.
            if "cliente" in data or "cliente_uuid" in data:
                cliente_raw = data.get("cliente") or data.get("cliente_uuid")
                if not cliente_raw:
                    return (
                        False,
                        {
                            "error": "cliente_requerido",
                            "message": "El cliente es obligatorio, no se puede dejar vacio.",
                        },
                        422,
                    )
                from apps.tenant.clientes.models import Cliente

                cliente = RequisicionCompraBusinessService._obtener_entidad_por_id_o_uuid(
                    Cliente, cliente_raw, empresa_id
                )
                if not cliente:
                    return (
                        False,
                        {
                            "error": "cliente_invalido",
                            "message": "El cliente especificado no es valido o no pertenece a la empresa.",
                        },
                        400,
                    )
                data.pop("cliente_uuid", None)
                data["cliente"] = cliente

            requisicion = RequisicionCompraCRUDService.actualizar_requisicion(
                requisicion, data, items_data
            )
            return True, requisicion, 200
        except ValidationError as e:
            return False, e.detail, 400
        except Exception as e:
            logger.error(f"Error en actualizar_requisicion: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500

    @staticmethod
    def eliminar_requisicion(requisicion_uuid: str, empresa_id: int) -> tuple[bool, Any, int]:
        try:
            requisicion = RequisicionCompra.objects.filter(
                uuid=requisicion_uuid, empresa_id=empresa_id
            ).first()
            if not requisicion:
                return (
                    False,
                    {"error": "requisicion_no_encontrada", "message": "La requisicion no existe."},
                    404,
                )
            RequisicionCompraCRUDService.eliminar_requisicion(requisicion)
            return True, None, 204
        except ValidationError as e:
            return False, {"detail": str(e)}, 400
        except Exception as e:
            logger.error(f"Error en eliminar_requisicion: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500

    # ==================================================================
    # Maquina de estados
    # ==================================================================

    @staticmethod
    @transaction.atomic
    def _transicionar(
        requisicion_uuid: str,
        empresa_id: int,
        nuevo_estado: str,
        *,
        usuario=None,
        comentario: str = "",
    ) -> tuple[bool, Any, int]:
        requisicion = (
            RequisicionCompra.objects.select_for_update()
            .filter(uuid=requisicion_uuid, empresa_id=empresa_id)
            .first()
        )
        if not requisicion:
            return (
                False,
                {"error": "requisicion_no_encontrada", "message": "La requisicion no existe."},
                404,
            )

        actual = requisicion.estado
        if nuevo_estado == actual:
            return True, requisicion, 200

        permitidos = RequisicionCompraBusinessService.TRANSICIONES_VALIDAS.get(actual, set())
        if nuevo_estado not in permitidos:
            return (
                False,
                {
                    "error": "transicion_invalida",
                    "message": f"No se puede pasar de '{actual}' a '{nuevo_estado}'. Transiciones validas: {sorted(permitidos) or 'ninguna'}.",
                },
                400,
            )

        requisicion = RequisicionCompraCRUDService.cambiar_estado(
            requisicion,
            nuevo_estado,
            usuario=usuario,
            comentario=comentario,
        )
        return True, requisicion, 200

    @staticmethod
    @transaction.atomic
    def enviar_a_aprobacion(
        requisicion_uuid: str, empresa_id: int, usuario=None
    ) -> tuple[bool, Any, int]:
        """Fase 5 de PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md (#11):
        BORRADOR -> Enviar -> PENDIENTE_APROBACION -> SolicitudAprobacion=
        PENDIENTE -> (Dashboard, Fase 7/8, DEFERRED). La creacion de la
        SolicitudAprobacion vive en la misma transaccion que la transicion
        de estado -- nunca debe quedar una requisicion en
        PENDIENTE_APROBACION sin su solicitud correspondiente."""
        requisicion = RequisicionCompra.objects.filter(
            uuid=requisicion_uuid, empresa_id=empresa_id
        ).first()
        if not requisicion:
            return (
                False,
                {"error": "requisicion_no_encontrada", "message": "La requisicion no existe."},
                404,
            )
        if not (requisicion.justificacion or "").strip():
            return (
                False,
                {
                    "error": "justificacion_requerida",
                    "message": "La justificacion es obligatoria para enviar la requisicion a aprobacion.",
                },
                422,
            )

        ok, result, status_code = RequisicionCompraBusinessService._transicionar(
            requisicion_uuid,
            empresa_id,
            RequisicionCompra.Estado.PENDIENTE_APROBACION,
            usuario=usuario,
        )
        if not ok:
            return ok, result, status_code
        requisicion = result

        from apps.tenant.approvals.models import SolicitudAprobacion
        from apps.tenant.approvals.services.business_service import ApprovalBusinessService

        ok_sol, solicitud_o_error, status_sol = ApprovalBusinessService.crear_solicitud(
            tipo_documento=SolicitudAprobacion.TipoDocumento.REQUISICION,
            objeto_uuid=requisicion.uuid,
            empresa_id=empresa_id,
            solicitante=usuario or requisicion.solicitante,
        )
        if not ok_sol:
            # Nunca dejar la requisicion en PENDIENTE_APROBACION sin su
            # solicitud -- se propaga el error y la transaccion completa
            # (transicion + intento de solicitud) hace rollback.
            raise ValidationError({"solicitud_aprobacion": solicitud_o_error})

        return True, requisicion, status_code

    @staticmethod
    def _cerrar_solicitud_aprobacion_si_existe(
        requisicion, nuevo_estado: str, usuario, observacion: str = ""
    ):
        """Fase 5 (#26/#28 del plan): si esta requisicion tiene una
        SolicitudAprobacion PENDIENTE (creada por enviar_a_aprobacion()), se
        cierra aqui mismo -- sin importar si la transicion la disparo el
        endpoint directo de Requisiciones (actual) o un futuro Centro de
        Aprobaciones via ApprovalBusinessService.aprobar()/rechazar() (que
        llega hasta aqui de todos modos, ver ese servicio). Import local
        (Requisiciones -> Approvals, nunca al reves) -- si la app Approvals
        no esta disponible por alguna razon, no bloquea la transicion real
        del dominio (best-effort, igual criterio que
        _sincronizar_trazabilidad_desde_proyecto)."""
        try:
            from apps.tenant.approvals.models import (
                SolicitudAprobacion,
                SolicitudAprobacionHistorial,
            )
            from apps.tenant.approvals.services.crud_service import SolicitudAprobacionCRUDService

            solicitud = (
                SolicitudAprobacion.objects.select_for_update()
                .filter(
                    empresa_id=requisicion.empresa_id,
                    tipo_documento=SolicitudAprobacion.TipoDocumento.REQUISICION,
                    objeto_uuid=requisicion.uuid,
                    estado=SolicitudAprobacion.Estado.PENDIENTE,
                )
                .first()
            )
            if solicitud:
                evento = (
                    SolicitudAprobacionHistorial.Evento.APROBADA
                    if nuevo_estado == SolicitudAprobacion.Estado.APROBADA
                    else SolicitudAprobacionHistorial.Evento.RECHAZADA
                )
                SolicitudAprobacionCRUDService.cambiar_estado(
                    solicitud,
                    nuevo_estado,
                    evento=evento,
                    usuario=usuario,
                    observacion=observacion,
                )
        except Exception as exc:
            logger.warning(
                "[RequisicionBS] No se pudo cerrar la SolicitudAprobacion de la requisicion id=%s: %s",
                requisicion.id,
                exc,
            )

    @staticmethod
    @transaction.atomic
    def aprobar_requisicion(
        requisicion_uuid: str, empresa_id: int, usuario=None, comentario: str = ""
    ) -> tuple[bool, Any, int]:
        success, result, status_code = RequisicionCompraBusinessService._transicionar(
            requisicion_uuid,
            empresa_id,
            RequisicionCompra.Estado.APROBADA,
            usuario=usuario,
            comentario=comentario,
        )
        if not success:
            return success, result, status_code
        # Por defecto, cantidad_aprobada = cantidad_solicitada (design #5) --
        # salvo que ya se haya ajustado explicitamente antes de aprobar.
        for item in result.items.all():
            if item.cantidad_aprobada == Decimal("0.00"):
                item.cantidad_aprobada = item.cantidad_solicitada
                item.save(update_fields=["cantidad_aprobada"])
        RequisicionCompraBusinessService._cerrar_solicitud_aprobacion_si_existe(
            result,
            "APROBADA",
            usuario,
            comentario,
        )
        return True, result, 200

    @staticmethod
    @transaction.atomic
    def rechazar_requisicion(
        requisicion_uuid: str, empresa_id: int, motivo: str, usuario=None
    ) -> tuple[bool, Any, int]:
        if not (motivo or "").strip():
            return (
                False,
                {"error": "motivo_requerido", "message": "Debe indicar el motivo de rechazo."},
                422,
            )
        success, result, status_code = RequisicionCompraBusinessService._transicionar(
            requisicion_uuid,
            empresa_id,
            RequisicionCompra.Estado.RECHAZADA,
            usuario=usuario,
            comentario=motivo,
        )
        if not success:
            return success, result, status_code
        RequisicionCompraBusinessService._cerrar_solicitud_aprobacion_si_existe(
            result,
            "RECHAZADA",
            usuario,
            motivo,
        )
        return True, result, status_code

    @staticmethod
    def cancelar_requisicion(
        requisicion_uuid: str, empresa_id: int, motivo: str = "", usuario=None
    ) -> tuple[bool, Any, int]:
        return RequisicionCompraBusinessService._transicionar(
            requisicion_uuid,
            empresa_id,
            RequisicionCompra.Estado.CANCELADA,
            usuario=usuario,
            comentario=motivo,
        )

    # ==================================================================
    # Vinculos de trazabilidad (Cotizacion/Factura)
    # ==================================================================

    @staticmethod
    @transaction.atomic
    def vincular_cotizacion(
        requisicion_uuid: str,
        cotizacion_uuid: str,
        empresa_id: int,
        *,
        tipo_relacion: str = "CONTEXTO",
        es_principal: bool = False,
        observacion: str = "",
    ) -> tuple[bool, Any, int]:
        requisicion = RequisicionCompra.objects.filter(
            uuid=requisicion_uuid, empresa_id=empresa_id
        ).first()
        if not requisicion:
            return (
                False,
                {"error": "requisicion_no_encontrada", "message": "La requisicion no existe."},
                404,
            )

        from apps.tenant.cotizaciones.models import Cotizacion

        cotizacion = RequisicionCompraBusinessService._obtener_entidad_por_id_o_uuid(
            Cotizacion, cotizacion_uuid, empresa_id
        )
        if not cotizacion:
            return (
                False,
                {
                    "error": "cotizacion_invalida",
                    "message": "La cotizacion especificada no es valida o no pertenece a la empresa.",
                },
                400,
            )

        # PLAN_NUEVA_REQUISICION_FORMULARIO.md #2/#3: mismo helper
        # compartido que crear_requisicion() -- exclusividad +
        # coherencia de Cliente, revalidadas aqui tambien (esta accion es
        # el unico camino para vincular cotizaciones DESPUES de creada la
        # Requisicion, ya sea desde el detalle o desde el widget de
        # "Vincular Cotización" del formulario de creacion, que la llama
        # en diferido tras el POST inicial).
        cotizacion = RequisicionCompraBusinessService._validar_y_reservar_cotizacion(
            cotizacion, requisicion.cliente
        )

        vinculo, _created = RequisicionCotizacion.objects.get_or_create(
            empresa_id=empresa_id,
            requisicion=requisicion,
            cotizacion=cotizacion,
            defaults={
                "tipo_relacion": tipo_relacion,
                "es_principal": es_principal,
                "observacion": observacion,
            },
        )
        return True, vinculo, 201

    @staticmethod
    def vincular_factura(
        requisicion_uuid: str,
        factura_uuid: str,
        empresa_id: int,
        *,
        tipo_relacion: str = "EVIDENCIA",
        es_principal: bool = False,
        observacion: str = "",
    ) -> tuple[bool, Any, int]:
        requisicion = RequisicionCompra.objects.filter(
            uuid=requisicion_uuid, empresa_id=empresa_id
        ).first()
        if not requisicion:
            return (
                False,
                {"error": "requisicion_no_encontrada", "message": "La requisicion no existe."},
                404,
            )

        from apps.tenant.facturas.models import Factura

        factura = RequisicionCompraBusinessService._obtener_entidad_por_id_o_uuid(
            Factura, factura_uuid, empresa_id
        )
        if not factura:
            return (
                False,
                {
                    "error": "factura_invalida",
                    "message": "La factura especificada no es valida o no pertenece a la empresa.",
                },
                400,
            )

        vinculo, _created = RequisicionFactura.objects.get_or_create(
            empresa_id=empresa_id,
            requisicion=requisicion,
            factura=factura,
            defaults={
                "tipo_relacion": tipo_relacion,
                "es_principal": es_principal,
                "observacion": observacion,
            },
        )
        return True, vinculo, 201

    # ==================================================================
    # Trazabilidad automatica desde Proyecto (pedido explicito del usuario,
    # 2026-09-25): dado el Proyecto de una Requisicion, resuelve y vincula
    # (solo lectura/trazabilidad, nunca reinterpretacion de negocio) la
    # Cotizacion y Factura reales de origen, usando UNICAMENTE mecanismos
    # ya existentes -- Proyecto es Zero-Coupling (sin FK a Cotizaciones,
    # ver docstring de CotizacionService.convertir_a_proyecto()) asi que la
    # unica forma real de encontrar su Cotizacion de origen es el mismo
    # codigo determinista que ese metodo ya genera: "PRJ-COT-<codigo>".
    # ==================================================================

    @staticmethod
    def _resolver_cotizacion_desde_proyecto(proyecto) -> Any:
        """Devuelve la Cotizacion real que origino este Proyecto, o None si
        no aplica (proyecto no viene de una conversion de Cotizacion, o la
        Cotizacion ya no existe). Nunca inventa una relacion -- si el
        codigo no sigue el patron esperado, retorna None sin error."""
        from apps.tenant.cotizaciones.models import Cotizacion

        codigo = proyecto.codigo or ""
        prefijo = "PRJ-COT-"
        if not codigo.startswith(prefijo):
            return None
        identificador = codigo[len(prefijo) :]
        if not identificador:
            return None

        # convertir_a_proyecto() usa codigo_unico si existe, si no
        # numero_cotizacion -- se prueban ambos, en ese mismo orden.
        return (
            Cotizacion.objects.filter(
                empresa_id=proyecto.empresa_id, codigo_unico=identificador
            ).first()
            or Cotizacion.objects.filter(
                empresa_id=proyecto.empresa_id, numero_cotizacion=identificador
            ).first()
        )

    @staticmethod
    def _resolver_factura_desde_proyecto(proyecto, cotizacion) -> Any:
        """Resuelve la Factura real asociada, en orden de confiabilidad:
        1. Proyecto.factura_costo (FK real y directa, ya existente en el
           dominio Proyectos).
        2. Si hay Cotizacion resuelta y esta fue convertida a Venta
           (Venta.cotizacion_uuid), la Factura asociada a esa Venta
           (Venta.factura_asociada, mismo patron que OrdenCompra.
           factura_asociada). Ninguno de los 2 caminos es inventado -- son
           campos reales que ya existen en Proyectos/Ventas."""
        if proyecto.factura_costo_id:
            return proyecto.factura_costo

        if not cotizacion:
            return None

        from apps.tenant.ventas.models import Venta

        venta = (
            Venta.objects.filter(empresa_id=proyecto.empresa_id, cotizacion_uuid=cotizacion.uuid)
            .exclude(factura_asociada=None)
            .select_related("factura_asociada")
            .first()
        )
        return venta.factura_asociada if venta else None

    @staticmethod
    @transaction.atomic
    def _sincronizar_trazabilidad_desde_proyecto(requisicion: RequisicionCompra) -> dict:
        """Resuelve y vincula (idempotente, via get_or_create -- mismo
        criterio que vincular_cotizacion()/vincular_factura()) la
        Cotizacion/Factura de origen del Proyecto de esta requisicion.
        Retorna {'cotizacion': bool, 'factura': bool} indicando que se
        encontro/vinculo. No falla si no encuentra nada -- ausencia de
        trazabilidad es un resultado valido, no un error."""
        resultado = {"cotizacion": False, "factura": False}
        if not requisicion.proyecto_id:
            return resultado

        proyecto = requisicion.proyecto
        cotizacion = RequisicionCompraBusinessService._resolver_cotizacion_desde_proyecto(proyecto)
        if cotizacion:
            RequisicionCotizacion.objects.get_or_create(
                empresa_id=requisicion.empresa_id,
                requisicion=requisicion,
                cotizacion=cotizacion,
                defaults={
                    "tipo_relacion": "ORIGEN_PROYECTO",
                    "es_principal": True,
                    "observacion": "Vinculada automaticamente desde el Proyecto de la requisicion.",
                },
            )
            resultado["cotizacion"] = True

        factura = RequisicionCompraBusinessService._resolver_factura_desde_proyecto(
            proyecto, cotizacion
        )
        if factura:
            RequisicionFactura.objects.get_or_create(
                empresa_id=requisicion.empresa_id,
                requisicion=requisicion,
                factura=factura,
                defaults={
                    "tipo_relacion": "ORIGEN_PROYECTO",
                    "es_principal": True,
                    "observacion": "Vinculada automaticamente desde el Proyecto de la requisicion.",
                },
            )
            resultado["factura"] = True

        return resultado

    @staticmethod
    def sincronizar_trazabilidad_proyecto(
        requisicion_uuid: str, empresa_id: int
    ) -> tuple[bool, Any, int]:
        """Entrada publica (API) para re-disparar la sincronizacion
        manualmente -- util si el Proyecto se asigna/cambia despues de
        creada la requisicion, o si la Factura/Venta aparece mas tarde."""
        requisicion = (
            RequisicionCompra.objects.select_related("proyecto")
            .filter(
                uuid=requisicion_uuid,
                empresa_id=empresa_id,
            )
            .first()
        )
        if not requisicion:
            return (
                False,
                {"error": "requisicion_no_encontrada", "message": "La requisicion no existe."},
                404,
            )
        if not requisicion.proyecto_id:
            return (
                False,
                {
                    "error": "sin_proyecto",
                    "message": "Esta requisicion no tiene un proyecto asignado.",
                },
                422,
            )

        resultado = RequisicionCompraBusinessService._sincronizar_trazabilidad_desde_proyecto(
            requisicion
        )
        return True, resultado, 200

    # ==================================================================
    # Generacion de OrdenCompra desde una Requisicion
    # ==================================================================

    @staticmethod
    @transaction.atomic
    def crear_orden_desde_requisicion(
        requisicion_uuid: str,
        oc_data: dict,
        items_ordenados: list,
        empresa: Any,
        sede: Any,
        empresa_id: int,
    ) -> tuple[bool, Any, int]:
        """
        Pseudoflujo (plan original #20): resuelve requisicion -> verifica
        empresa/estado -> valida cantidades disponibles -> delega la
        creacion real de la OrdenCompra a OrdenCompraBusinessService (nunca
        duplica su logica DSV de plantilla/proveedor) -> acumula
        cantidad_ordenada en los items de la requisicion -> recalcula estado.

        `items_ordenados`: lista de {requisicion_item_uuid, cantidad,
        valor_unitario (opcional, default = valor_unitario_estimado),
        porcentaje_iva (opcional, default = el del item)}.
        """
        requisicion = (
            RequisicionCompra.objects.select_for_update()
            .filter(uuid=requisicion_uuid, empresa_id=empresa_id)
            .first()
        )
        if not requisicion:
            return (
                False,
                {"error": "requisicion_no_encontrada", "message": "La requisicion no existe."},
                404,
            )

        if (
            requisicion.estado
            not in RequisicionCompraBusinessService.ESTADOS_CON_ORDENES_PERMITIDAS
        ):
            return (
                False,
                {
                    "error": "requisicion_no_disponible",
                    "message": f"No se pueden generar ordenes desde una requisicion en estado {requisicion.estado}.",
                },
                422,
            )

        oc_items_data = []
        items_a_acumular = []
        for linea in items_ordenados:
            req_item = (
                requisicion.items.select_for_update()
                .filter(uuid=linea["requisicion_item_uuid"])
                .first()
            )
            if not req_item:
                return (
                    False,
                    {
                        "error": "item_invalido",
                        "message": f"El item {linea.get('requisicion_item_uuid')} no pertenece a esta requisicion.",
                    },
                    400,
                )

            cantidad = Decimal(str(linea["cantidad"]))
            if cantidad <= 0:
                return (
                    False,
                    {
                        "error": "cantidad_invalida",
                        "message": "La cantidad a ordenar debe ser mayor a cero.",
                    },
                    400,
                )
            if cantidad > req_item.cantidad_pendiente:
                return (
                    False,
                    {
                        "error": "cantidad_excede_pendiente",
                        "message": f"El item '{req_item.descripcion}' solo tiene {req_item.cantidad_pendiente} pendiente por ordenar.",
                    },
                    422,
                )

            oc_items_data.append(
                {
                    "descripcion": req_item.descripcion,
                    "item_inventario_uuid": req_item.item_inventario_uuid,
                    "requisicion_item_uuid": req_item.uuid,
                    "cantidad": cantidad,
                    "valor_unitario": linea.get("valor_unitario", req_item.valor_unitario_estimado),
                    "porcentaje_iva": linea.get("porcentaje_iva", req_item.porcentaje_iva),
                }
            )
            items_a_acumular.append((req_item, cantidad))

        if not oc_items_data:
            return (
                False,
                {"error": "sin_items", "message": "Debe indicar al menos un item a ordenar."},
                400,
            )

        from apps.tenant.compras.services.business_service import OrdenCompraBusinessService

        oc_data = dict(oc_data)
        oc_data["requisiciones"] = [requisicion.uuid]
        success, orden_o_error, status_code = OrdenCompraBusinessService.crear_orden_compra(
            oc_data,
            oc_items_data,
            empresa,
            sede,
        )
        if not success:
            return False, orden_o_error, status_code

        for req_item, cantidad in items_a_acumular:
            RequisicionCompraCRUDService.acumular_cantidad_ordenada(req_item, cantidad)

        if requisicion.estado == RequisicionCompra.Estado.APROBADA:
            requisicion = RequisicionCompraCRUDService.cambiar_estado(
                requisicion,
                RequisicionCompra.Estado.EN_PROCESO_COMPRA,
                comentario="Primera orden de compra generada.",
            )

        RequisicionCompraBusinessService.recalcular_estado(requisicion)
        return True, orden_o_error, status_code

    @staticmethod
    @transaction.atomic
    def recalcular_estado(requisicion: RequisicionCompra) -> RequisicionCompra:
        """Deriva EN_PROCESO_COMPRA/PARCIALMENTE_ATENDIDA/ATENDIDA a partir
        del agregado real de items -- nunca disparado manualmente por el
        usuario (design #4/#10)."""
        if (
            requisicion.estado
            not in RequisicionCompraBusinessService.ESTADOS_CON_ORDENES_PERMITIDAS
        ):
            return requisicion

        items = list(requisicion.items.all())
        if not items:
            return requisicion

        todos_atendidos = all(
            (item.cantidad_ordenada + item.cantidad_cancelada) >= item.cantidad_aprobada
            for item in items
        )
        algo_ordenado = any(item.cantidad_ordenada > 0 for item in items)

        if todos_atendidos:
            nuevo_estado = RequisicionCompra.Estado.ATENDIDA
        elif algo_ordenado:
            nuevo_estado = RequisicionCompra.Estado.PARCIALMENTE_ATENDIDA
        else:
            nuevo_estado = requisicion.estado

        if nuevo_estado != requisicion.estado:
            requisicion = RequisicionCompraCRUDService.cambiar_estado(
                requisicion,
                nuevo_estado,
                comentario="Recalculo automatico por atencion de items.",
            )
        return requisicion

    # ==================================================================
    # Documentos adjuntos
    # ==================================================================

    @staticmethod
    def adjuntar_documento(
        requisicion_uuid: str, empresa_id: int, data: dict
    ) -> tuple[bool, Any, int]:
        requisicion = RequisicionCompra.objects.filter(
            uuid=requisicion_uuid, empresa_id=empresa_id
        ).first()
        if not requisicion:
            return (
                False,
                {"error": "requisicion_no_encontrada", "message": "La requisicion no existe."},
                404,
            )

        documento = RequisicionDocumento.objects.create(
            empresa_id=empresa_id,
            requisicion=requisicion,
            tipo=data.get("tipo"),
            nombre=data.get("nombre"),
            numero_referencia=data.get("numero_referencia", ""),
            documento_uuid=data.get("documento_uuid"),
            archivo=data.get("archivo"),
            descripcion=data.get("descripcion", ""),
        )
        return True, documento, 201
