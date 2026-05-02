"""
Selectores para Cotizaciones v3.6 - Zero Waste Queries.

Campos alineados con modelo Cotizacion (models.py):
- numero_cotizacion (NO "numero")
- total_con_impuestos (NO "total")
- cliente__razon_social, cliente__nombre_comercial (NO "cliente__nombre")
"""
from django.db.models import Q

from apps.tenant.cotizaciones.models import Cotizacion, CotizacionItem


LIST_FIELDS = (
    "id",
    "uuid",
    "numero_cotizacion",
    "estado",
    "fecha_emision",
    "fecha_vencimiento",
    "total_con_impuestos",
    "empresa_id",
    "created_at",
)

LIST_FK_FIELDS = (
    "cliente__razon_social",
    "cliente__nombre_comercial",
)

DETAIL_FIELDS = (
    "id",
    "uuid",
    "numero_cotizacion",
    "codigo_unico",
    "fecha_emision",
    "fecha_vencimiento",
    "estado",
    "tipo_cotizacion",
    "iva_porcentaje",
    "porcentaje_aiu_admin",
    "porcentaje_aiu_imprevistos",
    "porcentaje_aiu_utilidad",
    "total_con_impuestos",
    "empresa_id",
    "created_at",
    "updated_at",
)

DETAIL_FK_FIELDS = (
    "cliente__razon_social",
    "cliente__nombre_comercial",
    "cliente__numero_documento",
    "configuracion__id",
)

ITEM_LIST_FIELDS = (
    "id",
    "cotizacion_id",
    "tipo_item",
    "descripcion",
    "marca",
    "referencia",
    "unidad",
    "cantidad",
    "costo_unitario",
    "porcentaje_utilidad",
    "precio_unitario_venta",
    "subtotal_linea",
    "orden",
    "empresa_id",
)


class CotizacionSelector:
    """Selector para modelo Cotizacion."""

    @staticmethod
    def get_list(empresa_id, search=None, estado=None, cliente=None):
        """Retorna listado optimizado de cotizaciones."""
        qs = Cotizacion.objects.filter(
            empresa_id=empresa_id
        ).select_related('cliente').only(*LIST_FIELDS, *LIST_FK_FIELDS)

        if search:
            qs = qs.filter(
                Q(numero_cotizacion__icontains=search) |
                Q(cliente__razon_social__icontains=search)
            )

        if estado:
            qs = qs.filter(estado=estado)

        if cliente:
            qs = qs.filter(cliente_id=cliente)

        return qs.order_by('-created_at')

    @staticmethod
    def get_detail(cotizacion_id, empresa_id):
        """Retorna detalle de una cotizacion.

        Si cotizacion_id es None retorna queryset filtrado por empresa
        (util como base para ViewSet.get_object()).
        Si cotizacion_id esta presente retorna instancia unica o None.
        """
        qs = Cotizacion.objects.filter(
            empresa_id=empresa_id
        ).select_related(
            'cliente', 'configuracion'
        ).prefetch_related('items').only(
            *DETAIL_FIELDS, *DETAIL_FK_FIELDS
        )
        if cotizacion_id is None:
            return qs
        return qs.filter(id=cotizacion_id).first()

    @staticmethod
    def get_by_numero(numero, empresa_id):
        """Retorna cotizacion por numero."""
        return Cotizacion.objects.filter(
            numero_cotizacion=numero,
            empresa_id=empresa_id
        ).select_related('cliente').only(*DETAIL_FIELDS, *DETAIL_FK_FIELDS).first()


class CotizacionItemSelector:
    """Selector para modelo CotizacionItem."""

    @staticmethod
    def get_list(cotizacion_id, empresa_id):
        """Retorna items de una cotizacion."""
        return CotizacionItem.objects.filter(
            cotizacion_id=cotizacion_id,
            empresa_id=empresa_id
        ).select_related('producto', 'servicio').only(*ITEM_LIST_FIELDS)

    @staticmethod
    def get_detail(item_id, empresa_id):
        """Retorna detalle de un item."""
        return CotizacionItem.objects.filter(
            id=item_id,
            empresa_id=empresa_id
        ).select_related('producto', 'servicio').only(*ITEM_LIST_FIELDS).first()
