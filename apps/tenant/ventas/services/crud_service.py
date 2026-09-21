"""
CRUD Service para Ventas - Persistencia transaccional pura.

Responsabilidad: DML sin logica de negocio.
"""
import logging
from decimal import Decimal

from django.db import transaction

from apps.tenant.ventas.models import ItemVenta, ResolucionFacturacion, Venta

logger = logging.getLogger(__name__)


class VentaCRUDService:
    """Operaciones de persistencia para Venta e ItemVenta."""

    @staticmethod
    @transaction.atomic
    def crear_venta(empresa, cliente, data: dict, items_data: list) -> Venta:
        """
        Crea un registro Venta (estado BORRADOR) junto con sus ItemVenta.
        Acepta opcionalmente data['resolucion'] y data['numero_factura'].
        Devuelve la instancia con totales calculados.
        """
        subtotal = Decimal("0.00")
        impuestos = Decimal("0.00")

        venta = Venta(
            empresa=empresa,
            cliente=cliente,
            proyecto=data.get("proyecto"),
            resolucion=data.get("resolucion"),
            fecha_emision=data["fecha_emision"],
            fecha_vencimiento=data.get("fecha_vencimiento"),
            observaciones=data.get("observaciones", ""),
            numero_factura=data.get("numero_factura"),
            estado=Venta.Estado.BORRADOR,
        )
        venta.save()

        items_a_crear = []
        for item in items_data:
            cant = Decimal(str(item.get("cantidad", "1")))
            pu = Decimal(str(item.get("precio_unitario", "0")))
            pct_iva = Decimal(str(item.get("porcentaje_iva", "0")))
            sub = cant * pu
            iva_item = sub * (pct_iva / Decimal("100"))
            subtotal += sub
            impuestos += iva_item

            items_a_crear.append(
                ItemVenta(
                    empresa=empresa,
                    venta=venta,
                    descripcion=item.get("descripcion", ""),
                    cantidad=cant,
                    precio_unitario=pu,
                    porcentaje_iva=pct_iva,
                    subtotal=sub,
                    producto_id=item.get("producto_id"),
                    servicio_id=item.get("servicio_id"),
                )
            )

        ItemVenta.objects.bulk_create(items_a_crear)

        venta.subtotal = subtotal
        venta.impuestos = impuestos
        venta.total_neto = subtotal + impuestos
        venta.save(update_fields=["subtotal", "impuestos", "total_neto"])

        logger.info("[VentaCRUD] Venta id=%s creada con %d items", venta.id, len(items_a_crear))
        return venta

    @staticmethod
    @transaction.atomic
    def actualizar_venta(venta: Venta, data: dict, items_data: list = None) -> Venta:
        """Actualiza cabecera y, si se proveen, reemplaza los items."""
        if venta.estado != Venta.Estado.BORRADOR:
            raise ValueError("Solo se puede editar una Venta en estado BORRADOR.")

        campos_cabecera = ["fecha_emision", "fecha_vencimiento", "observaciones", "proyecto"]
        for campo in campos_cabecera:
            if campo in data:
                setattr(venta, campo, data[campo])

        if items_data is not None:
            venta.items.all().delete()
            subtotal = Decimal("0.00")
            impuestos = Decimal("0.00")
            nuevos = []
            for item in items_data:
                cant = Decimal(str(item.get("cantidad", "1")))
                pu = Decimal(str(item.get("precio_unitario", "0")))
                pct_iva = Decimal(str(item.get("porcentaje_iva", "0")))
                sub = cant * pu
                subtotal += sub
                impuestos += sub * (pct_iva / Decimal("100"))
                nuevos.append(
                    ItemVenta(
                        empresa=venta.empresa,
                        venta=venta,
                        descripcion=item.get("descripcion", ""),
                        cantidad=cant,
                        precio_unitario=pu,
                        porcentaje_iva=pct_iva,
                        subtotal=sub,
                        producto_id=item.get("producto_id"),
                        servicio_id=item.get("servicio_id"),
                    )
                )
            ItemVenta.objects.bulk_create(nuevos)
            venta.subtotal = subtotal
            venta.impuestos = impuestos
            venta.total_neto = subtotal + impuestos

        venta.save()
        logger.info("[VentaCRUD] Venta id=%s actualizada", venta.id)
        return venta

    @staticmethod
    @transaction.atomic
    def vincular_factura(venta: Venta, factura) -> Venta:
        """Asigna la factura generada y pasa estado a FACTURADA_DIAN."""
        venta.factura_asociada = factura
        venta.estado = Venta.Estado.FACTURADA_DIAN
        venta.save(update_fields=["factura_asociada", "estado"])
        logger.info("[VentaCRUD] Venta id=%s vinculada a Factura id=%s", venta.id, factura.id)
        return venta

    @staticmethod
    @transaction.atomic
    def anular_venta(venta: Venta) -> Venta:
        """Marca la venta como ANULADA. La factura asociada no se elimina."""
        if venta.estado == Venta.Estado.FACTURADA_DIAN:
            raise ValueError("Una venta facturada no puede anularse directamente. Emita nota credito.")
        venta.estado = Venta.Estado.ANULADA
        venta.save(update_fields=["estado"])
        return venta

    @staticmethod
    @transaction.atomic
    def eliminar_venta_sincronizada(venta: Venta) -> None:
        """PLAN_SINCRONIZACION_FACTURAS_VENTAS_FASES: elimina (hard delete)
        una Venta comercial creada/vinculada por el flujo de sincronizacion.
        Solo borra la fila Venta (y sus ItemVenta, on_delete=CASCADE) --
        NUNCA toca la Factura (SSoT fiscal, permanece intacta y vuelve a
        aparecer como "pendiente" en el panel de sincronizacion)."""
        venta.delete()


