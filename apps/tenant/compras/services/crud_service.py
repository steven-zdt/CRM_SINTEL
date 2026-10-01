import logging
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.tenant.compras.models import (
    ItemOrdenCompra,
    OrdenCompra,
    PlantillaOrdenCompra,
    RecepcionCompra,
    RecepcionCompraItem,
)
from apps.tenant.empresa.models import Empresa

_TWO = Decimal("0.01")
logger = logging.getLogger(__name__)


def _calcular_item(item_data: dict) -> dict:
    """SSoT del calculo de subtotal/iva/total de un item (Fase 7/9 de
    PLAN_OPTIMIZACION_COMPRAS...). Reutilizado por crear_orden() y
    actualizar_orden() -- antes cada uno repetia la misma formula inline."""
    cant = Decimal(str(item_data.get("cantidad", 0)))
    val_uni = Decimal(str(item_data.get("valor_unitario", 0)))
    pct_iva = Decimal(str(item_data.get("porcentaje_iva", 0)))

    subtotal = (cant * val_uni).quantize(_TWO, rounding=ROUND_HALF_UP)
    iva = (subtotal * (pct_iva / Decimal("100"))).quantize(_TWO, rounding=ROUND_HALF_UP)
    total = (subtotal + iva).quantize(_TWO, rounding=ROUND_HALF_UP)
    return {
        "cantidad": cant,
        "valor_unitario": val_uni,
        "porcentaje_iva": pct_iva,
        "subtotal": subtotal,
        "iva": iva,
        "total": total,
    }


class PlantillaOrdenCompraCRUDService:
    """
    Operaciones CRUD puras y persistencia transaccional para PlantillaOrdenCompra.
    """

    @staticmethod
    @transaction.atomic
    def crear_plantilla(empresa, data: dict) -> PlantillaOrdenCompra:
        """
        Crea una nueva PlantillaOrdenCompra.
        """
        plantilla = PlantillaOrdenCompra(
            empresa=empresa,
            # Bug real encontrado en vivo (PLAN_NUEVA_REQUISICION_NUMERACION_
            # CLIENTE_COTIZACIONES.md Fase A): este metodo nunca leia
            # tipo_documento del payload -- toda plantilla creada via la API
            # real (incluido el formulario) quedaba siempre en el default
            # del modelo (ORDEN_COMPRA), sin importar lo seleccionado en
            # "Tipo de Documento". El default aqui preserva el
            # comportamiento previo para cualquier caller que no lo envie.
            tipo_documento=data.get(
                "tipo_documento", PlantillaOrdenCompra.TipoDocumento.ORDEN_COMPRA
            ),
            nombre=data["nombre"],
            prefijo=data.get("prefijo", ""),
            rango_desde=data["rango_desde"],
            rango_hasta=data["rango_hasta"],
            consecutivo_actual=data.get("consecutivo_actual", data.get("rango_desde", 1)),
            vigente=data.get("vigente", True),
        )
        plantilla.full_clean()
        plantilla.save()
        logger.info(
            "[PlantillaCRUD] PlantillaOrdenCompra id=%s creada para empresa_id=%s",
            plantilla.id,
            empresa.id,
        )
        return plantilla

    @staticmethod
    @transaction.atomic
    def actualizar_plantilla(plantilla: PlantillaOrdenCompra, data: dict) -> PlantillaOrdenCompra:
        """
        Actualiza campos editables de PlantillaOrdenCompra.
        """
        campos = [
            "nombre",
            "prefijo",
            "rango_desde",
            "rango_hasta",
            "consecutivo_actual",
            "vigente",
        ]
        for campo in campos:
            if campo in data:
                setattr(plantilla, campo, data[campo])
        plantilla.full_clean()
        plantilla.save()
        logger.info("[PlantillaCRUD] PlantillaOrdenCompra id=%s actualizada", plantilla.id)
        return plantilla

    @staticmethod
    @transaction.atomic
    def eliminar_plantilla(plantilla: PlantillaOrdenCompra) -> None:
        """
        Elimina la plantilla si no tiene ordenes de compra asociadas.
        """
        if plantilla.ordenes_compra.exists():
            raise ValidationError(
                "No se puede eliminar una plantilla con ordenes de compra asociadas. Marquela como inactiva."
            )
        plantilla_id = plantilla.id
        plantilla.delete()
        logger.info("[PlantillaCRUD] PlantillaOrdenCompra id=%s eliminada", plantilla_id)


