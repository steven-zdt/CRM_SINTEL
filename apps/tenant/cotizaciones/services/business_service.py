import logging
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from ..models import Cotizacion
from .crud_service import CotizacionCRUDService

logger = logging.getLogger(__name__)


class CotizacionService:
    MONEY_Q = Decimal("0.01")
    HUNDRED = Decimal("100")

    @staticmethod
    def _to_decimal(value, field_name="value", default="0.00"):
        if value is None:
            return Decimal(default)
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError(f"Invalid decimal for {field_name}") from exc

    @staticmethod
    def _q(value):
        return value.quantize(CotizacionService.MONEY_Q, rounding=ROUND_HALF_UP)

    @classmethod
    def _get_payload_value(cls, datos, field_name, default_value):
        value = datos.get(field_name)
        if value is None:
            return default_value
        return value

    @classmethod
    def _build_header_fields(cls, configuracion, datos):
        dias_validez = int(getattr(configuracion, "dias_validez", 15) or 15)
        fecha_emision = cls._get_payload_value(datos, "fecha_emision", timezone.now().date())
        fecha_vencimiento = fecha_emision + timedelta(days=dias_validez)

        tipo_cotizacion_default = (
            getattr(configuracion, "tipo_cotizacion_default", None)
            or getattr(configuracion, "tipo_cotizacion", None)
            or "MIXTO"
        )
        iva_default = (
            getattr(configuracion, "iva_porcentaje_default", None)
            or getattr(configuracion, "iva_porcentaje", None)
            or Decimal("19.00")
        )
        aiu_admin_default = (
            getattr(configuracion, "aiu_admin_default", None)
            or getattr(configuracion, "porcentaje_aiu_admin", None)
            or Decimal("0.00")
        )
        aiu_imprevistos_default = (
            getattr(configuracion, "aiu_imprevistos_default", None)
            or getattr(configuracion, "porcentaje_aiu_imprevistos", None)
            or Decimal("0.00")
        )
        aiu_utilidad_default = (
            getattr(configuracion, "aiu_utilidad_default", None)
            or getattr(configuracion, "porcentaje_aiu_utilidad", None)
            or Decimal("0.00")
        )

        return {
            "tipo_cotizacion": cls._get_payload_value(datos, "tipo_cotizacion", tipo_cotizacion_default),
            "fecha_emision": fecha_emision,
            "fecha_vencimiento": fecha_vencimiento,
            "iva_porcentaje": cls._to_decimal(cls._get_payload_value(datos, "iva_porcentaje", iva_default), field_name="iva_porcentaje"),
            "porcentaje_aiu_admin": cls._to_decimal(cls._get_payload_value(datos, "porcentaje_aiu_admin", aiu_admin_default), field_name="porcentaje_aiu_admin"),
            "porcentaje_aiu_imprevistos": cls._to_decimal(cls._get_payload_value(datos, "porcentaje_aiu_imprevistos", aiu_imprevistos_default), field_name="porcentaje_aiu_imprevistos"),
            "porcentaje_aiu_utilidad": cls._to_decimal(cls._get_payload_value(datos, "porcentaje_aiu_utilidad", aiu_utilidad_default), field_name="porcentaje_aiu_utilidad"),
        }

    @classmethod
    def _sync_items(cls, cotizacion, items_data):
        if items_data is None:
            return

        CotizacionCRUDService.delete_items_for_cotizacion(cotizacion)

        for item_data in items_data:
            cantidad = cls._to_decimal(item_data.get("cantidad", 0), field_name="cantidad")
            costo = cls._to_decimal(item_data.get("costo_unitario", 0), field_name="costo_unitario")
            utilidad = cls._to_decimal(item_data.get("porcentaje_utilidad", 0), field_name="porcentaje_utilidad")
            calculos = cls.calcular_linea(cantidad, costo, utilidad)

            CotizacionCRUDService.create_item(
                cotizacion=cotizacion,
                empresa=cotizacion.empresa,
                tipo_item=item_data.get("tipo_item", "PRODUCTO"),
                producto=item_data.get("producto"),
                servicio=item_data.get("servicio"),
                descripcion=item_data.get("descripcion", "Sin descripción"),
                marca=item_data.get("marca", ""),
                referencia=item_data.get("referencia", ""),
                unidad=item_data.get("unidad", "UND"),
                cantidad=cantidad,
                costo_unitario=costo,
                porcentaje_utilidad=utilidad,
                precio_unitario_venta=calculos["precio_unitario"],
                subtotal_linea=calculos["subtotal"],
                orden=item_data.get("orden", 0),
            )

    @staticmethod
    def calcular_linea(cantidad, costo, utilidad):
        cantidad_dec = CotizacionService._to_decimal(cantidad, field_name="cantidad")
        costo_dec = CotizacionService._to_decimal(costo, field_name="costo")
        utilidad_dec = CotizacionService._to_decimal(utilidad, field_name="utilidad")

        factor_utilidad = Decimal("1") + (utilidad_dec / CotizacionService.HUNDRED)
        precio_unitario = costo_dec * factor_utilidad
        subtotal_linea = cantidad_dec * precio_unitario

        precio_unitario_q = CotizacionService._q(precio_unitario)
        subtotal_linea_q = CotizacionService._q(subtotal_linea)

        return {
            "precio_unitario": precio_unitario_q,
            "subtotal": subtotal_linea_q,
            "subtotal_linea": subtotal_linea_q,
        }

    @classmethod
    @transaction.atomic
    def crear_preforma(cls, empresa, datos):
        if not empresa:
            raise ValueError("empresa is required")

        configuracion_input = datos.get("configuracion")
        if not configuracion_input:
            raise ValueError("configuracion is required")

        configuracion = CotizacionCRUDService.get_configuracion_for_empresa(
            configuracion_input,
            empresa.id,
        )
        cliente = CotizacionCRUDService.get_cliente_for_empresa(datos.get("cliente"), empresa.id)
        items_data = datos.get("items", [])

        codigo_unico = cls.generar_codigo_unico(configuracion.id, empresa.id)
        configuracion.refresh_from_db(fields=["ultimo_numero"])

        numero_cotizacion = str(configuracion.ultimo_numero)
        header_fields = cls._build_header_fields(configuracion, datos)

        cotizacion = CotizacionCRUDService.create_cotizacion(
            empresa=empresa,
            cliente=cliente,
            configuracion=configuracion,
            numero_cotizacion=numero_cotizacion,
            codigo_unico=codigo_unico,
            estado=Cotizacion.Estado.BORRADOR,
            **header_fields,
        )

        cls._sync_items(cotizacion, items_data)
        cls.calcular_totales(cotizacion.id)

        return cotizacion

    @classmethod
    @transaction.atomic
    def actualizar_cotizacion(cls, instance, datos):
        cliente = instance.cliente
        if "cliente" in datos:
            cliente = CotizacionCRUDService.get_cliente_for_empresa(datos.get("cliente"), instance.empresa_id)

        configuracion = instance.configuracion
        if "configuracion" in datos and datos.get("configuracion"):
            configuracion = CotizacionCRUDService.get_configuracion_for_empresa(datos.get("configuracion"), instance.empresa_id)

        merged_data = {
            "tipo_cotizacion": instance.tipo_cotizacion,
            "fecha_emision": instance.fecha_emision,
            "iva_porcentaje": instance.iva_porcentaje,
            "porcentaje_aiu_admin": instance.porcentaje_aiu_admin,
            "porcentaje_aiu_imprevistos": instance.porcentaje_aiu_imprevistos,
            "porcentaje_aiu_utilidad": instance.porcentaje_aiu_utilidad,
        }
        merged_data.update(datos)

        header_fields = cls._build_header_fields(configuracion, merged_data)
        items_data = datos.get("items")

        updated = CotizacionCRUDService.update_cotizacion(
            instance,
            cliente=cliente,
            configuracion=configuracion,
            tipo_cotizacion=header_fields["tipo_cotizacion"],
            fecha_emision=header_fields["fecha_emision"],
            fecha_vencimiento=header_fields["fecha_vencimiento"],
            porcentaje_aiu_admin=header_fields["porcentaje_aiu_admin"],
            porcentaje_aiu_imprevistos=header_fields["porcentaje_aiu_imprevistos"],
            porcentaje_aiu_utilidad=header_fields["porcentaje_aiu_utilidad"],
            iva_porcentaje=header_fields["iva_porcentaje"],
        )

        cls._sync_items(updated, items_data)
        cls.calcular_totales(updated.id)
        return updated

    @classmethod
    def generar_codigo_unico(cls, perfil_id, empresa_id):
        if not transaction.get_connection().in_atomic_block:
            raise RuntimeError("generar_codigo_unico must be called inside transaction.atomic")

        configuracion = CotizacionCRUDService.get_configuracion_for_update(perfil_id, empresa_id)

        ultimo_numero = int(configuracion.ultimo_numero or 0)
        if ultimo_numero == 0:
            siguiente_numero = int(configuracion.semilla_inicial or 1)
        else:
            siguiente_numero = ultimo_numero + 1

        configuracion.ultimo_numero = siguiente_numero
        configuracion.save(update_fields=["ultimo_numero"])

        numero_formateado = f"{siguiente_numero:04d}"
        prefijo = configuracion.prefijo_secuencia or ""
        sufijo = configuracion.sufijo_secuencia or ""
        return f"{prefijo}{numero_formateado}{sufijo}"

    @staticmethod
    def calcular_totales(cotizacion_id):
        cotizacion = CotizacionCRUDService.get_cotizacion_for_totals(cotizacion_id)
        subtotal = CotizacionCRUDService.get_items_subtotal(cotizacion.id)

        aiu_admin_pct = Decimal(str(cotizacion.porcentaje_aiu_admin or Decimal("0.00")))
        aiu_imprevistos_pct = Decimal(str(cotizacion.porcentaje_aiu_imprevistos or Decimal("0.00")))
        aiu_utilidad_pct = Decimal(str(cotizacion.porcentaje_aiu_utilidad or Decimal("0.00")))
        iva_pct = Decimal(str(cotizacion.iva_porcentaje or Decimal("0.00")))

        aiu_admin = subtotal * (aiu_admin_pct / CotizacionService.HUNDRED)
        aiu_imprevistos = subtotal * (aiu_imprevistos_pct / CotizacionService.HUNDRED)
        aiu_utilidad = subtotal * (aiu_utilidad_pct / CotizacionService.HUNDRED)
        aiu_total = aiu_admin + aiu_imprevistos + aiu_utilidad

        base_iva = subtotal + aiu_total
        iva = base_iva * (iva_pct / CotizacionService.HUNDRED)
        total_con_impuestos = subtotal + aiu_total + iva

        subtotal_q = CotizacionService._q(subtotal)
        aiu_total_q = CotizacionService._q(aiu_total)
        iva_q = CotizacionService._q(iva)
        total_q = CotizacionService._q(total_con_impuestos)

        cotizacion.total_con_impuestos = total_q
        cotizacion.save(update_fields=["total_con_impuestos"])

        return {
            "subtotal": subtotal_q,
            "aiu_total": aiu_total_q,
            "iva": iva_q,
            "total_con_impuestos": total_q,
        }