class ResolucionFacturacionCRUDService:
    """Operaciones de persistencia para ResolucionFacturacion."""

    @staticmethod
    @transaction.atomic
    def crear_resolucion(empresa, data: dict) -> ResolucionFacturacion:
        """Crea una nueva ResolucionFacturacion para la empresa."""
        resolucion = ResolucionFacturacion(
            empresa=empresa,
            numero_resolucion=data["numero_resolucion"],
            prefijo=data.get("prefijo", ""),
            tipo=data.get("tipo", ResolucionFacturacion.TipoDocumento.ELECTRONICA),
            fecha_resolucion=data["fecha_resolucion"],
            fecha_desde=data["fecha_desde"],
            fecha_hasta=data["fecha_hasta"],
            rango_desde=data["rango_desde"],
            rango_hasta=data["rango_hasta"],
            consecutivo_actual=data.get("consecutivo_actual", data.get("rango_desde", 1)),
            vigente=data.get("vigente", True),
        )
        resolucion.full_clean()
        resolucion.save()
        logger.info(
            "[ResolucionCRUD] ResolucionFacturacion id=%s creada para empresa_id=%s",
            resolucion.id,
            empresa.id,
        )
        return resolucion

    @staticmethod
    @transaction.atomic
    def actualizar_resolucion(resolucion: ResolucionFacturacion, data: dict) -> ResolucionFacturacion:
        """Actualiza campos editables de ResolucionFacturacion."""
        campos = [
            "numero_resolucion", "prefijo", "tipo",
            "fecha_resolucion", "fecha_desde", "fecha_hasta",
            "rango_desde", "rango_hasta", "vigente",
        ]
        for campo in campos:
            if campo in data:
                setattr(resolucion, campo, data[campo])
        resolucion.full_clean()
        resolucion.save()
        logger.info("[ResolucionCRUD] ResolucionFacturacion id=%s actualizada", resolucion.id)
        return resolucion

    @staticmethod
    @transaction.atomic
    def eliminar_resolucion(resolucion: ResolucionFacturacion) -> None:
        """Elimina la resolucion si no tiene ventas asociadas."""
        if resolucion.ventas_asociadas.exists():
            raise ValueError(
                "No se puede eliminar una resolucion con ventas asociadas. Marquela como inactiva."
            )
        resolucion_id = resolucion.id
        resolucion.delete()
        logger.info("[ResolucionCRUD] ResolucionFacturacion id=%s eliminada", resolucion_id)
