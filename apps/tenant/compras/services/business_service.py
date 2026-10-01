import logging
import uuid as uuid_lib
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.tenant.compras.models import (
    ItemOrdenCompra,
    OrdenCompra,
    PlantillaOrdenCompra,
    RecepcionCompra,
)
from apps.tenant.compras.services.crud_service import (
    OrdenCompraCRUDService,
    RecepcionCompraCRUDService,
)

logger = logging.getLogger(__name__)


class OrdenCompraBusinessService:
    """
    Logica de negocio para Ordenes de Compra.
    Realiza la Double Semantic Verification (DSV) y orquesta transacciones.
    """

    # REM P1-01 (docs/remediation/REM-P1-01.md): OrdenCompraCRUDService.
    # cambiar_estado() solo validaba que el estado destino existiera en
    # ESTADO_CHOICES, nunca que la transicion desde el estado actual fuera
    # valida -- permitia saltos arbitrarios (ej. RECIBIDA -> BORRADOR).
    #
    # Diseño basado en evidencia real, no asumido: test_sincronizacion_
    # cuentas_pagar.py (existente) confirma 2 comportamientos reales que la
    # primera version de esta matriz rompia por asumir un flujo lineal
    # BORRADOR->PENDIENTE->APROBADA que el codigo real no impone:
    #   1. BORRADOR->APROBADA directo es un flujo legitimo y probado
    #      ("Decision explicita del usuario: el trigger es la transicion a
    #      estado APROBADA" -- comentario del propio archivo de test).
    #   2. Re-aplicar el MISMO estado (ej. APROBADA->APROBADA) debe ser un
    #      no-op idempotente (test_reaprobar_es_idempotente_no_duplica), no
    #      un error de transicion invalida.
    # Por eso cada estado se permite a si mismo (self-loop). PARCIAL/RECIBIDA
    # nunca se alcanzan por esta via manual (los asigna
    # RecepcionCompraBusinessService.confirmar_recepcion() -- ver
    # business_service.py:596,598), asi que solo se permiten a si mismos
    # (no-op) -- una vez la orden entra en el flujo de recepcion,
    # cambiar_estado() manual no puede sacarla de ese flujo.
    TRANSICIONES_VALIDAS = {
        "BORRADOR": {"BORRADOR", "PENDIENTE", "APROBADA", "ANULADA"},
        "PENDIENTE": {"PENDIENTE", "APROBADA", "BORRADOR", "ANULADA"},
        "APROBADA": {"APROBADA", "ANULADA"},
        "PARCIAL": {"PARCIAL"},
        "RECIBIDA": {"RECIBIDA"},
        "ANULADA": {"ANULADA"},
    }

    @staticmethod
    def _obtener_entidad_por_id_o_uuid(model_class, lookup_value, empresa_id: int):
        """
        Helper para obtener un objeto de cualquier modelo tenant usando ID o UUID,
        aplicando filtrado por empresa_id para evitar IDOR.
        Soporta instancias del modelo, UUIDs y enteros.
        """
        if not lookup_value:
            return None

        # Si ya es una instancia del modelo, validar empresa_id y retornar
        if isinstance(lookup_value, model_class):
            if getattr(lookup_value, "empresa_id", None) == empresa_id:
                return lookup_value
            return None

        # Si es un objeto UUID directo
        if isinstance(lookup_value, uuid_lib.UUID):
            return model_class.objects.filter(uuid=lookup_value, empresa_id=empresa_id).first()

        # Verificar si es una cadena de texto representando un UUID valido
        is_uuid = False
        if isinstance(lookup_value, str) and len(lookup_value) >= 32:
            try:
                uuid_lib.UUID(str(lookup_value))
                is_uuid = True
            except (ValueError, TypeError):
                pass

        if is_uuid:
            return model_class.objects.filter(uuid=lookup_value, empresa_id=empresa_id).first()
        else:
            try:
                return model_class.objects.filter(
                    id=int(lookup_value), empresa_id=empresa_id
                ).first()
            except (ValueError, TypeError):
                return None

    @staticmethod
    def _dsv_y_asignar_plantilla(
        empresa_id: int, plantilla_raw: Any, tipo_documento_esperado: str = None
    ):
        """
        DSV + asignacion atomica del consecutivo de la PlantillaOrdenCompra.
        Usa select_for_update() para prevenir race conditions en entornos concurrentes.

        Debe invocarse dentro de un bloque @transaction.atomic.

        `tipo_documento_esperado` (PLAN_NUEVA_REQUISICION_NUMERACION_CLIENTE_
        COTIZACIONES.md Fase A/B): motor de numeracion COMPARTIDO entre
        OrdenCompra y RequisicionCompra -- `RequisicionCompraBusinessService`
        (apps/tenant/compras/requisiciones/services/business_service.py)
        llama a este mismo metodo pasando
        `tipo_documento_esperado=PlantillaOrdenCompra.TipoDocumento.REQUISICION`
        en vez de duplicar el algoritmo select_for_update()+F()+1. `None`
        (default, uso desde OrdenCompra) no valida el tipo -- mantiene el
        comportamiento previo a esta Fase intacto.

        Retorna: (plantilla_instance, numero_documento_str, consecutivo_int)
        """
        if isinstance(plantilla_raw, PlantillaOrdenCompra):
            plantilla_id = plantilla_raw.id
            plantilla = (
                PlantillaOrdenCompra.objects.select_for_update()
                .filter(id=plantilla_id, empresa_id=empresa_id)
                .first()
            )
        else:
            is_uuid = False
            if isinstance(plantilla_raw, uuid_lib.UUID):
                is_uuid = True
            elif isinstance(plantilla_raw, str) and len(plantilla_raw) >= 32:
                try:
                    uuid_lib.UUID(plantilla_raw)
                    is_uuid = True
                except (ValueError, TypeError):
                    pass

            if is_uuid:
                plantilla = (
                    PlantillaOrdenCompra.objects.select_for_update()
                    .filter(uuid=plantilla_raw, empresa_id=empresa_id)
                    .first()
                )
            else:
                try:
                    plantilla = (
                        PlantillaOrdenCompra.objects.select_for_update()
                        .filter(id=int(plantilla_raw), empresa_id=empresa_id)
                        .first()
                    )
                except (ValueError, TypeError):
                    plantilla = None

        if not plantilla:
            raise ValidationError(
                {
                    "plantilla": f"La plantilla {plantilla_raw} no fue encontrada o no pertenece a la empresa."
                }
            )
        if tipo_documento_esperado and plantilla.tipo_documento != tipo_documento_esperado:
            raise ValidationError(
                {
                    "plantilla": f"La plantilla {plantilla.nombre} es de tipo {plantilla.get_tipo_documento_display()}, no de {dict(PlantillaOrdenCompra.TipoDocumento.choices).get(tipo_documento_esperado, tipo_documento_esperado)}."
                }
            )
        if not plantilla.vigente:
            raise ValidationError(
                {"plantilla": f"La plantilla {plantilla.nombre} no esta marcada como vigente."}
            )
        if not plantilla.esta_en_rango():
            raise ValidationError(
                {
                    "plantilla": f"La plantilla {plantilla.nombre} ha agotado su rango de consecutivos ({plantilla.rango_desde}-{plantilla.rango_hasta})."
                }
            )

        consecutivo = plantilla.consecutivo_actual
        numero_documento = plantilla.formar_numero()

        # Incrementar consecutivo atomicamente (con select_for_update ya activo)
        PlantillaOrdenCompra.objects.filter(pk=plantilla.pk).update(
            consecutivo_actual=F("consecutivo_actual") + 1
        )

        logger.info(
            "[ComprasBS] Consecutivo asignado: %s (plantilla id=%s, siguiente=%s)",
            numero_documento,
            plantilla.id,
            consecutivo + 1,
        )
        return plantilla, numero_documento, consecutivo

    @staticmethod
    @transaction.atomic
    def crear_orden_compra(
        data: dict, items_data: list, empresa: Any, sede: Any
    ) -> tuple[bool, Any, int]:
        """
        Orquesta la creacion de una Orden de Compra.
        Aplica Double Semantic Verification (DSV) en Plantilla, Proveedor, Proyecto, Documento
        Soporte y Area (opcional). `sede` es un parametro explicito (ver ADR-003) - este metodo
        nunca la resuelve por su cuenta.
        """
        logger.info(
            f"[OrdenCompraBusinessService:crear_orden_compra] Iniciando proceso para empresa={empresa.id}"
        )
        try:
            if sede is None:
                return (
                    False,
                    {
                        "error": "sede_requerida",
                        "message": "No hay ninguna Sede activa para esta empresa. Cree al menos una Sede antes de registrar ordenes de compra.",
                    },
                    422,
                )
            if getattr(sede, "empresa_id", None) != empresa.id:
                # Anti-IDOR: la sede resuelta por el contexto debe pertenecer a la misma empresa.
                return (
                    False,
                    {
                        "error": "sede_invalida",
                        "message": "La sede activa no pertenece a la empresa actual.",
                    },
                    422,
                )

            # DSV: Area (opcional) - si viene, debe pertenecer a la misma
            # empresa Y a la misma Sede de la orden (F5, OSF: un Area
            # siempre cuelga de una Sede especifica - permitir un Area de
            # otra Sede dejaria la orden en un estado organizacionalmente
            # inconsistente, ej. alcance=AREA filtrando por una combinacion
            # sede/area que nunca puede coincidir con datos reales).
            area_raw = data.get("area") or data.get("area_uuid")
            if area_raw:
                from apps.tenant.empresa.models import Area

                area = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
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
                            "message": "El area especificada no pertenece a la sede de esta orden.",
                        },
                        400,
                    )
                data.pop("area_uuid", None)
                data["area"] = area
            else:
                data.pop("area_uuid", None)
                data["area"] = None

            # 1. DSV: Plantilla (Obligatorio)
            plantilla_raw = data.get("plantilla") or data.get("plantilla_uuid")
            if not plantilla_raw:
                raise ValidationError(
                    {"plantilla": "La plantilla de orden de compra es obligatoria."}
                )

            plantilla, numero_documento, consecutivo = (
                OrdenCompraBusinessService._dsv_y_asignar_plantilla(
                    empresa.id,
                    plantilla_raw,
                    tipo_documento_esperado=PlantillaOrdenCompra.TipoDocumento.ORDEN_COMPRA,
                )
            )
            # Remove UUID key if present to avoid conflicting arguments
            data.pop("plantilla_uuid", None)
            data["plantilla"] = plantilla
            data["numero_documento"] = numero_documento
            data["consecutivo"] = consecutivo

            # 2. DSV: Proveedor (Obligatorio)
            from apps.tenant.proveedores.models import Proveedor

            proveedor_raw = data.get("proveedor") or data.get("proveedor_uuid")
            proveedor = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                Proveedor, proveedor_raw, empresa.id
            )
            if not proveedor:
                return (
                    False,
                    {
                        "error": "proveedor_invalido",
                        "message": "El proveedor especificado no es valido.",
                    },
                    400,
                )
            data.pop("proveedor_uuid", None)
            data["proveedor"] = proveedor

            # 3. DSV: Proyecto (Opcional)
            proyecto_raw = data.get("proyecto") or data.get("proyecto_uuid")
            if proyecto_raw:
                from apps.tenant.proyectos.models import Proyecto

                proyecto = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
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

            # 4. DSV: Documento Soporte / Gasto (Opcional)
            doc_raw = data.get("documento_soporte") or data.get("documento_soporte_uuid")
            if doc_raw:
                from apps.tenant.gastos.models import DocumentoSoporte

                doc = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                    DocumentoSoporte, doc_raw, empresa.id
                )
                if not doc:
                    return (
                        False,
                        {
                            "error": "documento_invalido",
                            "message": "El documento soporte especificado no es valido o no pertenece a la empresa.",
                        },
                        400,
                    )
                data.pop("documento_soporte_uuid", None)
                data["documento_soporte"] = doc
            else:
                data.pop("documento_soporte_uuid", None)
                data["documento_soporte"] = None

            # 5. DSV: Requisiciones (N:N -- PLAN_CENTRO_APROBACIONES_
            # DASHBOARD_COMPRAS.md #3): toda Orden de Compra nueva DEBE
            # llevar >= 1 Requisicion. Sin excepcion posible (el escape
            # `es_excepcional` existio brevemente el 2026-09-26 y se retiro
            # el mismo dia: "la excepcion no debe seguir funcionando para
            # nuevas OC"). Nunca bypass por API/servicio alterno -- esta es
            # la unica via de creacion real (incluida
            # crear_orden_desde_requisicion(), que llama aqui mismo).
            from apps.tenant.compras.requisiciones.models import RequisicionCompra
            from apps.tenant.compras.requisiciones.services.selectors import (
                ESTADOS_DISPONIBLES_PARA_COMPRA,
            )
            from apps.tenant.compras.services.budget_control_service import (
                ProcurementBudgetControlService,
            )

            requisiciones_raw = data.pop("requisiciones", None) or []
            montos_explicitos = data.pop("montos_requisiciones", None) or {}

            if not requisiciones_raw:
                return (
                    False,
                    {
                        "error": "requisicion_requerida",
                        "message": "Toda Orden de Compra debe estar asociada a al menos una Requisicion.",
                    },
                    422,
                )

            requisiciones = []
            for req_raw in requisiciones_raw:
                requisicion = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                    RequisicionCompra, req_raw, empresa.id
                )
                if not requisicion:
                    return (
                        False,
                        {
                            "error": "requisicion_invalida",
                            "message": f"La requisicion '{req_raw}' no es valida o no pertenece a la empresa.",
                        },
                        400,
                    )
                if requisicion.estado not in ESTADOS_DISPONIBLES_PARA_COMPRA:
                    return (
                        False,
                        {
                            "error": "requisicion_no_disponible",
                            "message": f"La requisicion {requisicion.numero_documento} no esta en un estado disponible para generar ordenes (estado actual: {requisicion.estado}).",
                        },
                        422,
                    )
                requisiciones.append(requisicion)

            if len(set(r.id for r in requisiciones)) != len(requisiciones):
                return (
                    False,
                    {
                        "error": "requisiciones_duplicadas",
                        "message": "No se puede repetir la misma requisicion.",
                    },
                    400,
                )

            # Concurrencia (#25 del plan): re-lockear las filas de Requisicion
            # con select_for_update(), en orden deterministico por id (evita
            # deadlocks entre 2 transacciones concurrentes que consolidan las
            # mismas Requisiciones en distinto orden), ANTES de calcular
            # saldos/montos mas abajo. `_obtener_entidad_por_id_o_uuid()` NO
            # bloquea (es un simple .filter().first()) -- sin este re-fetch,
            # 2 OC creadas en paralelo contra la misma Requisicion podrian
            # ambas leer el mismo saldo "libre" y sobre-consumirlo (hallazgo
            # real de la autoauditoria Fase 13, corregido aqui).
            requisiciones_por_id = {
                r.id: r
                for r in RequisicionCompra.objects.select_for_update().filter(
                    id__in=[r.id for r in requisiciones],
                )
            }
            requisiciones = [requisiciones_por_id[r.id] for r in requisiciones]

            data.pop("requisicion", None)
            data.pop("requisicion_uuid", None)
            data.pop("es_excepcional", None)
            data.pop("motivo_excepcion", None)

            # 6. Crear la orden (sin persistir aun las requisiciones vinculadas
            # -- el total de la orden solo se conoce despues de que CRUD
            # calcula subtotal/impuestos/total a partir de items_data).
            orden = OrdenCompraCRUDService.crear_orden(data, items_data, empresa, sede)

            # 7. Control financiero (#17-25): reparte el total de la orden
            # entre las requisiciones (proporcional si no se especifico
            # explicito) y valida que ninguna exceda su saldo disponible
            # ANTES de persistir el vinculo N:N. Las filas ya estan
            # bloqueadas con select_for_update() (paso anterior).
            if montos_explicitos:
                montos = {r: Decimal(str(montos_explicitos[str(r.uuid)])) for r in requisiciones}
            else:
                montos = ProcurementBudgetControlService.repartir_monto_proporcional(
                    requisiciones, orden.total
                )

            ok_budget, mensaje_budget = ProcurementBudgetControlService.validar_consolidacion_oc(
                montos
            )
            if not ok_budget:
                raise ValidationError({"presupuesto": mensaje_budget})

            from apps.tenant.compras.models import OrdenCompraRequisicion

            OrdenCompraRequisicion.objects.bulk_create(
                [
                    OrdenCompraRequisicion(
                        empresa=empresa,
                        orden_compra=orden,
                        requisicion=requisicion,
                        monto_asignado=monto,
                    )
                    for requisicion, monto in montos.items()
                ]
            )

            return True, orden, 201

        except ValidationError as e:
            # Bug real encontrado en la autoauditoria de esta mision (2026-
            # 09-26): Django NO revierte automaticamente una transaction.
            # atomic() cuando la excepcion se captura DENTRO del mismo
            # metodo decorado -- solo revierte si la excepcion escapa del
            # bloque. Sin este set_rollback(True) explicito, la OrdenCompra
            # ya insertada arriba (antes de la validacion de presupuesto)
            # quedaba COMMITEADA huerfana pese a que el metodo devolvia
            # ok=False (verificado en vivo: `OrdenCompra.objects.count()`
            # daba 1 en vez de 0 tras un rechazo por presupuesto).
            transaction.set_rollback(True)
            return False, e.detail, 400
        except Exception as e:
            transaction.set_rollback(True)
            logger.error(f"Error en crear_orden_compra: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500

    @staticmethod
    @transaction.atomic
    def actualizar_orden_compra(
        orden_uuid: str, data: dict, items_data: list, empresa_id: int
    ) -> tuple[bool, Any, int]:
        """
        Orquesta la actualizacion de una Orden de Compra y sus items.
        """
        logger.info(f"[OrdenCompraBusinessService:actualizar_orden_compra] UUID={orden_uuid}")
        try:
            orden = OrdenCompra.objects.filter(uuid=orden_uuid, empresa_id=empresa_id).first()
            if not orden:
                return (
                    False,
                    {"error": "orden_no_encontrada", "message": "La orden de compra no existe."},
                    404,
                )

            # 1. DSV: Proveedor (Si viene en la peticion)
            if "proveedor" in data or "proveedor_uuid" in data:
                from apps.tenant.proveedores.models import Proveedor

                proveedor_raw = data.get("proveedor") or data.get("proveedor_uuid")
                proveedor = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                    Proveedor, proveedor_raw, empresa_id
                )
                if not proveedor:
                    return (
                        False,
                        {
                            "error": "proveedor_invalido",
                            "message": "El proveedor especificado no es valido.",
                        },
                        400,
                    )
                data.pop("proveedor_uuid", None)
                data["proveedor"] = proveedor

            # 2. DSV: Proyecto (Si viene en la peticion)
            if "proyecto" in data or "proyecto_uuid" in data:
                proyecto_raw = data.get("proyecto") or data.get("proyecto_uuid")
                if proyecto_raw:
                    from apps.tenant.proyectos.models import Proyecto

                    proyecto = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
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

            # 3. DSV: Documento Soporte (Si viene en la peticion)
            if "documento_soporte" in data or "documento_soporte_uuid" in data:
                doc_raw = data.get("documento_soporte") or data.get("documento_soporte_uuid")
                if doc_raw:
                    from apps.tenant.gastos.models import DocumentoSoporte

                    doc = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                        DocumentoSoporte, doc_raw, empresa_id
                    )
                    if not doc:
                        return (
                            False,
                            {
                                "error": "documento_invalido",
                                "message": "El documento soporte especificado no es valido.",
                            },
                            400,
                        )
                    data.pop("documento_soporte_uuid", None)
                    data["documento_soporte"] = doc
                else:
                    data.pop("documento_soporte_uuid", None)
                    data["documento_soporte"] = None

            # 4. DSV: Area (Si viene en la peticion) - [OSF Fase F5] Hallazgo
            # real: antes de esta fase 'area' nunca llegaba aqui (el
            # serializer no lo declaraba, ver OrdenCompraCreateUpdateSerializer),
            # asi que este bloque no existia - agregado simetrico a los de
            # arriba, con la misma regla de consistencia sede/area que
            # crear_orden_compra (un Area siempre pertenece a una Sede
            # especifica; la Sede de la orden es inmutable tras crearla).
            if "area" in data or "area_uuid" in data:
                area_raw = data.get("area") or data.get("area_uuid")
                if area_raw:
                    from apps.tenant.empresa.models import Area

                    area = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                        Area, area_raw, empresa_id
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
                    if area.sede_id != orden.sede_id:
                        return (
                            False,
                            {
                                "error": "area_invalida",
                                "message": "El area especificada no pertenece a la sede de esta orden.",
                            },
                            400,
                        )
                    data.pop("area_uuid", None)
                    data["area"] = area
                else:
                    data.pop("area_uuid", None)
                    data["area"] = None

            orden = OrdenCompraCRUDService.actualizar_orden(orden, data, items_data)
            return True, orden, 200

        except ValidationError as e:
            return False, e.detail, 400
        except Exception as e:
            logger.error(f"Error en actualizar_orden_compra: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500

    @staticmethod
    @transaction.atomic
    def cambiar_estado_orden_compra(
        orden_uuid: str, nuevo_estado: str, empresa_id: int
    ) -> tuple[bool, Any, int]:
        """
        Cambia el estado de una Orden de Compra.
        """
        try:
            orden = OrdenCompra.objects.filter(uuid=orden_uuid, empresa_id=empresa_id).first()
            if not orden:
                return (
                    False,
                    {"error": "orden_no_encontrada", "message": "La orden de compra no existe."},
                    404,
                )

            permitidos = OrdenCompraBusinessService.TRANSICIONES_VALIDAS.get(orden.estado, set())
            if nuevo_estado not in permitidos:
                return (
                    False,
                    {
                        "error": "transicion_invalida",
                        "message": (
                            f"No se puede pasar de '{orden.estado}' a '{nuevo_estado}'. "
                            f"Transiciones validas desde '{orden.estado}': {sorted(permitidos) or 'ninguna'}."
                        ),
                    },
                    400,
                )

            # REQUISICIONES N:N (PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md
            # #3): toda OrdenCompra real tiene >= 1 requisicion vinculada
            # (exigido en crear_orden_compra(), sin excepcion posible) --
            # todas deben estar APROBADA antes de aprobar la orden.
            if nuevo_estado == "APROBADA":
                requisiciones_no_aprobadas = [
                    vinculo.requisicion
                    for vinculo in orden.requisiciones_vinculadas.select_related(
                        "requisicion"
                    ).all()
                    if vinculo.requisicion.estado != "APROBADA"
                ]
                if requisiciones_no_aprobadas:
                    numeros = ", ".join(r.numero_documento for r in requisiciones_no_aprobadas)
                    return (
                        False,
                        {
                            "error": "requisicion_no_aprobada",
                            "message": f"Las siguientes requisiciones deben estar APROBADA antes de aprobar esta orden: {numeros}.",
                        },
                        422,
                    )

            orden = OrdenCompraCRUDService.cambiar_estado(orden, nuevo_estado)
            if nuevo_estado == "APROBADA":
                OrdenCompraBusinessService._sincronizar_cuenta_por_pagar(orden)
            return True, orden, 200
        except ValidationError as e:
            return False, e.detail, 400
        except Exception as e:
            logger.error(f"Error en cambiar_estado_orden_compra: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500

    @staticmethod
    def _sincronizar_cuenta_por_pagar(orden: OrdenCompra) -> None:
        """
        Bridge Compras -> Proveedores (import local dentro del metodo, mismo
        patron usado por RecepcionCompraBusinessService.confirmar_recepcion()
        para el bridge a Inventario). Genera/recupera la Cuenta por Pagar al
        aprobar la orden -- decision explicita: el punto de reconocimiento
        de la obligacion es APROBADA, no RECIBIDA ni la existencia de una
        Factura DIAN (muchas compras de este ERP nunca generan una factura
        electronica, solo quedan respaldadas por un DocumentoSoporte
        opcional o ninguno -- ver hallazgo real: 0 CuentasPagar existian en
        el tenant `home` pese a tener una OrdenCompra APROBADA/BORRADOR).

        Idempotente: CuentasPagarBusinessService.registrar_cuenta_pagar()
        hace get_or_create sobre (empresa, proveedor, numero_factura) -- una
        reaprobacion o reintento no duplica el registro.

        Fuera de alcance deliberado (mismo criterio que
        RecepcionCompraBusinessService.anular_recepcion): si la orden se
        anula despues de aprobada, la CxP ya generada NO se reversa aqui.
        """
        from apps.tenant.proveedores.services.business_service import CuentasPagarBusinessService

        numero = orden.numero_documento or f"OC-{orden.consecutivo}"
        fecha_vencimiento = orden.fecha + timedelta(days=orden.proveedor.plazo_pago_dias)

        CuentasPagarBusinessService.registrar_cuenta_pagar(
            proveedor=orden.proveedor,
            empresa_id=orden.empresa_id,
            datos_cuenta_pagar={
                "numero_factura": numero,
                "fecha_emision": orden.fecha,
                "fecha_vencimiento": fecha_vencimiento,
                "valor_total": orden.total,
                "observaciones": f"Generado automaticamente al aprobar Orden de Compra {numero}.",
                "orden_compra_uuid": orden.uuid,
                # PLAN_VINCULAR_FACTURA_COMPRA_COMPRAS Fase 20: si la Orden ya
                # tenia una Factura de compra vinculada antes de aprobarse, la
                # CxP nace con la trazabilidad completa desde el primer momento.
                "factura_uuid": orden.factura_asociada.uuid if orden.factura_asociada_id else None,
            },
        )

    @staticmethod
    @transaction.atomic
    def eliminar_orden_compra(orden_uuid: str, empresa_id: int) -> tuple[bool, Any, int]:
        """
        Elimina fisicamente una Orden de Compra si cumple las condiciones (estado Borrador).
        """
        try:
            orden = OrdenCompra.objects.filter(uuid=orden_uuid, empresa_id=empresa_id).first()
            if not orden:
                return (
                    False,
                    {"error": "orden_no_encontrada", "message": "La orden de compra no existe."},
                    404,
                )

            OrdenCompraCRUDService.eliminar_orden(orden)
            return True, {"message": "Orden de compra eliminada correctamente."}, 204
        except ValidationError as e:
            return False, e.detail, 400
        except Exception as e:
            logger.error(f"Error en eliminar_orden_compra: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500

    @staticmethod
    @transaction.atomic
    def vincular_factura_existente(
        orden_uuid: str, factura_uuid: str, empresa_id: int
    ) -> tuple[bool, Any, int]:
        """
        FACTURAS-UI-CRONO-01: vincula manualmente una Factura YA PERSISTIDA
        (naturaleza COMPRA) a esta Orden de Compra -- nunca crea ni emite
        ninguna Factura. Mismo patron de DSV que el resto de esta clase
        (uuid+empresa_id, `compras` no importa el modelo Factura a nivel
        de modulo -- import local, regla del Bridge).

        PLAN_VINCULAR_FACTURA_COMPRA_COMPRAS Fase 10/22: valida que el NIT
        emisor de la Factura coincida con el proveedor de la Orden (nunca
        vincula silenciosamente un documento de otro tercero) y usa
        select_for_update() sobre la Orden para que dos vinculaciones
        concurrentes sobre la misma Orden no puedan colarse ambas.
        """
        try:
            orden = (
                OrdenCompra.objects.select_for_update()
                .filter(
                    uuid=orden_uuid,
                    empresa_id=empresa_id,
                )
                .select_related("proveedor")
                .first()
            )
            if not orden:
                return (
                    False,
                    {"error": "orden_no_encontrada", "message": "La orden de compra no existe."},
                    404,
                )

            if not factura_uuid:
                return (
                    False,
                    {"error": "missing_factura_uuid", "message": "factura_uuid es requerido."},
                    400,
                )

            if orden.factura_asociada_id:
                return (
                    False,
                    {
                        "error": "orden_ya_vinculada",
                        "message": "Esta Orden de Compra ya tiene una Factura vinculada.",
                    },
                    409,
                )

            from apps.tenant.facturas.models import Factura
            from apps.tenant.facturas.services.business_service import same_nit
            from apps.tenant.facturas.services.selectors import FacturaSelectors

            factura = (
                FacturaSelectors.qs_detail(empresa_id=empresa_id).filter(uuid=factura_uuid).first()
            )
            if not factura:
                return (
                    False,
                    {
                        "error": "factura_not_found",
                        "message": "La Factura no existe o no pertenece a esta empresa.",
                    },
                    404,
                )

            if factura.naturaleza != Factura.Naturaleza.COMPRA:
                return (
                    False,
                    {
                        "error": "naturaleza_incorrecta",
                        "message": "Solo se puede vincular una Factura de naturaleza COMPRA a una Orden de Compra.",
                    },
                    422,
                )

            if (
                hasattr(factura, "orden_compra_origen")
                and factura.orden_compra_origen.id != orden.id
            ):
                return (
                    False,
                    {
                        "error": "factura_ya_vinculada",
                        "message": "Esta Factura ya esta vinculada a otra Orden de Compra.",
                    },
                    409,
                )

            if not same_nit(factura.emisor_nit, orden.proveedor.numero_documento):
                return (
                    False,
                    {
                        "error": "proveedor_incompatible",
                        "message": (
                            "El proveedor de la Factura de Compra no coincide "
                            "con el proveedor del documento de Compras."
                        ),
                    },
                    422,
                )

            orden = OrdenCompraCRUDService.vincular_factura(orden, factura)
            OrdenCompraBusinessService._sincronizar_factura_uuid_cuenta_pagar(orden, factura.uuid)
            return True, orden, 200
        except ValidationError as e:
            return False, e.detail, 400
        except Exception as e:
            logger.error(f"Error en vincular_factura_existente: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500

    @staticmethod
    @transaction.atomic
    def desvincular_factura_existente(orden_uuid: str, empresa_id: int) -> tuple[bool, Any, int]:
        """
        PLAN_VINCULAR_FACTURA_COMPRA_COMPRAS Fase 16/17: elimina UNICAMENTE
        el vinculo (OrdenCompra.factura_asociada), nunca la Factura fiscal.
        Bloquea si ya existen pagos aplicados sobre la CuentasPagar asociada
        a esa Factura -- desvincular en ese caso perderia trazabilidad de un
        pago real ya registrado.
        """
        try:
            orden = (
                OrdenCompra.objects.select_for_update()
                .filter(
                    uuid=orden_uuid,
                    empresa_id=empresa_id,
                )
                .first()
            )
            if not orden:
                return (
                    False,
                    {"error": "orden_no_encontrada", "message": "La orden de compra no existe."},
                    404,
                )

            if not orden.factura_asociada_id:
                return (
                    False,
                    {
                        "error": "sin_factura_vinculada",
                        "message": "Esta Orden de Compra no tiene una Factura vinculada.",
                    },
                    404,
                )

            from apps.tenant.proveedores.models import CuentasPagar

            factura_uuid_actual = orden.factura_asociada.uuid
            cuenta_pagar = (
                CuentasPagar.objects.filter(
                    empresa_id=empresa_id,
                    factura_uuid=factura_uuid_actual,
                )
                .only("id", "valor_pagado")
                .first()
            )
            if cuenta_pagar and cuenta_pagar.valor_pagado > 0:
                return (
                    False,
                    {
                        "error": "vinculo_bloqueado_pagos",
                        "message": (
                            "No se puede desvincular: ya existen pagos aplicados "
                            "sobre la Cuenta por Pagar de esta Factura."
                        ),
                    },
                    409,
                )

            if cuenta_pagar:
                cuenta_pagar.factura_uuid = None
                cuenta_pagar.save(update_fields=["factura_uuid"])

            orden = OrdenCompraCRUDService.desvincular_factura(orden)
            return True, orden, 200
        except ValidationError as e:
            return False, e.detail, 400
        except Exception as e:
            logger.error(f"Error en desvincular_factura_existente: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500

    @staticmethod
    def _sincronizar_factura_uuid_cuenta_pagar(orden: OrdenCompra, factura_uuid) -> None:
        """
        PLAN_VINCULAR_FACTURA_COMPRA_COMPRAS Fase 20: si la Orden ya tenia
        una CuentasPagar materializada (generada al Aprobar, ver
        _sincronizar_cuenta_por_pagar) sin `factura_uuid` propio, la
        completa con la Factura recien vinculada -- nunca crea una segunda
        CxP, solo completa la trazabilidad de la que ya existe.
        """
        from apps.tenant.proveedores.models import CuentasPagar

        CuentasPagar.objects.filter(
            empresa_id=orden.empresa_id,
            orden_compra_uuid=orden.uuid,
            factura_uuid__isnull=True,
        ).update(factura_uuid=factura_uuid)

    @staticmethod
    @transaction.atomic
    def vincular_requisicion_existente(
        orden_uuid: str, requisicion_uuid: str, empresa_id: int
    ) -> tuple[bool, Any, int]:
        """
        Vincula manualmente una Requisicion ya existente (con saldo
        disponible) a esta Orden de Compra YA EXISTENTE -- complementa a
        crear_orden_compra() (que exige >=1 Requisicion al crear)
        permitiendo agregar MAS despues, mismo patron que
        vincular_factura_existente(). Reutiliza
        ProcurementBudgetControlService (#20 del plan: "una regla, una
        implementacion") -- nunca reinventa el calculo de saldo.

        Decision explicita del usuario (2026-09-28): el monto asignado es
        SIEMPRE el saldo COMPLETO disponible de la Requisicion en el
        momento de vincular (no un monto parcial editable) -- deja la
        Requisicion sin saldo restante, por lo que deja de aparecer como
        "disponible" para cualquier otra Orden ("no se puede reutilizar en
        otras ordenes de compra, solo en una").
        """
        try:
            orden = (
                OrdenCompra.objects.select_for_update()
                .filter(
                    uuid=orden_uuid,
                    empresa_id=empresa_id,
                )
                .first()
            )
            if not orden:
                return (
                    False,
                    {"error": "orden_no_encontrada", "message": "La orden de compra no existe."},
                    404,
                )

            if orden.estado == "ANULADA":
                return (
                    False,
                    {
                        "error": "orden_anulada",
                        "message": "No se pueden vincular requisiciones a una Orden anulada.",
                    },
                    422,
                )

            if not requisicion_uuid:
                return (
                    False,
                    {
                        "error": "missing_requisicion_uuid",
                        "message": "requisicion_uuid es requerido.",
                    },
                    400,
                )

            from apps.tenant.compras.models import OrdenCompraRequisicion
            from apps.tenant.compras.requisiciones.models import RequisicionCompra
            from apps.tenant.compras.requisiciones.services.selectors import (
                ESTADOS_DISPONIBLES_PARA_COMPRA,
            )
            from apps.tenant.compras.services.budget_control_service import (
                ProcurementBudgetControlService,
            )

            requisicion = (
                RequisicionCompra.objects.select_for_update()
                .filter(
                    uuid=requisicion_uuid,
                    empresa_id=empresa_id,
                )
                .first()
            )
            if not requisicion:
                return (
                    False,
                    {
                        "error": "requisicion_not_found",
                        "message": "La requisicion no existe o no pertenece a esta empresa.",
                    },
                    404,
                )

            if requisicion.estado not in ESTADOS_DISPONIBLES_PARA_COMPRA:
                return (
                    False,
                    {
                        "error": "requisicion_no_disponible",
                        "message": (
                            f"La requisicion {requisicion.numero_documento} no esta en un estado "
                            f"disponible para vincular (estado actual: {requisicion.estado})."
                        ),
                    },
                    422,
                )

            if OrdenCompraRequisicion.objects.filter(
                orden_compra=orden, requisicion=requisicion
            ).exists():
                return (
                    False,
                    {
                        "error": "requisicion_ya_vinculada",
                        "message": "Esta requisicion ya esta vinculada a esta Orden de Compra.",
                    },
                    409,
                )

            saldo = ProcurementBudgetControlService.obtener_saldo_requisicion(requisicion)
            if saldo <= Decimal("0.00"):
                return (
                    False,
                    {
                        "error": "sin_saldo_disponible",
                        "message": (
                            f"La requisicion {requisicion.numero_documento} no tiene saldo disponible "
                            f"(ya fue consumida por otra(s) Orden(es) de Compra)."
                        ),
                    },
                    409,
                )

            OrdenCompraRequisicion.objects.create(
                empresa_id=empresa_id,
                orden_compra=orden,
                requisicion=requisicion,
                monto_asignado=saldo,
            )
            return True, orden, 201
        except ValidationError as e:
            return False, e.detail, 400
        except Exception as e:
            logger.error(f"Error en vincular_requisicion_existente: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500

    @staticmethod
    @transaction.atomic
    def desvincular_requisicion_existente(
        orden_uuid: str, requisicion_uuid: str, empresa_id: int
    ) -> tuple[bool, Any, int]:
        """
        Contraparte de vincular_requisicion_existente() -- solo permite
        quitar mientras la Orden sigue en BORRADOR/PENDIENTE (una vez
        APROBADA el presupuesto ya quedo comprometido --
        cambiar_estado_orden_compra() ya exige que TODAS las requisiciones
        vinculadas esten APROBADA antes de aprobar la Orden). Nunca deja la
        Orden sin NINGUNA requisicion vinculada (mismo invariante que exige
        crear_orden_compra() al crear).
        """
        try:
            orden = (
                OrdenCompra.objects.select_for_update()
                .filter(
                    uuid=orden_uuid,
                    empresa_id=empresa_id,
                )
                .first()
            )
            if not orden:
                return (
                    False,
                    {"error": "orden_no_encontrada", "message": "La orden de compra no existe."},
                    404,
                )

            if orden.estado not in ("BORRADOR", "PENDIENTE"):
                return (
                    False,
                    {
                        "error": "estado_no_permite_desvincular",
                        "message": "Solo se pueden quitar requisiciones mientras la Orden esta en Borrador o Pendiente.",
                    },
                    422,
                )

            from apps.tenant.compras.models import OrdenCompraRequisicion

            vinculo = OrdenCompraRequisicion.objects.filter(
                empresa_id=empresa_id,
                orden_compra=orden,
                requisicion__uuid=requisicion_uuid,
            ).first()
            if not vinculo:
                return (
                    False,
                    {
                        "error": "vinculo_no_encontrado",
                        "message": "Esta requisicion no esta vinculada a esta Orden de Compra.",
                    },
                    404,
                )

            if orden.requisiciones_vinculadas.count() <= 1:
                return (
                    False,
                    {
                        "error": "requisicion_requerida",
                        "message": "La Orden debe tener al menos una Requisicion vinculada -- vincule otra antes de quitar esta.",
                    },
                    422,
                )

            vinculo.delete()
            return True, orden, 200
        except ValidationError as e:
            return False, e.detail, 400
        except Exception as e:
            logger.error(f"Error en desvincular_requisicion_existente: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500


class RecepcionCompraBusinessService:
    """
    Logica de negocio para Recepcion de Compras (F21):
    OrdenCompra -> RecepcionCompra -> RecepcionCompraItem -> MovimientoInventario.

    Bridge controlado compras -> inventario (import local dentro de metodo,
    igual patron que el resto del codebase para evitar acoplamiento a nivel
    de modulo — ver F15_INTEGRATION_BASELINE.md sobre imports locales
    cross-app). Es el gap que este mismo prompt maestro pide cerrar; no una
    violacion de Bounded Context nueva.
    """

    @staticmethod
    @transaction.atomic
    def crear_recepcion(
        data: dict, items_data: list, empresa: Any, sede: Any, usuario: Any
    ) -> tuple[bool, Any, int]:
        """
        Crea una RecepcionCompra en BORRADOR (sin efecto en stock todavia).
        Valida: orden existe/pertenece a la empresa, esta en un estado que
        admite recepcion, cada item pertenece a esa orden, y cantidad_recibida
        de este evento no excede lo pendiente (cantidad - cantidad_recibida
        acumulada) — bloquea el escenario "100 ordenado, 60+40 recibido, un
        tercer intento de 10 debe RECHAZARSE" desde el momento de creacion,
        no solo al confirmar.
        """
        try:
            orden_raw = data.get("orden_compra") or data.get("orden_compra_uuid")
            orden = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                OrdenCompra, orden_raw, empresa.id
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

            if orden.estado not in ("APROBADA", "PARCIAL"):
                return (
                    False,
                    {
                        "error": "estado_invalido",
                        "message": f"Solo se puede recibir mercancia de una orden APROBADA o con recepcion PARCIAL (estado actual: {orden.estado}).",
                    },
                    422,
                )

            sede_recepcion = sede or orden.sede
            if sede_recepcion.empresa_id != empresa.id:
                return (
                    False,
                    {
                        "error": "sede_invalida",
                        "message": "La sede de recepcion no pertenece a la empresa actual.",
                    },
                    422,
                )

            if not items_data:
                return (
                    False,
                    {
                        "error": "items_requeridos",
                        "message": "Debe indicar al menos un item recibido.",
                    },
                    400,
                )

            items_resueltos = []
            for item_in in items_data:
                item_raw = item_in.get("item_orden_compra") or item_in.get("item_orden_compra_uuid")
                item = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                    ItemOrdenCompra, item_raw, empresa.id
                )
                if not item or item.orden_compra_id != orden.id:
                    return (
                        False,
                        {
                            "error": "item_invalido",
                            "message": f"El item {item_raw} no existe en esta orden de compra.",
                        },
                        400,
                    )

                cantidad = Decimal(str(item_in.get("cantidad_recibida") or "0"))
                if cantidad <= 0:
                    return (
                        False,
                        {
                            "error": "cantidad_invalida",
                            "message": "cantidad_recibida debe ser mayor a cero.",
                        },
                        400,
                    )

                pendiente = item.cantidad - item.cantidad_recibida
                if cantidad > pendiente:
                    return (
                        False,
                        {
                            "error": "cantidad_excede_pendiente",
                            "message": (
                                f"Cantidad recibida ({cantidad}) excede lo pendiente ({pendiente}) "
                                f"para el item '{item.descripcion}'."
                            ),
                        },
                        422,
                    )

                items_resueltos.append(
                    {
                        "item_orden_compra": item,
                        "cantidad_recibida": cantidad,
                        "observaciones": item_in.get("observaciones", ""),
                    }
                )

            recepcion = RecepcionCompraCRUDService.crear_recepcion(
                empresa=empresa,
                sede=sede_recepcion,
                orden_compra=orden,
                usuario=usuario,
                fecha=data.get("fecha") or timezone.localdate(),
                items_data=items_resueltos,
                observaciones=data.get("observaciones", ""),
            )
            return True, recepcion, 201
        except ValidationError as e:
            return False, e.detail if hasattr(e, "detail") else {"detail": str(e)}, 400
        except Exception as e:
            logger.error(f"Error en crear_recepcion: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500

    @staticmethod
    @transaction.atomic
    def confirmar_recepcion(recepcion_uuid: str, empresa_id: int) -> tuple[bool, Any, int]:
        """
        Confirma una RecepcionCompra BORRADOR: genera MovimientoInventario
        ENTRADA_COMPRA por cada linea con producto resoluble en el catalogo
        (item_inventario_uuid -> Producto), acumula ItemOrdenCompra.cantidad_recibida,
        y transiciona OrdenCompra a PARCIAL o RECIBIDA.

        Idempotente (F21 S16): un segundo llamado sobre una recepcion ya
        CONFIRMADA es un no-op exitoso (mismo resultado, sin generar
        movimientos duplicados) — select_for_update() sobre la recepcion
        serializa intentos concurrentes; KardexService.registrar_movimiento()
        es una segunda capa de idempotencia (UniqueConstraint de BD) para la
        carrera real entre dos transacciones que pasan el chequeo de estado
        antes de que cualquiera haga commit.
        """
        from apps.tenant.inventario.models import MovimientoInventario, Producto
        from apps.tenant.inventario.services.business_service import KardexService

        try:
            recepcion = (
                RecepcionCompra.objects.select_for_update()
                .filter(uuid=recepcion_uuid, empresa_id=empresa_id)
                .first()
            )
            if not recepcion:
                return (
                    False,
                    {
                        "error": "recepcion_no_encontrada",
                        "message": "La recepcion no existe o no pertenece a la empresa.",
                    },
                    404,
                )

            if recepcion.estado == RecepcionCompra.Estado.CONFIRMADA:
                return True, recepcion, 200

            if recepcion.estado != RecepcionCompra.Estado.BORRADOR:
                return (
                    False,
                    {
                        "error": "estado_invalido",
                        "message": f"No se puede confirmar una recepcion en estado {recepcion.estado}.",
                    },
                    422,
                )

            orden = OrdenCompra.objects.select_for_update().get(pk=recepcion.orden_compra_id)

            for item_recepcion in recepcion.items.select_related("item_orden_compra").all():
                item_oc = ItemOrdenCompra.objects.select_for_update().get(
                    pk=item_recepcion.item_orden_compra_id
                )

                nueva_recibida = item_oc.cantidad_recibida + item_recepcion.cantidad_recibida
                if nueva_recibida > item_oc.cantidad:
                    raise ValidationError(
                        f"La confirmacion excede la cantidad ordenada para '{item_oc.descripcion}' "
                        f"(ordenado={item_oc.cantidad}, ya recibido={item_oc.cantidad_recibida}, "
                        f"este evento={item_recepcion.cantidad_recibida})."
                    )
                item_oc.cantidad_recibida = nueva_recibida
                item_oc.full_clean()
                item_oc.save(update_fields=["cantidad_recibida"])

                producto = None
                if item_oc.item_inventario_uuid:
                    producto = (
                        Producto.objects.filter(
                            uuid=item_oc.item_inventario_uuid,
                            empresa_id=empresa_id,
                        )
                        .only("id")
                        .first()
                    )

                if producto is not None:
                    KardexService.registrar_movimiento(
                        empresa_id=empresa_id,
                        producto_id=producto.id,
                        tipo=MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
                        cantidad=item_recepcion.cantidad_recibida,
                        costo_unitario=item_oc.valor_unitario,
                        origen_referencia=orden.numero_documento or f"OC-{orden.consecutivo}",
                        sede_id=recepcion.sede_id,
                        documento_origen_app="compras",
                        documento_origen_modelo="RecepcionCompraItem",
                        documento_origen_id=item_recepcion.id,
                    )
                else:
                    logger.info(
                        "[RecepcionCompraBS] item_orden_compra id=%s sin Producto de catalogo "
                        "resoluble (item_inventario_uuid=%s) - se omite MovimientoInventario, "
                        "la recepcion sigue siendo valida (F21 S10/S15).",
                        item_oc.id,
                        item_oc.item_inventario_uuid,
                    )

            recepcion = RecepcionCompraCRUDService.marcar_confirmada(recepcion)

            items_oc = list(orden.items.all())
            todos_completos = all(i.cantidad_recibida >= i.cantidad for i in items_oc)
            algo_recibido = any(i.cantidad_recibida > 0 for i in items_oc)
            if todos_completos:
                nuevo_estado_orden = "RECIBIDA"
            elif algo_recibido:
                nuevo_estado_orden = "PARCIAL"
            else:
                nuevo_estado_orden = orden.estado
            if nuevo_estado_orden != orden.estado:
                OrdenCompraCRUDService.cambiar_estado(orden, nuevo_estado_orden)

            return True, recepcion, 200
        except ValidationError as e:
            transaction.set_rollback(True)
            return False, e.detail if hasattr(e, "detail") else {"detail": str(e)}, 400
        except Exception as e:
            transaction.set_rollback(True)
            logger.error(f"Error en confirmar_recepcion: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500

    @staticmethod
    @transaction.atomic
    def anular_recepcion(recepcion_uuid: str, empresa_id: int) -> tuple[bool, Any, int]:
        """
        Anula una RecepcionCompra. Solo permitido en BORRADOR: una CONFIRMADA
        ya genero MovimientoInventario append-only reales — reversarla
        requeriria un movimiento compensatorio explicito, deliberadamente
        fuera de alcance de F21 (riesgo de corromper trazabilidad historica,
        ver S49 del prompt maestro: se bloquea la operacion especifica en vez
        de intentarla).
        """
        try:
            recepcion = RecepcionCompra.objects.filter(
                uuid=recepcion_uuid, empresa_id=empresa_id
            ).first()
            if not recepcion:
                return (
                    False,
                    {
                        "error": "recepcion_no_encontrada",
                        "message": "La recepcion no existe o no pertenece a la empresa.",
                    },
                    404,
                )

            if recepcion.estado != RecepcionCompra.Estado.BORRADOR:
                return (
                    False,
                    {
                        "error": "estado_invalido",
                        "message": "Solo se puede anular una recepcion en estado Borrador.",
                    },
                    422,
                )

            recepcion = RecepcionCompraCRUDService.anular(recepcion)
            return True, recepcion, 200
        except Exception as e:
            transaction.set_rollback(True)
            logger.error(f"Error en anular_recepcion: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500
