import logging
from decimal import Decimal

from django.db.models import Sum

from apps.tenant.clientes.models import Cliente
from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion

from ..models import Cotizacion, CotizacionItem

logger = logging.getLogger(__name__)


class CotizacionCRUDService:
    @staticmethod
    def get_configuracion_for_empresa(configuracion_input, empresa_id):
        if isinstance(configuracion_input, ConfiguracionCotizacion):
            if configuracion_input.empresa_id != empresa_id:
                raise ValueError("configuracion does not belong to tenant empresa")
            return configuracion_input

        configuracion_id = int(configuracion_input)
        configuracion = (
            ConfiguracionCotizacion.objects.filter(id=configuracion_id, empresa_id=empresa_id)
            .only(
                "id",
                "empresa_id",
                "prefijo_secuencia",
                "sufijo_secuencia",
                "semilla_inicial",
                "ultimo_numero",
                "dias_validez",
                "tipo_cotizacion_default",
                "tipo_cotizacion",
                "iva_porcentaje_default",
                "iva_porcentaje",
                "aiu_admin_default",
                "porcentaje_aiu_admin",
                "aiu_imprevistos_default",
                "porcentaje_aiu_imprevistos",
                "aiu_utilidad_default",
                "porcentaje_aiu_utilidad",
            )
            .first()
        )
        if not configuracion:
            raise ValueError("configuracion not found for tenant empresa")
        return configuracion

    @staticmethod
    def get_cliente_for_empresa(cliente_input, empresa_id):
        if not cliente_input:
            return None

        if isinstance(cliente_input, Cliente):
            if cliente_input.empresa_id != empresa_id:
                raise ValueError("cliente does not belong to tenant empresa")
            return cliente_input

        cliente_id = int(cliente_input)
        cliente = (
            Cliente.objects.filter(id=cliente_id, empresa_id=empresa_id)
            .only("id", "empresa_id")
            .first()
        )
        if not cliente:
            raise ValueError("cliente not found for tenant empresa")
        return cliente

    @staticmethod
    def get_configuracion_for_update(perfil_id, empresa_id):
        configuracion = (
            ConfiguracionCotizacion.objects.select_for_update()
            .only(
                "id",
                "empresa_id",
                "prefijo_secuencia",
                "sufijo_secuencia",
                "semilla_inicial",
                "ultimo_numero",
            )
            .filter(id=perfil_id, empresa_id=empresa_id)
            .first()
        )
        if not configuracion:
            raise ValueError("configuracion not found for tenant empresa")
        return configuracion

    @staticmethod
    def create_cotizacion(**kwargs):
        return Cotizacion.objects.create(**kwargs)

    @staticmethod
    def update_cotizacion(instance, **kwargs):
        for field, value in kwargs.items():
            setattr(instance, field, value)
        instance.save()
        return instance

    @staticmethod
    def delete_items_for_cotizacion(cotizacion):
        cotizacion.items.all().delete()

    @staticmethod
    def create_item(**kwargs):
        return CotizacionItem.objects.create(**kwargs)

    @staticmethod
    def get_cotizacion_for_totals(cotizacion_id):
        cotizacion = (
            Cotizacion.objects.filter(id=cotizacion_id)
            .only(
                "id",
                "iva_porcentaje",
                "porcentaje_aiu_admin",
                "porcentaje_aiu_imprevistos",
                "porcentaje_aiu_utilidad",
                "total_con_impuestos",
            )
            .first()
        )
        if not cotizacion:
            raise ValueError("cotizacion not found")
        return cotizacion

    @staticmethod
    def get_items_subtotal(cotizacion_id):
        subtotal_db = (
            CotizacionItem.objects.filter(cotizacion_id=cotizacion_id)
            .only("subtotal_linea")
            .aggregate(total=Sum("subtotal_linea"))
            .get("total")
        )
        return Decimal("0.00") if subtotal_db is None else Decimal(str(subtotal_db))
