import logging
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction, models

_TWO = Decimal('0.01')
from rest_framework.exceptions import ValidationError

from apps.tenant.compras.models import OrdenCompra, ItemOrdenCompra, PlantillaOrdenCompra
from apps.tenant.empresa.models import Empresa

logger = logging.getLogger(__name__)


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
            "nombre", "prefijo", "rango_desde", "rango_hasta",
            "consecutivo_actual", "vigente",
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
        data = data.copy()
        consecutivo = data.pop('consecutivo')
        numero_documento = data.pop('numero_documento')
        plantilla = data.pop('plantilla')
        data.pop('items', None)

        # Calculo preliminar de totales de cabecera a partir de los items
        subtotal = Decimal('0.00')
        impuestos = Decimal('0.00')
        total = Decimal('0.00')

        # Crear instancia de la orden
        orden = OrdenCompra(
            empresa=empresa,
            sede=sede,
            consecutivo=consecutivo,
            numero_documento=numero_documento,
            plantilla=plantilla,
            subtotal=subtotal,
            impuestos=impuestos,
            total=total,
            **data
        )
        orden.full_clean()
        orden.save()

        # Crear items
        items_a_crear = []
        for item_data in items_data:
            # Calcular subtotal, iva y total a nivel de item
            cant = Decimal(str(item_data.get('cantidad', 0)))
            val_uni = Decimal(str(item_data.get('valor_unitario', 0)))
            pct_iva = Decimal(str(item_data.get('porcentaje_iva', 0)))

            item_sub = (cant * val_uni).quantize(_TWO, rounding=ROUND_HALF_UP)
            item_iva = (item_sub * (pct_iva / Decimal('100'))).quantize(_TWO, rounding=ROUND_HALF_UP)
            item_tot = (item_sub + item_iva).quantize(_TWO, rounding=ROUND_HALF_UP)

            subtotal += item_sub
            impuestos += item_iva
            total += item_tot

            item = ItemOrdenCompra(
                empresa=empresa,
                orden_compra=orden,
                descripcion=item_data.get('descripcion'),
                item_inventario_uuid=item_data.get('item_inventario_uuid'),
                cantidad=cant,
                valor_unitario=val_uni,
                porcentaje_iva=pct_iva,
                valor_iva=item_iva,
                subtotal=item_sub,
                total=item_tot
            )
            item.full_clean()
            items_a_crear.append(item)

        if not items_a_crear:
            raise ValidationError("Una orden de compra debe contener al menos un item.")

        ItemOrdenCompra.objects.bulk_create(items_a_crear)

        # Actualizar totales de la cabecera
        orden.subtotal = subtotal.quantize(_TWO, rounding=ROUND_HALF_UP)
        orden.impuestos = impuestos.quantize(_TWO, rounding=ROUND_HALF_UP)
        orden.total = total.quantize(_TWO, rounding=ROUND_HALF_UP)
        orden.save(update_fields=['subtotal', 'impuestos', 'total'])

        logger.info(f"[OrdenCompraCRUD] Creada Orden ID={orden.id}, Consecutivo={consecutivo}")
        return orden

    @staticmethod
    @transaction.atomic
    def actualizar_orden(orden: OrdenCompra, data: dict, items_data: list = None) -> OrdenCompra:
        """
        Actualiza los datos de la cabecera y opcionalmente reemplaza todos sus items.
        """
        # Solo permitir edicion si esta en BORRADOR o PENDIENTE
        if orden.estado not in ['BORRADOR', 'PENDIENTE']:
            raise ValidationError(
                f"No se puede modificar una orden de compra en estado {orden.estado}."
            )

        data = data.copy()
        data.pop('items', None)
        # Actualizar campos de cabecera proporcionados
        for field, val in data.items():
            setattr(orden, field, val)

        if items_data is not None:
            # Eliminar items existentes
            orden.items.all().delete()

            # Recalcular e insertar nuevos items
            subtotal = Decimal('0.00')
            impuestos = Decimal('0.00')
            total = Decimal('0.00')

            items_a_crear = []
            for item_data in items_data:
                cant = Decimal(str(item_data.get('cantidad', 0)))
                val_uni = Decimal(str(item_data.get('valor_unitario', 0)))
                pct_iva = Decimal(str(item_data.get('porcentaje_iva', 0)))

                item_sub = (cant * val_uni).quantize(_TWO, rounding=ROUND_HALF_UP)
                item_iva = (item_sub * (pct_iva / Decimal('100'))).quantize(_TWO, rounding=ROUND_HALF_UP)
                item_tot = (item_sub + item_iva).quantize(_TWO, rounding=ROUND_HALF_UP)

                subtotal += item_sub
                impuestos += item_iva
                total += item_tot

                item = ItemOrdenCompra(
                    empresa=orden.empresa,
                    orden_compra=orden,
                    descripcion=item_data.get('descripcion'),
                    item_inventario_uuid=item_data.get('item_inventario_uuid'),
                    cantidad=cant,
                    valor_unitario=val_uni,
                    porcentaje_iva=pct_iva,
                    valor_iva=item_iva,
                    subtotal=item_sub,
                    total=item_tot
                )
                item.full_clean()
                items_a_crear.append(item)

            if not items_a_crear:
                raise ValidationError("Una orden de compra debe contener al menos un item.")

            ItemOrdenCompra.objects.bulk_create(items_a_crear)

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
        orden.save(update_fields=['estado'])
        logger.info(f"[OrdenCompraCRUD] Cambio de estado Orden ID={orden.id} a {nuevo_estado}")
        return orden

    @staticmethod
    @transaction.atomic
    def eliminar_orden(orden: OrdenCompra) -> None:
        """
        Elimina fisicamente una orden de compra si esta en estado Borrador.
        """
        if orden.estado != 'BORRADOR':
            raise ValidationError("Solo se pueden eliminar ordenes de compra en estado Borrador.")

        orden_id = orden.id
        orden.delete()
        logger.info(f"[OrdenCompraCRUD] Eliminada fisicamente Orden ID={orden_id}")

    @staticmethod
    def _obtener_siguiente_consecutivo(empresa: Empresa) -> int:
        """
        Calcula el siguiente consecutivo de la empresa de manera secuencial.
        """
        ultimo = OrdenCompra.objects.filter(
            empresa=empresa
        ).aggregate(max_val=models.Max('consecutivo'))['max_val']

        return (ultimo + 1) if ultimo else 1
