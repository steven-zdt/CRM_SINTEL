"""
Selectores de Ventas - Consultas read-only optimizadas.

Regla ZERO-COLLISION:
- Los *_LIST_FIELDS y *_DETAIL_FIELDS NUNCA contienen strings con '__'.
- Los campos de relaciones van en tuplas _*_TRAVERSALS separadas.
"""
from django.db.models import Q

from apps.tenant.ventas.models import ResolucionFacturacion, Venta, ItemVenta


# ==============================================================================
# CONSTANTES SSoT -- Campos directos de Venta (sin __ en nombres)
# ==============================================================================

VENTA_LIST_FIELDS = (
    "id",
    "uuid",
    "fecha_emision",
    "fecha_vencimiento",
    "estado",
    "subtotal",
    "impuestos",
    "total_neto",
    "observaciones",
    "numero_factura",
    "cliente_id",
    "proyecto_id",
    "resolucion_id",
    "factura_asociada_id",
    "empresa_id",
    "created_at",
    "updated_at",
)

VENTA_DETAIL_FIELDS = VENTA_LIST_FIELDS

ITEM_LIST_FIELDS = (
    "id",
    "descripcion",
    "cantidad",
    "precio_unitario",
    "porcentaje_iva",
    "subtotal",
    "venta_id",
    "producto_id",
    "servicio_id",
    "empresa_id",
)

# Traversals de Venta -- pueden contener __ (solo aqui)
_CLIENTE_TRAVERSALS = (
    "cliente__razon_social",
    "cliente__numero_documento",
    "cliente__tipo_documento",
)

_PROYECTO_TRAVERSALS = ("proyecto__nombre",)

_FACTURA_TRAVERSALS = (
    "factura_asociada__numero",
    "factura_asociada__uuid",
    "factura_asociada__estado",
    "factura_asociada__cufe",
)

_RESOLUCION_TRAVERSALS = (
    "resolucion__uuid",
    "resolucion__numero_resolucion",
    "resolucion__prefijo",
    "resolucion__tipo",
)

_PRODUCTO_TRAVERSALS = (
    "producto__nombre",
    "producto__codigo",
)

_SERVICIO_TRAVERSALS = (
    "servicio__nombre",
    "servicio__codigo",
)


# ==============================================================================
# CONSTANTES SSoT -- Campos directos de ResolucionFacturacion
# ==============================================================================

RESOLUCION_LIST_FIELDS = (
    "id",
    "uuid",
    "numero_resolucion",
    "prefijo",
    "tipo",
    "fecha_resolucion",
    "fecha_desde",
    "fecha_hasta",
    "rango_desde",
    "rango_hasta",
    "consecutivo_actual",
    "vigente",
    "empresa_id",
    "created_at",
    "updated_at",
)

RESOLUCION_DETAIL_FIELDS = RESOLUCION_LIST_FIELDS


# ==============================================================================
# SELECTORES
# ==============================================================================

class VentaSelector:
    """Selectores read-only para el modelo Venta."""

    @staticmethod
    def get_list(empresa_id: int, search: str = None, estado: str = None):
        """QuerySet optimizado para listado Tabulator."""
        qs = (
            Venta.objects.filter(empresa_id=empresa_id)
            .select_related("cliente", "proyecto", "factura_asociada", "resolucion")
            .only(
                *VENTA_LIST_FIELDS,
                *_CLIENTE_TRAVERSALS,
                *_PROYECTO_TRAVERSALS,
                *_FACTURA_TRAVERSALS,
                *_RESOLUCION_TRAVERSALS,
            )
        )

        if estado:
            qs = qs.filter(estado=estado)

        if search:
            qs = qs.filter(
                Q(cliente__razon_social__icontains=search)
                | Q(cliente__numero_documento__icontains=search)
                | Q(numero_factura__icontains=search)
                | Q(observaciones__icontains=search)
            )

        return qs.order_by("-created_at")

    @staticmethod
    def get_detail(empresa_id: int, venta_uuid=None):
        """QuerySet para detalle de Venta con prefetch de items."""
        qs = (
            Venta.objects.filter(empresa_id=empresa_id)
            .select_related("cliente", "proyecto", "factura_asociada", "resolucion")
            .prefetch_related("items", "items__producto", "items__servicio")
            .only(
                *VENTA_DETAIL_FIELDS,
                *_CLIENTE_TRAVERSALS,
                *_PROYECTO_TRAVERSALS,
                *_FACTURA_TRAVERSALS,
                *_RESOLUCION_TRAVERSALS,
            )
        )
        if venta_uuid:
            return qs.filter(uuid=venta_uuid)
        return qs


class ResolucionFacturacionSelector:
    """Selectores read-only para ResolucionFacturacion."""

    @staticmethod
    def get_list(empresa_id: int, vigente_only: bool = False):
        """QuerySet optimizado para listado."""
        qs = (
            ResolucionFacturacion.objects.filter(empresa_id=empresa_id)
            .only(*RESOLUCION_LIST_FIELDS)
        )
        if vigente_only:
            qs = qs.filter(vigente=True)
        return qs.order_by("-vigente", "-fecha_resolucion")

    @staticmethod
    def get_detail(empresa_id: int, resolucion_uuid=None):
        """QuerySet para detalle de ResolucionFacturacion."""
        qs = (
            ResolucionFacturacion.objects.filter(empresa_id=empresa_id)
            .only(*RESOLUCION_DETAIL_FIELDS)
        )
        if resolucion_uuid:
            return qs.filter(uuid=resolucion_uuid)
        return qs

    @staticmethod
    def get_vigentes(empresa_id: int):
        """Solo las resoluciones activas y dentro de fecha para el selector del formulario."""
        import datetime
        hoy = datetime.date.today()
        return (
            ResolucionFacturacion.objects.filter(
                empresa_id=empresa_id,
                vigente=True,
                fecha_desde__lte=hoy,
                fecha_hasta__gte=hoy,
            )
            .only(*RESOLUCION_LIST_FIELDS)
            .order_by("-fecha_resolucion")
        )
