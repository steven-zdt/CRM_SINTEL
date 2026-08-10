import logging
import uuid as uuid_lib
from decimal import Decimal
from typing import Any, Dict, List, Tuple

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
from apps.tenant.compras.services.selectors import OrdenCompraSelector

logger = logging.getLogger(__name__)


class OrdenCompraBusinessService:
    """
    Logica de negocio para Ordenes de Compra.
    Realiza la Double Semantic Verification (DSV) y orquesta transacciones.
    """

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
            if getattr(lookup_value, 'empresa_id', None) == empresa_id:
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
                return model_class.objects.filter(id=int(lookup_value), empresa_id=empresa_id).first()
            except (ValueError, TypeError):
                return None

    @staticmethod
    def _dsv_y_asignar_plantilla(empresa_id: int, plantilla_raw: Any):
        """
        DSV + asignacion atomica del consecutivo de la PlantillaOrdenCompra.
        Usa select_for_update() para prevenir race conditions en entornos concurrentes.

        Debe invocarse dentro de un bloque @transaction.atomic.

        Retorna: (plantilla_instance, numero_documento_str, consecutivo_int)
        """
        if isinstance(plantilla_raw, PlantillaOrdenCompra):
            plantilla_id = plantilla_raw.id
            plantilla = (
                PlantillaOrdenCompra.objects
                .select_for_update()
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
                    PlantillaOrdenCompra.objects
                    .select_for_update()
                    .filter(uuid=plantilla_raw, empresa_id=empresa_id)
                    .first()
                )
            else:
                try:
                    plantilla = (
                        PlantillaOrdenCompra.objects
                        .select_for_update()
                        .filter(id=int(plantilla_raw), empresa_id=empresa_id)
                        .first()
                    )
                except (ValueError, TypeError):
                    plantilla = None

        if not plantilla:
            raise ValidationError(
                {"plantilla": f"La plantilla {plantilla_raw} no fue encontrada o no pertenece a la empresa."}
            )
        if not plantilla.vigente:
            raise ValidationError(
                {"plantilla": f"La plantilla {plantilla.nombre} no esta marcada como vigente."}
            )
        if not plantilla.esta_en_rango():
            raise ValidationError(
                {"plantilla": f"La plantilla {plantilla.nombre} ha agotado su rango de consecutivos ({plantilla.rango_desde}-{plantilla.rango_hasta})."}
            )

        consecutivo = plantilla.consecutivo_actual
        numero_documento = plantilla.formar_numero()

        # Incrementar consecutivo atomicamente (con select_for_update ya activo)
        PlantillaOrdenCompra.objects.filter(pk=plantilla.pk).update(
            consecutivo_actual=F('consecutivo_actual') + 1
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
    def crear_orden_compra(data: dict, items_data: list, empresa: Any, sede: Any) -> Tuple[bool, Any, int]:
        """
        Orquesta la creacion de una Orden de Compra.
        Aplica Double Semantic Verification (DSV) en Plantilla, Proveedor, Proyecto, Documento
        Soporte y Area (opcional). `sede` es un parametro explicito (ver ADR-003) - este metodo
        nunca la resuelve por su cuenta.
        """
        logger.info(f"[OrdenCompraBusinessService:crear_orden_compra] Iniciando proceso para empresa={empresa.id}")
        try:
            if sede is None:
                return False, {"error": "sede_requerida", "message": "No hay ninguna Sede activa para esta empresa. Cree al menos una Sede antes de registrar ordenes de compra."}, 422
            if getattr(sede, 'empresa_id', None) != empresa.id:
                # Anti-IDOR: la sede resuelta por el contexto debe pertenecer a la misma empresa.
                return False, {"error": "sede_invalida", "message": "La sede activa no pertenece a la empresa actual."}, 422

            # DSV: Area (opcional) - si viene, debe pertenecer a la misma
            # empresa Y a la misma Sede de la orden (F5, OSF: un Area
            # siempre cuelga de una Sede especifica - permitir un Area de
            # otra Sede dejaria la orden en un estado organizacionalmente
            # inconsistente, ej. alcance=AREA filtrando por una combinacion
            # sede/area que nunca puede coincidir con datos reales).
            area_raw = data.get('area') or data.get('area_uuid')
            if area_raw:
                from apps.tenant.empresa.models import Area
                area = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                    Area, area_raw, empresa.id
                )
                if not area:
                    return False, {"error": "area_invalida", "message": "El area especificada no es valida o no pertenece a la empresa."}, 400
                if area.sede_id != sede.id:
                    return False, {"error": "area_invalida", "message": "El area especificada no pertenece a la sede de esta orden."}, 400
                data.pop('area_uuid', None)
                data['area'] = area
            else:
                data.pop('area_uuid', None)
                data['area'] = None

            # 1. DSV: Plantilla (Obligatorio)
            plantilla_raw = data.get('plantilla') or data.get('plantilla_uuid')
            if not plantilla_raw:
                raise ValidationError({"plantilla": "La plantilla de orden de compra es obligatoria."})
            
            plantilla, numero_documento, consecutivo = OrdenCompraBusinessService._dsv_y_asignar_plantilla(
                empresa.id, plantilla_raw
            )
            # Remove UUID key if present to avoid conflicting arguments
            data.pop('plantilla_uuid', None)
            data['plantilla'] = plantilla
            data['numero_documento'] = numero_documento
            data['consecutivo'] = consecutivo

            # 2. DSV: Proveedor (Obligatorio)
            from apps.tenant.proveedores.models import Proveedor
            proveedor_raw = data.get('proveedor') or data.get('proveedor_uuid')
            proveedor = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                Proveedor, proveedor_raw, empresa.id
            )
            if not proveedor:
                return False, {"error": "proveedor_invalido", "message": "El proveedor especificado no es valido."}, 400
            data.pop('proveedor_uuid', None)
            data['proveedor'] = proveedor

            # 3. DSV: Proyecto (Opcional)
            proyecto_raw = data.get('proyecto') or data.get('proyecto_uuid')
            if proyecto_raw:
                from apps.tenant.proyectos.models import Proyecto
                proyecto = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                    Proyecto, proyecto_raw, empresa.id
                )
                if not proyecto:
                    return False, {"error": "proyecto_invalido", "message": "El proyecto especificado no es valido o no pertenece a la empresa."}, 400
                data.pop('proyecto_uuid', None)
                data['proyecto'] = proyecto
            else:
                data.pop('proyecto_uuid', None)
                data['proyecto'] = None

            # 4. DSV: Documento Soporte / Gasto (Opcional)
            doc_raw = data.get('documento_soporte') or data.get('documento_soporte_uuid')
            if doc_raw:
                from apps.tenant.gastos.models import DocumentoSoporte
                doc = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                    DocumentoSoporte, doc_raw, empresa.id
                )
                if not doc:
                    return False, {"error": "documento_invalido", "message": "El documento soporte especificado no es valido o no pertenece a la empresa."}, 400
                data.pop('documento_soporte_uuid', None)
                data['documento_soporte'] = doc
            else:
                data.pop('documento_soporte_uuid', None)
                data['documento_soporte'] = None

            # 5. Crear a traves de CRUD
            orden = OrdenCompraCRUDService.crear_orden(data, items_data, empresa, sede)
            return True, orden, 201

        except ValidationError as e:
            return False, e.detail, 400
        except Exception as e:
            logger.error(f"Error en crear_orden_compra: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500

    @staticmethod
    @transaction.atomic
    def actualizar_orden_compra(orden_uuid: str, data: dict, items_data: list, empresa_id: int) -> Tuple[bool, Any, int]:
        """
        Orquesta la actualizacion de una Orden de Compra y sus items.
        """
        logger.info(f"[OrdenCompraBusinessService:actualizar_orden_compra] UUID={orden_uuid}")
        try:
            orden = OrdenCompra.objects.filter(uuid=orden_uuid, empresa_id=empresa_id).first()
            if not orden:
                return False, {"error": "orden_no_encontrada", "message": "La orden de compra no existe."}, 404

            # 1. DSV: Proveedor (Si viene en la peticion)
            if 'proveedor' in data or 'proveedor_uuid' in data:
                from apps.tenant.proveedores.models import Proveedor
                proveedor_raw = data.get('proveedor') or data.get('proveedor_uuid')
                proveedor = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                    Proveedor, proveedor_raw, empresa_id
                )
                if not proveedor:
                    return False, {"error": "proveedor_invalido", "message": "El proveedor especificado no es valido."}, 400
                data.pop('proveedor_uuid', None)
                data['proveedor'] = proveedor

            # 2. DSV: Proyecto (Si viene en la peticion)
            if 'proyecto' in data or 'proyecto_uuid' in data:
                proyecto_raw = data.get('proyecto') or data.get('proyecto_uuid')
                if proyecto_raw:
                    from apps.tenant.proyectos.models import Proyecto
                    proyecto = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                        Proyecto, proyecto_raw, empresa_id
                    )
                    if not proyecto:
                        return False, {"error": "proyecto_invalido", "message": "El proyecto especificado no es valido."}, 400
                    data.pop('proyecto_uuid', None)
                    data['proyecto'] = proyecto
                else:
                    data.pop('proyecto_uuid', None)
                    data['proyecto'] = None

            # 3. DSV: Documento Soporte (Si viene en la peticion)
            if 'documento_soporte' in data or 'documento_soporte_uuid' in data:
                doc_raw = data.get('documento_soporte') or data.get('documento_soporte_uuid')
                if doc_raw:
                    from apps.tenant.gastos.models import DocumentoSoporte
                    doc = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                        DocumentoSoporte, doc_raw, empresa_id
                    )
                    if not doc:
                        return False, {"error": "documento_invalido", "message": "El documento soporte especificado no es valido."}, 400
                    data.pop('documento_soporte_uuid', None)
                    data['documento_soporte'] = doc
                else:
                    data.pop('documento_soporte_uuid', None)
                    data['documento_soporte'] = None

            # 4. DSV: Area (Si viene en la peticion) - [OSF Fase F5] Hallazgo
            # real: antes de esta fase 'area' nunca llegaba aqui (el
            # serializer no lo declaraba, ver OrdenCompraCreateUpdateSerializer),
            # asi que este bloque no existia - agregado simetrico a los de
            # arriba, con la misma regla de consistencia sede/area que
            # crear_orden_compra (un Area siempre pertenece a una Sede
            # especifica; la Sede de la orden es inmutable tras crearla).
            if 'area' in data or 'area_uuid' in data:
                area_raw = data.get('area') or data.get('area_uuid')
                if area_raw:
                    from apps.tenant.empresa.models import Area
                    area = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                        Area, area_raw, empresa_id
                    )
                    if not area:
                        return False, {"error": "area_invalida", "message": "El area especificada no es valida o no pertenece a la empresa."}, 400
                    if area.sede_id != orden.sede_id:
                        return False, {"error": "area_invalida", "message": "El area especificada no pertenece a la sede de esta orden."}, 400
                    data.pop('area_uuid', None)
                    data['area'] = area
                else:
                    data.pop('area_uuid', None)
                    data['area'] = None

            orden = OrdenCompraCRUDService.actualizar_orden(orden, data, items_data)
            return True, orden, 200

        except ValidationError as e:
            return False, e.detail, 400
        except Exception as e:
            logger.error(f"Error en actualizar_orden_compra: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500

    @staticmethod
    @transaction.atomic
    def cambiar_estado_orden_compra(orden_uuid: str, nuevo_estado: str, empresa_id: int) -> Tuple[bool, Any, int]:
        """
        Cambia el estado de una Orden de Compra.
        """
        try:
            orden = OrdenCompra.objects.filter(uuid=orden_uuid, empresa_id=empresa_id).first()
            if not orden:
                return False, {"error": "orden_no_encontrada", "message": "La orden de compra no existe."}, 404

            orden = OrdenCompraCRUDService.cambiar_estado(orden, nuevo_estado)
            return True, orden, 200
        except ValidationError as e:
            return False, e.detail, 400
        except Exception as e:
            logger.error(f"Error en cambiar_estado_orden_compra: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500

    @staticmethod
    @transaction.atomic
    def eliminar_orden_compra(orden_uuid: str, empresa_id: int) -> Tuple[bool, Any, int]:
        """
        Elimina fisicamente una Orden de Compra si cumple las condiciones (estado Borrador).
        """
        try:
            orden = OrdenCompra.objects.filter(uuid=orden_uuid, empresa_id=empresa_id).first()
            if not orden:
                return False, {"error": "orden_no_encontrada", "message": "La orden de compra no existe."}, 404

            OrdenCompraCRUDService.eliminar_orden(orden)
            return True, {"message": "Orden de compra eliminada correctamente."}, 204
        except ValidationError as e:
            return False, e.detail, 400
        except Exception as e:
            logger.error(f"Error en eliminar_orden_compra: {e}", exc_info=True)
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
    def crear_recepcion(data: dict, items_data: list, empresa: Any, sede: Any, usuario: Any) -> Tuple[bool, Any, int]:
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
            orden_raw = data.get('orden_compra') or data.get('orden_compra_uuid')
            orden = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                OrdenCompra, orden_raw, empresa.id
            )
            if not orden:
                return False, {"error": "orden_no_encontrada", "message": "La orden de compra no existe o no pertenece a la empresa."}, 404

            if orden.estado not in ('APROBADA', 'PARCIAL'):
                return False, {
                    "error": "estado_invalido",
                    "message": f"Solo se puede recibir mercancia de una orden APROBADA o con recepcion PARCIAL (estado actual: {orden.estado}).",
                }, 422

            sede_recepcion = sede or orden.sede
            if sede_recepcion.empresa_id != empresa.id:
                return False, {"error": "sede_invalida", "message": "La sede de recepcion no pertenece a la empresa actual."}, 422

            if not items_data:
                return False, {"error": "items_requeridos", "message": "Debe indicar al menos un item recibido."}, 400

            items_resueltos = []
            for item_in in items_data:
                item_raw = item_in.get('item_orden_compra') or item_in.get('item_orden_compra_uuid')
                item = OrdenCompraBusinessService._obtener_entidad_por_id_o_uuid(
                    ItemOrdenCompra, item_raw, empresa.id
                )
                if not item or item.orden_compra_id != orden.id:
                    return False, {"error": "item_invalido", "message": f"El item {item_raw} no existe en esta orden de compra."}, 400

                cantidad = Decimal(str(item_in.get('cantidad_recibida') or '0'))
                if cantidad <= 0:
                    return False, {"error": "cantidad_invalida", "message": "cantidad_recibida debe ser mayor a cero."}, 400

                pendiente = item.cantidad - item.cantidad_recibida
                if cantidad > pendiente:
                    return False, {
                        "error": "cantidad_excede_pendiente",
                        "message": (
                            f"Cantidad recibida ({cantidad}) excede lo pendiente ({pendiente}) "
                            f"para el item '{item.descripcion}'."
                        ),
                    }, 422

                items_resueltos.append({
                    'item_orden_compra': item,
                    'cantidad_recibida': cantidad,
                    'observaciones': item_in.get('observaciones', ''),
                })

            recepcion = RecepcionCompraCRUDService.crear_recepcion(
                empresa=empresa,
                sede=sede_recepcion,
                orden_compra=orden,
                usuario=usuario,
                fecha=data.get('fecha') or timezone.localdate(),
                items_data=items_resueltos,
                observaciones=data.get('observaciones', ''),
            )
            return True, recepcion, 201
        except ValidationError as e:
            return False, e.detail if hasattr(e, 'detail') else {"detail": str(e)}, 400
        except Exception as e:
            logger.error(f"Error en crear_recepcion: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500

    @staticmethod
    @transaction.atomic
    def confirmar_recepcion(recepcion_uuid: str, empresa_id: int) -> Tuple[bool, Any, int]:
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
                return False, {"error": "recepcion_no_encontrada", "message": "La recepcion no existe o no pertenece a la empresa."}, 404

            if recepcion.estado == RecepcionCompra.Estado.CONFIRMADA:
                return True, recepcion, 200

            if recepcion.estado != RecepcionCompra.Estado.BORRADOR:
                return False, {
                    "error": "estado_invalido",
                    "message": f"No se puede confirmar una recepcion en estado {recepcion.estado}.",
                }, 422

            orden = OrdenCompra.objects.select_for_update().get(pk=recepcion.orden_compra_id)

            for item_recepcion in recepcion.items.select_related('item_orden_compra').all():
                item_oc = ItemOrdenCompra.objects.select_for_update().get(pk=item_recepcion.item_orden_compra_id)

                nueva_recibida = item_oc.cantidad_recibida + item_recepcion.cantidad_recibida
                if nueva_recibida > item_oc.cantidad:
                    raise ValidationError(
                        f"La confirmacion excede la cantidad ordenada para '{item_oc.descripcion}' "
                        f"(ordenado={item_oc.cantidad}, ya recibido={item_oc.cantidad_recibida}, "
                        f"este evento={item_recepcion.cantidad_recibida})."
                    )
                item_oc.cantidad_recibida = nueva_recibida
                item_oc.full_clean()
                item_oc.save(update_fields=['cantidad_recibida'])

                producto = None
                if item_oc.item_inventario_uuid:
                    producto = Producto.objects.filter(
                        uuid=item_oc.item_inventario_uuid, empresa_id=empresa_id,
                    ).only('id').first()

                if producto is not None:
                    KardexService.registrar_movimiento(
                        empresa_id=empresa_id,
                        producto_id=producto.id,
                        tipo=MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
                        cantidad=item_recepcion.cantidad_recibida,
                        costo_unitario=item_oc.valor_unitario,
                        origen_referencia=orden.numero_documento or f"OC-{orden.consecutivo}",
                        sede_id=recepcion.sede_id,
                        documento_origen_app='compras',
                        documento_origen_modelo='RecepcionCompraItem',
                        documento_origen_id=item_recepcion.id,
                    )
                else:
                    logger.info(
                        "[RecepcionCompraBS] item_orden_compra id=%s sin Producto de catalogo "
                        "resoluble (item_inventario_uuid=%s) - se omite MovimientoInventario, "
                        "la recepcion sigue siendo valida (F21 S10/S15).",
                        item_oc.id, item_oc.item_inventario_uuid,
                    )

            recepcion = RecepcionCompraCRUDService.marcar_confirmada(recepcion)

            items_oc = list(orden.items.all())
            todos_completos = all(i.cantidad_recibida >= i.cantidad for i in items_oc)
            algo_recibido = any(i.cantidad_recibida > 0 for i in items_oc)
            if todos_completos:
                nuevo_estado_orden = 'RECIBIDA'
            elif algo_recibido:
                nuevo_estado_orden = 'PARCIAL'
            else:
                nuevo_estado_orden = orden.estado
            if nuevo_estado_orden != orden.estado:
                OrdenCompraCRUDService.cambiar_estado(orden, nuevo_estado_orden)

            return True, recepcion, 200
        except ValidationError as e:
            transaction.set_rollback(True)
            return False, e.detail if hasattr(e, 'detail') else {"detail": str(e)}, 400
        except Exception as e:
            transaction.set_rollback(True)
            logger.error(f"Error en confirmar_recepcion: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500

    @staticmethod
    @transaction.atomic
    def anular_recepcion(recepcion_uuid: str, empresa_id: int) -> Tuple[bool, Any, int]:
        """
        Anula una RecepcionCompra. Solo permitido en BORRADOR: una CONFIRMADA
        ya genero MovimientoInventario append-only reales — reversarla
        requeriria un movimiento compensatorio explicito, deliberadamente
        fuera de alcance de F21 (riesgo de corromper trazabilidad historica,
        ver S49 del prompt maestro: se bloquea la operacion especifica en vez
        de intentarla).
        """
        try:
            recepcion = RecepcionCompra.objects.filter(uuid=recepcion_uuid, empresa_id=empresa_id).first()
            if not recepcion:
                return False, {"error": "recepcion_no_encontrada", "message": "La recepcion no existe o no pertenece a la empresa."}, 404

            if recepcion.estado != RecepcionCompra.Estado.BORRADOR:
                return False, {
                    "error": "estado_invalido",
                    "message": "Solo se puede anular una recepcion en estado Borrador.",
                }, 422

            recepcion = RecepcionCompraCRUDService.anular(recepcion)
            return True, recepcion, 200
        except Exception as e:
            transaction.set_rollback(True)
            logger.error(f"Error en anular_recepcion: {e}", exc_info=True)
            return False, {"detail": f"Error interno del servidor: {str(e)}"}, 500
