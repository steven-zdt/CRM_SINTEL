"""
Selectores de Ventas - Consultas GET optimizadas (read-only).

Regla ZERO-COLLISION:
- LIST_FIELDS y DETAIL_FIELDS NUNCA contienen strings con doble guion bajo (__).
- Los campos de relaciones van en tuplas _TRAVERSALS nombradas explicitamente.
"""
from django.db.models import Q

from apps.tenant.ventas.models import OrdenVenta, ItemOrdenVenta


# ==============================================================================
# CONSTANTES SSoT — Campos directos (sin __ en nombres)
# ==============================================================================

ORDEN_LIST_FIELDS = (
    "id",
    "uuid",
    "fecha_emision",
    "fecha_vencimiento",
    "estado",
    "subtotal",
    "impuestos",
    "total",
    "observaciones",
    "cliente_id",
    "factura_id",
    "empresa_id",
    "created_at",
    "updated_at",
)

ORDEN_DETAIL_FIELDS = (
    "id",
    "uuid",
    "fecha_emision",
    "fecha_vencimiento",
    "estado",
    "subtotal",
    "impuestos",
    "total",
    "observaciones",
    "cliente_id",
    "factura_id",
    "empresa_id",
    "created_at",
    "updated_at",
)

ITEM_LIST_FIELDS = (
    "id",
    "uuid",
    "descripcion",
    "cantidad",
    "precio_unitario",
    "tasa_iva",
    "subtotal",
    "orden_id",
    "producto_id",
    "servicio_id",
    "empresa_id",
)

# Traversals para relaciones — pueden contener __
_CLIENTE_TRAVERSALS = (
    "cliente__razon_social",
    "cliente__numero_documento",
    "cliente__tipo_documento",
)

_FACTURA_TRAVERSALS = (
    "factura__numero",
    "factura__uuid",
    "factura__estado",
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
# SELECTOR CLASSES
# ==============================================================================

class OrdenVentaSelector:
    """Selectores read-only para OrdenVenta."""

    @staticmethod
    def get_list(empresa_id: int, search: str = None):
        """QuerySet optimizado para LISTAR Ordenes de Venta."""
        qs = (
            OrdenVenta.objects.filter(empresa_id=empresa_id)
            .select_related("cliente", "factura")
            .only(*ORDEN_LIST_FIELDS, *_CLIENTE_TRAVERSALS, *_FACTURA_TRAVERSALS)
        )

        if search:
            qs = qs.filter(
                Q(cliente__razon_social__icontains=search)
                | Q(cliente__numero_documento__icontains=search)
                | Q(observaciones__icontains=search)
            )

        return qs.order_by("-created_at")

    @staticmethod
    def get_detail(empresa_id: int, orden_uuid=None):
        """QuerySet optimizado para DETALLE de OrdenVenta."""
        qs = (
            OrdenVenta.objects.filter(empresa_id=empresa_id)
            .select_related("cliente", "factura")
            .prefetch_related("items", "items__producto", "items__servicio")
            .only(*ORDEN_DETAIL_FIELDS, *_CLIENTE_TRAVERSALS, *_FACTURA_TRAVERSALS)
        )
        if orden_uuid:
            return qs.filter(uuid=orden_uuid)
        return qs

    @staticmethod
    def get_items(empresa_id: int, orden_id: int):
        """QuerySet optimizado para LISTAR Items de una OrdenVenta."""
        return (
            ItemOrdenVenta.objects.filter(empresa_id=empresa_id, orden_id=orden_id)
            .select_related("producto", "servicio")
            .only(*ITEM_LIST_FIELDS, *_PRODUCTO_TRAVERSALS, *_SERVICIO_TRAVERSALS)
            .order_by("id")
        )
