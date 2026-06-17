"""
Business Service para Ventas - Logica de negocio y orquestacion.

Responsabilidades:
- Double Semantic Verification (DSV): validar que cliente e items pertenezcan a empresa.
- Maquina de estados de OrdenVenta.
- Orquestar generacion de Factura via FacturaCRUDService (sin importar contabilidad).

Lazy imports para dependencias cross-domain (facturas, inventario) para evitar
importaciones circulares al momento de carga del modulo.
"""
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.tenant.ventas.models import OrdenVenta, ItemOrdenVenta
from apps.tenant.ventas.services.crud_service import OrdenVentaCRUDService

logger = logging.getLogger(__name__)


class OrdenVentaBusinessService:
    """
    Logica de negocio centralizada para OrdenVenta.
    SSoT para validaciones, DSV y orquestacion de procesos.
    """

    # --------------------------------------------------------------------------
    # DSV Helpers
    # --------------------------------------------------------------------------

    @staticmethod
    def _dsv_cliente(cliente_id: int, empresa_id: int) -> None:
        """Verifica que el cliente pertenezca a la empresa (DSV)."""
        from apps.tenant.clientes.models import Cliente

        existe = Cliente.objects.filter(
            id=cliente_id,
            empresa_id=empresa_id,
        ).exists()
        if not existe:
            raise ValidationError(
                f"El cliente id={cliente_id} no pertenece a esta empresa."
            )

    @staticmethod
    def _dsv_items(items_data: List[Dict[str, Any]], empresa_id: int) -> None:
        """
        Verifica DSV para cada item: producto o servicio debe pertenecer a la empresa.
        Cada item debe referenciar exactamente uno de: producto_id, servicio_id, o ninguno
        (item libre con solo descripcion).
        """
        from apps.tenant.inventario.models import Producto, Servicio

        for idx, item in enumerate(items_data):
            producto_id = item.get("producto_id")
            servicio_id = item.get("servicio_id")

            if producto_id and servicio_id:
                raise ValidationError(
                    f"Item #{idx + 1}: no puede referenciar producto y servicio al mismo tiempo."
                )

            if producto_id:
                if not Producto.objects.filter(
                    id=producto_id,
                    empresa_id=empresa_id,
                ).exists():
                    raise ValidationError(
                        f"Item #{idx + 1}: producto id={producto_id} no pertenece a esta empresa."
                    )

            if servicio_id:
                if not Servicio.objects.filter(
                    id=servicio_id,
                    empresa_id=empresa_id,
                ).exists():
                    raise ValidationError(
                        f"Item #{idx + 1}: servicio id={servicio_id} no pertenece a esta empresa."
                    )

            if not item.get("descripcion", "").strip():
                raise ValidationError(
                    f"Item #{idx + 1}: el campo 'descripcion' es obligatorio."
                )

            precio = Decimal(str(item.get("precio_unitario", "0")))
            if precio < Decimal("0"):
                raise ValidationError(
                    f"Item #{idx + 1}: precio_unitario no puede ser negativo."
                )

    # --------------------------------------------------------------------------
    # Operaciones principales
    # --------------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def crear_orden(
        empresa,
        data: Dict[str, Any],
    ) -> OrdenVenta:
        """
        Crea una OrdenVenta con validacion DSV completa.

        Args:
            empresa: Instancia de Empresa (SSoT del tenant).
            data: Debe incluir 'cliente_id' y opcionalmente 'items'.
        """
        cliente_id = data.get("cliente_id") or data.get("cliente")
        if not cliente_id:
            raise ValidationError("El campo 'cliente' es obligatorio.")

        OrdenVentaBusinessService._dsv_cliente(cliente_id, empresa.id)

        items_data = data.pop("items", [])
        if items_data:
            OrdenVentaBusinessService._dsv_items(items_data, empresa.id)

        orden = OrdenVentaCRUDService.crear_orden(
            data=data,
            empresa=empresa,
            items_data=items_data,
        )
        return orden

    @staticmethod
    @transaction.atomic
    def actualizar_orden(
        empresa,
        orden: OrdenVenta,
        data: Dict[str, Any],
    ) -> OrdenVenta:
        """
        Actualiza una OrdenVenta existente con validacion DSV.

        Solo permite actualizar ordenes en estado BORRADOR o CONFIRMADA.
        """
        if orden.estado in (OrdenVenta.Estado.FACTURADA, OrdenVenta.Estado.ANULADA):
            raise ValidationError(
                f"No se puede modificar una orden en estado '{orden.estado}'."
            )

        if "cliente_id" in data or "cliente" in data:
            cliente_id = data.get("cliente_id") or data.get("cliente")
            OrdenVentaBusinessService._dsv_cliente(cliente_id, empresa.id)

        items_data = data.pop("items", None)
        if items_data is not None:
            OrdenVentaBusinessService._dsv_items(items_data, empresa.id)

        return OrdenVentaCRUDService.actualizar_orden(
            orden=orden,
            data=data,
            empresa=empresa,
            items_data=items_data,
        )

    @staticmethod
    @transaction.atomic
    def confirmar_orden(orden: OrdenVenta, empresa_id: int) -> OrdenVenta:
        """Transiciona la orden de BORRADOR a CONFIRMADA."""
        if orden.empresa_id != empresa_id:
            raise ValidationError("La orden no pertenece a esta empresa.")
        if orden.estado != OrdenVenta.Estado.BORRADOR:
            raise ValidationError(
                f"Solo se pueden confirmar ordenes en estado BORRADOR. Estado actual: '{orden.estado}'."
            )
        if not orden.items.exists():
            raise ValidationError("No se puede confirmar una orden sin items.")

        orden.estado = OrdenVenta.Estado.CONFIRMADA
        orden.save(update_fields=["estado", "updated_at"])
        logger.info("[OrdenVentaBusiness] Confirmada orden id=%s", orden.id)
        return orden

    @staticmethod
    @transaction.atomic
    def generar_factura(orden: OrdenVenta, empresa_id: int) -> Tuple[bool, Any, int]:
        """
        Genera una Factura de Venta a partir de una OrdenVenta CONFIRMADA.

        Flujo:
        1. Valida que la orden sea CONFIRMADA y pertenezca a la empresa.
        2. Prepara el payload de factura a partir de los datos de la orden.
        3. Llama a FacturaCRUDService para crear la Factura + ItemFactura en estado BORRADOR.
        4. Vincula la factura a la orden y cambia estado a FACTURADA.

        Returns:
            Tuple[bool, Any, int]: (exito, factura_o_detalle_error, http_status)
        """
        if orden.empresa_id != empresa_id:
            return False, {"detail": "La orden no pertenece a esta empresa."}, 403

        if orden.estado != OrdenVenta.Estado.CONFIRMADA:
            return False, {
                "detail": (
                    f"Solo se pueden facturar ordenes CONFIRMADAS. "
                    f"Estado actual: '{orden.estado}'."
                )
            }, 400

        try:
            from apps.tenant.facturas.services.crud_service import FacturaCRUDService
            from apps.tenant.facturas.models import Factura, ItemFactura
        except ImportError as exc:
            logger.error("[OrdenVentaBusiness] No se pudo importar facturas: %s", exc)
            return False, {"detail": "Modulo de facturas no disponible."}, 500

        try:
            empresa = orden.empresa
            cliente = orden.cliente
            items_qs = orden.items.select_related("producto", "servicio").all()

            numero_borrador = f"BORR-{str(orden.uuid).replace('-', '').upper()[:16]}"

            factura_data = {
                "empresa": empresa,
                "tipo": Factura.TipoFactura.FE,
                "estado": Factura.Estado.BORRADOR,
                "naturaleza": Factura.Naturaleza.VENTA,
                "numero": numero_borrador,
                "consecutivo": 0,
                "fecha_emision": timezone.now(),
                "subtotal": orden.subtotal,
                "impuestos": orden.impuestos,
                "total": orden.total,
                "cliente_uuid": cliente.uuid,
                "receptor_nombre": cliente.razon_social,
                "receptor_nit": cliente.numero_documento,
                "observaciones": orden.observaciones or "",
            }

            factura = FacturaCRUDService.crear(factura_data=factura_data)

            items_bulk = []
            for item in items_qs:
                item_inventario_uuid = None
                item_inventario_tipo = None
                item_inventario_codigo = None

                if item.producto_id and item.producto:
                    item_inventario_uuid = item.producto.uuid
                    item_inventario_tipo = ItemFactura.TipoItemInventario.PRODUCTO
                    item_inventario_codigo = item.producto.codigo
                elif item.servicio_id and item.servicio:
                    item_inventario_uuid = item.servicio.uuid
                    item_inventario_tipo = ItemFactura.TipoItemInventario.SERVICIO
                    item_inventario_codigo = item.servicio.codigo

                subtotal_linea = item.cantidad * item.precio_unitario
                valor_iva = subtotal_linea * (item.tasa_iva / Decimal("100"))

                items_bulk.append(
                    ItemFactura(
                        empresa=empresa,
                        factura=factura,
                        descripcion=item.descripcion,
                        cantidad=item.cantidad,
                        valor_unitario=item.precio_unitario,
                        porcentaje_iva=item.tasa_iva,
                        valor_iva=valor_iva,
                        subtotal=subtotal_linea,
                        total=subtotal_linea + valor_iva,
                        item_inventario_uuid=item_inventario_uuid,
                        item_inventario_tipo=item_inventario_tipo,
                        item_inventario_codigo=item_inventario_codigo,
                        orden=1,
                    )
                )

            if items_bulk:
                ItemFactura.objects.bulk_create(items_bulk)

            OrdenVentaCRUDService.vincular_factura(orden, factura)

            logger.info(
                "[OrdenVentaBusiness] Factura id=%s generada para orden id=%s",
                factura.id,
                orden.id,
            )
            return True, factura, 201

        except Exception as exc:
            logger.error(
                "[OrdenVentaBusiness] Error al generar factura para orden id=%s: %s",
                orden.id,
                exc,
                exc_info=True,
            )
            return False, {"detail": f"Error interno al generar factura: {str(exc)}"}, 500

    @staticmethod
    @transaction.atomic
    def anular_orden(
        orden: OrdenVenta,
        empresa_id: int,
        motivo: str,
    ) -> OrdenVenta:
        """Anula una OrdenVenta con validacion de pertenencia."""
        if orden.empresa_id != empresa_id:
            raise ValidationError("La orden no pertenece a esta empresa.")
        return OrdenVentaCRUDService.anular_orden(orden, motivo)
