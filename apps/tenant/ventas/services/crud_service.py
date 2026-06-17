"""
CRUD Service para Ventas - Persistencia transaccional pura.

Responsabilidad: Operaciones DML (Create/Update/Delete) sin logica de negocio.
Todas las funciones son @staticmethod y estan envueltas en @transaction.atomic.
"""
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.tenant.ventas.models import OrdenVenta, ItemOrdenVenta

logger = logging.getLogger(__name__)


class OrdenVentaCRUDService:
    """Operaciones CRUD puras para OrdenVenta e ItemOrdenVenta."""

    @staticmethod
    def _calcular_totales_desde_items(items_data: List[Dict[str, Any]]) -> Dict[str, Decimal]:
        """Calcula subtotal, impuestos y total a partir de la lista de items."""
        subtotal = Decimal("0.00")
        impuestos = Decimal("0.00")

        for item in items_data:
            cantidad = Decimal(str(item.get("cantidad", "1")))
            precio = Decimal(str(item.get("precio_unitario", "0")))
            tasa_iva = Decimal(str(item.get("tasa_iva", "0")))

            subtotal_linea = cantidad * precio
            iva_linea = subtotal_linea * (tasa_iva / Decimal("100"))

            subtotal += subtotal_linea
            impuestos += iva_linea

        return {
            "subtotal": subtotal.quantize(Decimal("0.01")),
            "impuestos": impuestos.quantize(Decimal("0.01")),
            "total": (subtotal + impuestos).quantize(Decimal("0.01")),
        }

    @staticmethod
    @transaction.atomic
    def crear_orden(
        data: Dict[str, Any],
        empresa,
        items_data: Optional[List[Dict[str, Any]]] = None,
    ) -> OrdenVenta:
        """
        Crea OrdenVenta con sus items.

        Args:
            data: Campos de la cabecera de la orden.
            empresa: Instancia de Empresa (SSoT).
            items_data: Lista de dicts con campos de ItemOrdenVenta.
        """
        items_data = items_data or []

        totales = OrdenVentaCRUDService._calcular_totales_desde_items(items_data)

        orden = OrdenVenta(
            empresa=empresa,
            subtotal=totales["subtotal"],
            impuestos=totales["impuestos"],
            total=totales["total"],
            **{k: v for k, v in data.items() if k not in ("subtotal", "impuestos", "total")},
        )
        orden.full_clean()
        orden.save()

        OrdenVentaCRUDService._crear_items(orden, empresa, items_data)

        logger.info("[OrdenVentaCRUD] Creada orden id=%s empresa=%s", orden.id, empresa.id)
        return orden

    @staticmethod
    @transaction.atomic
    def actualizar_orden(
        orden: OrdenVenta,
        data: Dict[str, Any],
        empresa,
        items_data: Optional[List[Dict[str, Any]]] = None,
    ) -> OrdenVenta:
        """
        Actualiza OrdenVenta. Si se proveen items_data, reemplaza todos los items.

        Args:
            orden: Instancia existente de OrdenVenta.
            data: Campos a actualizar en la cabecera.
            empresa: Instancia de Empresa (para DSV).
            items_data: Si se proporciona, reemplaza todos los items actuales.
        """
        campos_protegidos = {"empresa", "empresa_id", "uuid", "factura", "factura_id"}

        for campo, valor in data.items():
            if campo in campos_protegidos:
                continue
            if campo not in ("subtotal", "impuestos", "total"):
                setattr(orden, campo, valor)

        if items_data is not None:
            orden.items.all().delete()
            totales = OrdenVentaCRUDService._calcular_totales_desde_items(items_data)
            orden.subtotal = totales["subtotal"]
            orden.impuestos = totales["impuestos"]
            orden.total = totales["total"]
            OrdenVentaCRUDService._crear_items(orden, empresa, items_data)

        orden.full_clean()
        orden.save()

        logger.info("[OrdenVentaCRUD] Actualizada orden id=%s", orden.id)
        return orden

    @staticmethod
    def _crear_items(
        orden: OrdenVenta,
        empresa,
        items_data: List[Dict[str, Any]],
    ) -> None:
        """Crea ItemOrdenVenta en bulk para la orden."""
        items_bulk = []
        for item in items_data:
            cantidad = Decimal(str(item.get("cantidad", "1")))
            precio = Decimal(str(item.get("precio_unitario", "0")))
            tasa_iva = Decimal(str(item.get("tasa_iva", "0")))

            items_bulk.append(
                ItemOrdenVenta(
                    empresa=empresa,
                    orden=orden,
                    descripcion=item.get("descripcion", ""),
                    cantidad=cantidad,
                    precio_unitario=precio,
                    tasa_iva=tasa_iva,
                    subtotal=cantidad * precio,
                    producto_id=item.get("producto_id"),
                    servicio_id=item.get("servicio_id"),
                )
            )

        if items_bulk:
            ItemOrdenVenta.objects.bulk_create(items_bulk)

    @staticmethod
    @transaction.atomic
    def anular_orden(orden: OrdenVenta, motivo: str) -> OrdenVenta:
        """Marca la orden como ANULADA (inmutable, no se puede revertir)."""
        if orden.estado == OrdenVenta.Estado.ANULADA:
            raise ValidationError("La orden ya se encuentra anulada.")
        if orden.estado == OrdenVenta.Estado.FACTURADA:
            raise ValidationError(
                "No se puede anular una orden ya facturada. Anule la factura primero."
            )
        orden.estado = OrdenVenta.Estado.ANULADA
        if motivo:
            orden.observaciones = f"[ANULADA] {motivo}\n{orden.observaciones}".strip()
        orden.save(update_fields=["estado", "observaciones", "updated_at"])
        logger.info("[OrdenVentaCRUD] Anulada orden id=%s", orden.id)
        return orden

    @staticmethod
    @transaction.atomic
    def vincular_factura(orden: OrdenVenta, factura) -> OrdenVenta:
        """Vincula una Factura generada a la orden y cambia estado a FACTURADA."""
        orden.factura = factura
        orden.estado = OrdenVenta.Estado.FACTURADA
        orden.save(update_fields=["factura", "estado", "updated_at"])
        logger.info(
            "[OrdenVentaCRUD] Vinculada factura id=%s a orden id=%s",
            factura.id,
            orden.id,
        )
        return orden
