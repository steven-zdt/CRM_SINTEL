import logging
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import ValidationError

from apps.tenant.compras.requisiciones.models import (
    RequisicionCompra,
    RequisicionCompraItem,
    RequisicionHistorialEstado,
)
from apps.tenant.empresa.models import Empresa

_TWO = Decimal("0.01")
logger = logging.getLogger(__name__)

_CAMPOS_EDITABLES_CABECERA = (
    "fecha_necesidad",
    "tipo",
    "prioridad",
    "justificacion",
    "observaciones",
    "proyecto",
    "moneda",
    "responsable_aprobacion",
    # Cliente si es editable en BORRADOR (documento original #13); Plantilla
    # y numero_documento NUNCA (#22 del mismo documento -- ya asignados de
    # forma atomica en la creacion, ver crear_requisicion).
    "cliente",
    # Fecha de Solicitud -- PLAN_NUEVA_REQUISICION_FORMULARIO.md #6: pasa de
    # default silencioso a campo explicito, editable en BORRADOR (mismo
    # criterio que fecha_necesidad).
    "fecha_solicitud",
)


def _calcular_item(item_data: dict) -> dict:
    cant = Decimal(str(item_data.get("cantidad_solicitada", 0)))
    val_uni = Decimal(str(item_data.get("valor_unitario_estimado", 0)))
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