class OrdenCompraCRUDService:
    """
    Operaciones CRUD puras y persistencia transaccional para OrdenCompra.
    """

    @staticmethod
    @transaction.atomic
    def crear_orden(data: dict, items_data: list, empresa: Empresa, sede) -> OrdenCompra:
        """
        Crea una nueva Orden de Compra y sus items asociados dentro de una transaccion.

        [ADR-003] `sede` es un parametro explicito, igual que `empresa`: nunca
        se re-deriva dentro de esta capa. El llamador (business_service) es
        responsable de resolverla (ver SintelDSVMixin.get_sede_id() /
        _get_sede() en apps/tenant/api/mixins.py) antes de invocar esto.
        `area` (opcional) sigue fluyendo dentro de `data` como cualquier otro
        FK opcional de esta orden (proyecto, documento_soporte).
        """
        if not items_data:
            raise ValidationError("Una orden de compra debe contener al menos un item.")

        data = data.copy()
        consecutivo = data.pop("consecutivo")
        numero_documento = data.pop("numero_documento")
        plantilla = data.pop("plantilla")
        data.pop("items", None)

        # Fase 7 (PLAN_OPTIMIZACION_COMPRAS...): totales calculados ANTES de
        # crear la cabecera -- evita el patron "crear en 0 -> recalcular ->
        # segundo save()". Los items en si (con FK a `orden`) solo pueden
        # insertarse despues de que la cabecera tenga PK.
        calculos = [_calcular_item(item_data) for item_data in items_data]
        subtotal = sum((c["subtotal"] for c in calculos), Decimal("0.00"))
        impuestos = sum((c["iva"] for c in calculos), Decimal("0.00"))
        total = sum((c["total"] for c in calculos), Decimal("0.00"))

        orden = OrdenCompra(
            empresa=empresa,
            sede=sede,
            consecutivo=consecutivo,
            numero_documento=numero_documento,
            plantilla=plantilla,
            subtotal=subtotal.quantize(_TWO, rounding=ROUND_HALF_UP),
            impuestos=impuestos.quantize(_TWO, rounding=ROUND_HALF_UP),
            total=total.quantize(_TWO, rounding=ROUND_HALF_UP),
            **data,
        )
        orden.full_clean()
        orden.save()

        items_a_crear = []
        for item_data, calc in zip(items_data, calculos, strict=False):
            item = ItemOrdenCompra(
                empresa=empresa,
                orden_compra=orden,
                descripcion=item_data.get("descripcion"),
                item_inventario_uuid=item_data.get("item_inventario_uuid"),
                requisicion_item_uuid=item_data.get("requisicion_item_uuid"),
                cantidad=calc["cantidad"],
                valor_unitario=calc["valor_unitario"],
                porcentaje_iva=calc["porcentaje_iva"],
                valor_iva=calc["iva"],
                subtotal=calc["subtotal"],
                total=calc["total"],
            )
            item.full_clean()
            items_a_crear.append(item)

        ItemOrdenCompra.objects.bulk_create(items_a_crear)

        logger.info(f"[OrdenCompraCRUD] Creada Orden ID={orden.id}, Consecutivo={consecutivo}")
        return orden

    @staticmethod
    @transaction.atomic
    def actualizar_orden(orden: OrdenCompra, data: dict, items_data: list = None) -> OrdenCompra:
        """
        Actualiza los datos de la cabecera y opcionalmente reemplaza todos sus items.
        """
        # Solo permitir edicion si esta en BORRADOR o PENDIENTE
        if orden.estado not in ["BORRADOR", "PENDIENTE"]:
            raise ValidationError(
                f"No se puede modificar una orden de compra en estado {orden.estado}."
            )

        data = data.copy()
        data.pop("items", None)
        # Actualizar campos de cabecera proporcionados
        for field, val in data.items():
            setattr(orden, field, val)

        if items_data is not None:
            if not items_data:
                raise ValidationError("Una orden de compra debe contener al menos un item.")

            # Fase 6 (PLAN_OPTIMIZACION_COMPRAS...): sincronizacion
            # diferencial por UUID en vez de DELETE-todos + INSERT-todos.
            # item_data trae 'uuid' solo cuando el frontend edita una fila
            # existente (ver ItemOrdenCompraSerializer.uuid, required=False);
            # sin 'uuid' (o con uno que ya no existe) se trata como item
            # nuevo. Preserva `requisicion_item_uuid` de los items existentes
            # (nunca llega desde el frontend en edicion -- no se sobreescribe).
            existentes = {str(item.uuid): item for item in orden.items.all()}
            uuids_entrantes = set()
            items_a_crear = []
            items_a_actualizar = []
            subtotal = Decimal("0.00")
            impuestos = Decimal("0.00")
            total = Decimal("0.00")

            for item_data in items_data:
                calc = _calcular_item(item_data)
                subtotal += calc["subtotal"]
                impuestos += calc["iva"]
                total += calc["total"]

                item_uuid = item_data.get("uuid")
                existente = existentes.get(str(item_uuid)) if item_uuid else None

                if existente:
                    uuids_entrantes.add(str(item_uuid))
                    existente.descripcion = item_data.get("descripcion")
                    existente.item_inventario_uuid = item_data.get("item_inventario_uuid")
                    existente.cantidad = calc["cantidad"]
                    existente.valor_unitario = calc["valor_unitario"]
                    existente.porcentaje_iva = calc["porcentaje_iva"]
                    existente.valor_iva = calc["iva"]
                    existente.subtotal = calc["subtotal"]
                    existente.total = calc["total"]
                    existente.full_clean()
                    items_a_actualizar.append(existente)
                else:
                    nuevo = ItemOrdenCompra(
                        empresa=orden.empresa,
                        orden_compra=orden,
                        descripcion=item_data.get("descripcion"),
                        item_inventario_uuid=item_data.get("item_inventario_uuid"),
                        requisicion_item_uuid=item_data.get("requisicion_item_uuid"),
                        cantidad=calc["cantidad"],
                        valor_unitario=calc["valor_unitario"],
                        porcentaje_iva=calc["porcentaje_iva"],
                        valor_iva=calc["iva"],
                        subtotal=calc["subtotal"],
                        total=calc["total"],
                    )
                    nuevo.full_clean()
                    items_a_crear.append(nuevo)

            uuids_a_eliminar = set(existentes.keys()) - uuids_entrantes
            if uuids_a_eliminar:
                orden.items.filter(uuid__in=uuids_a_eliminar).delete()
            if items_a_crear:
                ItemOrdenCompra.objects.bulk_create(items_a_crear)
            if items_a_actualizar:
                ItemOrdenCompra.objects.bulk_update(
                    items_a_actualizar,
                    [
                        "descripcion",
                        "item_inventario_uuid",
                        "cantidad",
                        "valor_unitario",
                        "porcentaje_iva",
                        "valor_iva",
                        "subtotal",
                        "total",
                    ],
                )

            orden.subtotal = subtotal.quantize(_TWO, rounding=ROUND_HALF_UP)
            orden.impuestos = impuestos.quantize(_TWO, rounding=ROUND_HALF_UP)
            orden.total = total.quantize(_TWO, rounding=ROUND_HALF_UP)

        orden.full_clean()
        orden.save()

        logger.info(f"[OrdenCompraCRUD] Actualizada Orden ID={orden.id}")
        return orden

    @staticmethod
    @transaction.atomic
    def cambiar_estado(orden: OrdenCompra, nuevo_estado: str) -> OrdenCompra:
        """
        Cambia el estado de una orden de compra.
        """
        valido = False
        for choice in OrdenCompra.ESTADO_CHOICES:
            if choice[0] == nuevo_estado:
                valido = True
                break

        if not valido:
            raise ValidationError(f"Estado '{nuevo_estado}' no es valido.")

        orden.estado = nuevo_estado
        # BUG (2026-09-12, hallazgo CO-4): Django solo refresca un campo
        # auto_now=True (updated_at) si esta incluido en update_fields --
        # sin 'updated_at' aqui, una transicion de estado (Aprobar/Anular)
        # no dejaba ningun rastro de CUANDO ocurrio.
        orden.save(update_fields=["estado", "updated_at"])
        logger.info(f"[OrdenCompraCRUD] Cambio de estado Orden ID={orden.id} a {nuevo_estado}")
        return orden

    @staticmethod
    @transaction.atomic
    def vincular_factura(orden: OrdenCompra, factura) -> OrdenCompra:
        """
        FACTURAS-UI-CRONO-01: asigna manualmente la Factura (naturaleza
        COMPRA) ya persistida en el modulo Facturas -- mismo patron que
        VentaCRUDService.vincular_factura() (apps/tenant/ventas/services/
        crud_service.py). A diferencia de Ventas, OrdenCompra.ESTADO_CHOICES
        no tiene un estado equivalente a FACTURADA_DIAN -- no se inventa
        uno nuevo aqui (regla explicita de la mision), el estado de la
        orden no cambia por este vinculo.
        """
        orden.factura_asociada = factura
        orden.save(update_fields=["factura_asociada"])
        logger.info(
            "[OrdenCompraCRUD] Orden ID=%s vinculada manualmente a Factura ID=%s",
            orden.id,
            factura.id,
        )
        return orden

    @staticmethod
    @transaction.atomic
    def desvincular_factura(orden: OrdenCompra) -> OrdenCompra:
        """
        PLAN_VINCULAR_FACTURA_COMPRA_COMPRAS: contraparte de vincular_factura()
        -- limpia unicamente el vinculo (factura_asociada=None). Nunca toca ni
        elimina la Factura real en Facturas (SSoT fiscal intacto).
        """
        factura_id_previo = orden.factura_asociada_id
        orden.factura_asociada = None
        orden.save(update_fields=["factura_asociada"])
        logger.info(
            "[OrdenCompraCRUD] Orden ID=%s desvinculada de Factura ID=%s",
            orden.id,
            factura_id_previo,
        )
        return orden

    @staticmethod
    @transaction.atomic
    def eliminar_orden(orden: OrdenCompra) -> None:
        """
        Elimina fisicamente una orden de compra si esta en estado Borrador.
        """
        if orden.estado != "BORRADOR":
            raise ValidationError("Solo se pueden eliminar ordenes de compra en estado Borrador.")

        orden_id = orden.id
        orden.delete()
        logger.info(f"[OrdenCompraCRUD] Eliminada fisicamente Orden ID={orden_id}")


