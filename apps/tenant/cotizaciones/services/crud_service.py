import logging
from decimal import Decimal
from django.db.models import Sum
from ..models import Cotizacion, CotizacionItem

logger = logging.getLogger(__name__)

class CotizacionCRUDService:
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
    def delete_cotizacion(instance):
        instance.delete()

    @staticmethod
    def get_cotizacion_for_totals(cotizacion_id, empresa_id):
        # COTIZACIONES-01 (hallazgo H8): antes sin empresa_id -- no explotable
        # hoy porque el unico caller (CotizacionService.calcular_totales) ya
        # recibe un id resuelto desde un queryset scoped, pero sin defensa en
        # profundidad propia. Se blinda igual que el resto de selectors/CRUD.
        cotizacion = (
            Cotizacion.objects.filter(id=cotizacion_id, empresa_id=empresa_id)
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
    def get_items_subtotal(cotizacion_id, empresa_id):
        subtotal_db = (
            CotizacionItem.objects.filter(cotizacion_id=cotizacion_id, empresa_id=empresa_id)
            .only("subtotal_linea")
            .aggregate(total=Sum("subtotal_linea"))
            .get("total")
        )
        return Decimal("0.00") if subtotal_db is None else Decimal(str(subtotal_db))