class RequisicionCompraCRUDService:
    """Operaciones CRUD puras y persistencia transaccional para RequisicionCompra."""

    # `asignar_siguiente_numero` (Max(consecutivo)+1 propio, sin plantilla)
    # se retiro en PLAN_NUEVA_REQUISICION_NUMERACION_CLIENTE_COTIZACIONES.md
    # Fase B -- la numeracion ahora la asigna
    # OrdenCompraBusinessService._dsv_y_asignar_plantilla() (motor
    # compartido con OrdenCompra), llamado directamente desde
    # RequisicionCompraBusinessService.crear_requisicion().

    @staticmethod
    @transaction.atomic
    def crear_requisicion(
        data: dict, items_data: list, empresa: Empresa, sede
    ) -> RequisicionCompra:
        """Crea la cabecera + items dentro de una transaccion. `data` ya trae
        `numero_documento`/`consecutivo` asignados por el BusinessService."""
        if not items_data:
            raise ValidationError("Una requisicion de compra debe contener al menos un item.")

        data = data.copy()
        numero_documento = data.pop("numero_documento")
        consecutivo = data.pop("consecutivo")
        data.pop("items", None)

        # Fase 7 (PLAN_OPTIMIZACION_COMPRAS...): totales calculados ANTES de
        # crear la cabecera -- un solo save(), sin el segundo update()
        # posterior para corregir los totales en 0 iniciales.
        calculos = [_calcular_item(item_data) for item_data in items_data]
        subtotal = sum((c["subtotal"] for c in calculos), Decimal("0.00"))
        impuestos = sum((c["iva"] for c in calculos), Decimal("0.00"))
        total = sum((c["total"] for c in calculos), Decimal("0.00"))

        requisicion = RequisicionCompra(
            empresa=empresa,
            sede=sede,
            numero_documento=numero_documento,
            consecutivo=consecutivo,
            subtotal_estimado=subtotal.quantize(_TWO, rounding=ROUND_HALF_UP),
            impuestos_estimados=impuestos.quantize(_TWO, rounding=ROUND_HALF_UP),
            total_estimado=total.quantize(_TWO, rounding=ROUND_HALF_UP),
            **data,
        )
        requisicion.full_clean()
        requisicion.save()

        items_a_crear = []
        for item_data, calc in zip(items_data, calculos, strict=False):
            item = RequisicionCompraItem(
                empresa=empresa,
                requisicion=requisicion,
                descripcion=item_data.get("descripcion"),
                item_inventario_uuid=item_data.get("item_inventario_uuid"),
                tipo_item=item_data.get("tipo_item"),
                cantidad_solicitada=calc["cantidad"],
                unidad_medida=item_data.get("unidad_medida", "UND"),
                valor_unitario_estimado=calc["valor_unitario"],
                porcentaje_iva=calc["porcentaje_iva"],
                valor_iva_estimado=calc["iva"],
                subtotal_estimado=calc["subtotal"],
                total_estimado=calc["total"],
                observaciones=item_data.get("observaciones", ""),
            )
            item.full_clean()
            items_a_crear.append(item)

        RequisicionCompraItem.objects.bulk_create(items_a_crear)

        logger.info(
            "[RequisicionCRUD] Creada Requisicion id=%s numero=%s",
            requisicion.id,
            numero_documento,
        )
        return requisicion

    @staticmethod
    @transaction.atomic
    def actualizar_requisicion(
        requisicion: RequisicionCompra, data: dict, items_data: list = None
    ) -> RequisicionCompra:
        """Solo editable en BORRADOR (mismo criterio que
        OrdenCompraCRUDService.actualizar_orden -- 'no se puede modificar
        estando fuera de los estados editables')."""
        if requisicion.estado != RequisicionCompra.Estado.BORRADOR:
            raise ValidationError(
                f"No se puede modificar una requisicion en estado {requisicion.estado}."
            )

        data = data.copy()
        data.pop("items", None)
        for campo in _CAMPOS_EDITABLES_CABECERA:
            if campo in data:
                setattr(requisicion, campo, data[campo])

        if items_data is not None:
            if not items_data:
                raise ValidationError("Una requisicion de compra debe contener al menos un item.")

            # Fase 6 (PLAN_OPTIMIZACION_COMPRAS...): sincronizacion
            # diferencial por UUID -- mismo patron que
            # OrdenCompraCRUDService.actualizar_orden(). `cantidad_aprobada`/
            # `cantidad_ordenada`/`cantidad_cancelada` de un item existente
            # NUNCA se tocan aqui (no llegan en item_data, es progreso
            # gestionado por otros flujos) -- se preservan intactas al editar
            # solo los campos propios del formulario.
            existentes = {str(item.uuid): item for item in requisicion.items.all()}
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
                    existente.tipo_item = item_data.get("tipo_item")
                    existente.cantidad_solicitada = calc["cantidad"]
                    existente.unidad_medida = item_data.get("unidad_medida", "UND")
                    existente.valor_unitario_estimado = calc["valor_unitario"]
                    existente.porcentaje_iva = calc["porcentaje_iva"]
                    existente.valor_iva_estimado = calc["iva"]
                    existente.subtotal_estimado = calc["subtotal"]
                    existente.total_estimado = calc["total"]
                    existente.observaciones = item_data.get("observaciones", "")
                    existente.full_clean()
                    items_a_actualizar.append(existente)
                else:
                    nuevo = RequisicionCompraItem(
                        empresa=requisicion.empresa,
                        requisicion=requisicion,
                        descripcion=item_data.get("descripcion"),
                        item_inventario_uuid=item_data.get("item_inventario_uuid"),
                        tipo_item=item_data.get("tipo_item"),
                        cantidad_solicitada=calc["cantidad"],
                        unidad_medida=item_data.get("unidad_medida", "UND"),
                        valor_unitario_estimado=calc["valor_unitario"],
                        porcentaje_iva=calc["porcentaje_iva"],
                        valor_iva_estimado=calc["iva"],
                        subtotal_estimado=calc["subtotal"],
                        total_estimado=calc["total"],
                        observaciones=item_data.get("observaciones", ""),
                    )
                    nuevo.full_clean()
                    items_a_crear.append(nuevo)

            uuids_a_eliminar = set(existentes.keys()) - uuids_entrantes
            if uuids_a_eliminar:
                requisicion.items.filter(uuid__in=uuids_a_eliminar).delete()
            if items_a_crear:
                RequisicionCompraItem.objects.bulk_create(items_a_crear)
            if items_a_actualizar:
                RequisicionCompraItem.objects.bulk_update(
                    items_a_actualizar,
                    [
                        "descripcion",
                        "item_inventario_uuid",
                        "tipo_item",
                        "cantidad_solicitada",
                        "unidad_medida",
                        "valor_unitario_estimado",
                        "porcentaje_iva",
                        "valor_iva_estimado",
                        "subtotal_estimado",
                        "total_estimado",
                        "observaciones",
                    ],
                )

            requisicion.subtotal_estimado = subtotal.quantize(_TWO, rounding=ROUND_HALF_UP)
            requisicion.impuestos_estimados = impuestos.quantize(_TWO, rounding=ROUND_HALF_UP)
            requisicion.total_estimado = total.quantize(_TWO, rounding=ROUND_HALF_UP)

        requisicion.full_clean()
        requisicion.save()
        logger.info("[RequisicionCRUD] Actualizada Requisicion id=%s", requisicion.id)
        return requisicion

    @staticmethod
    @transaction.atomic
    def eliminar_requisicion(requisicion: RequisicionCompra) -> None:
        """Solo BORRADOR y sin dependencias reales (ordenes/facturas/
        cotizaciones ADICIONALES a la de origen) -- plan original #39
        ("No permitir DELETE fisico de una requisicion que tenga OrdenCompra/
        Cotizacion/Factura/Recepcion").

        Hallazgo real (2026-09-26, auditoria "evita redundancias"): el
        docstring ya afirmaba este comportamiento pero el codigo solo
        verificaba `ordenes_compra` -- Recepcion queda cubierto
        transitivamente (nunca existe sin una OrdenCompra). La Cotizacion de
        ORIGEN (obligatoria desde 2026-09-26, ver
        RequisicionCompraBusinessService.crear_requisicion) se excluye a
        proposito de este bloqueo: toda requisicion BORRADOR la tiene desde
        que nace, bloquearla por eso volveria indeletable cualquier borrador
        recien creado -- solo bloquea una cotizacion/factura ADICIONAL
        vinculada despues (via vincular_cotizacion/vincular_factura o
        sincronizacion desde Proyecto), que si es trazabilidad real que no
        debe destruirse."""
        if requisicion.estado != RequisicionCompra.Estado.BORRADOR:
            raise ValidationError(
                "Solo se puede eliminar una requisicion en estado BORRADOR. Use CANCELADA para las demas."
            )
        if requisicion.ordenes_compra_vinculadas.exists():
            raise ValidationError(
                "No se puede eliminar una requisicion con ordenes de compra generadas."
            )
        if requisicion.cotizaciones_vinculadas.exclude(tipo_relacion="ORIGEN").exists():
            raise ValidationError(
                "No se puede eliminar una requisicion con cotizaciones adicionales vinculadas."
            )
        if requisicion.facturas_vinculadas.exists():
            raise ValidationError("No se puede eliminar una requisicion con facturas vinculadas.")
        requisicion_id = requisicion.id
        requisicion.delete()
        logger.info("[RequisicionCRUD] Eliminada Requisicion id=%s", requisicion_id)

    @staticmethod
    @transaction.atomic
    def cambiar_estado(
        requisicion: RequisicionCompra, nuevo_estado: str, *, usuario=None, comentario: str = ""
    ) -> RequisicionCompra:
        """Escritura de bajo nivel del cambio de estado + historial
        append-only. La validacion de TRANSICIONES_VALIDAS vive en el
        BusinessService -- este metodo asume que ya fue validada."""
        estado_anterior = requisicion.estado
        requisicion.estado = nuevo_estado
        requisicion.save(update_fields=["estado", "updated_at"])

        RequisicionHistorialEstado.objects.create(
            empresa_id=requisicion.empresa_id,
            requisicion=requisicion,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            usuario=usuario,
            comentario=comentario or "",
        )
        logger.info(
            "[RequisicionCRUD] estado %s -> %s (id=%s)",
            estado_anterior,
            nuevo_estado,
            requisicion.id,
        )
        return requisicion

    @staticmethod
    @transaction.atomic
    def acumular_cantidad_ordenada(
        item: RequisicionCompraItem, cantidad: Decimal
    ) -> RequisicionCompraItem:
        """Incremento atomico bajo select_for_update -- llamado por
        RequisicionCompraBusinessService.crear_orden_desde_requisicion()
        dentro de la misma transaccion que crea la OrdenCompra."""
        RequisicionCompraItem.objects.filter(pk=item.pk).update(
            cantidad_ordenada=F("cantidad_ordenada") + cantidad,
        )
        item.refresh_from_db(fields=["cantidad_ordenada"])
        return item