class RecepcionCompraCRUDService:
    """
    Operaciones CRUD puras y persistencia transaccional para RecepcionCompra (F21).
    Toda validacion de negocio (estado de la orden, cantidades pendientes,
    pertenencia de items) vive en RecepcionCompraBusinessService — esta capa
    solo persiste lo que ya fue validado.
    """

    @staticmethod
    @transaction.atomic
    def crear_recepcion(
        *, empresa, sede, orden_compra, usuario, fecha, items_data: list, observaciones: str = ""
    ) -> RecepcionCompra:
        recepcion = RecepcionCompra(
            empresa=empresa,
            sede=sede,
            orden_compra=orden_compra,
            usuario=usuario,
            fecha=fecha,
            observaciones=observaciones,
        )
        recepcion.full_clean()
        recepcion.save()

        if not items_data:
            raise ValidationError("Una recepcion de compra debe contener al menos un item.")

        items_a_crear = []
        for item_data in items_data:
            item = RecepcionCompraItem(
                empresa=empresa,
                recepcion=recepcion,
                item_orden_compra=item_data["item_orden_compra"],
                cantidad_recibida=item_data["cantidad_recibida"],
                observaciones=item_data.get("observaciones", ""),
            )
            item.full_clean()
            items_a_crear.append(item)
        RecepcionCompraItem.objects.bulk_create(items_a_crear)

        logger.info(
            "[RecepcionCompraCRUD] Recepcion id=%s creada para orden_compra_id=%s (%s items)",
            recepcion.id,
            orden_compra.id,
            len(items_a_crear),
        )
        return recepcion

    @staticmethod
    @transaction.atomic
    def marcar_confirmada(recepcion: RecepcionCompra) -> RecepcionCompra:
        recepcion.estado = RecepcionCompra.Estado.CONFIRMADA
        recepcion.save(update_fields=["estado"])
        logger.info("[RecepcionCompraCRUD] Recepcion id=%s confirmada", recepcion.id)
        return recepcion

    @staticmethod
    @transaction.atomic
    def anular(recepcion: RecepcionCompra) -> RecepcionCompra:
        recepcion.estado = RecepcionCompra.Estado.ANULADA
        recepcion.save(update_fields=["estado"])
        logger.info("[RecepcionCompraCRUD] Recepcion id=%s anulada", recepcion.id)
        return recepcion
