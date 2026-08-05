import logging
import uuid as uuid_lib
from typing import Tuple, Any, Dict, List

from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import ValidationError

from apps.tenant.compras.models import OrdenCompra, PlantillaOrdenCompra
from apps.tenant.compras.services.crud_service import OrdenCompraCRUDService
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
    def crear_orden_compra(data: dict, items_data: list, empresa: Any) -> Tuple[bool, Any, int]:
        """
        Orquesta la creacion de una Orden de Compra.
        Aplica Double Semantic Verification (DSV) en Plantilla, Proveedor, Proyecto y Documento Soporte.
        """
        logger.info(f"[OrdenCompraBusinessService:crear_orden_compra] Iniciando proceso para empresa={empresa.id}")
        try:
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
            orden = OrdenCompraCRUDService.crear_orden(data, items_data, empresa)
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
