"""
Tabla server-rendered (django-tables2) para el listado de Facturas.

Piloto de reemplazo de Tabulator, expansion Fase 5-BIS (ver
PLAN_UNICO_CORRECCIONES.md). Una misma clase sirve para las 2 grillas del
modulo (Ventas / Compras) parametrizada por `naturaleza` — igual que el
`getColumnsNaturaleza(naturaleza)` que reemplaza en facturas_list.js.
"""
import django_tables2 as tables
from django.utils import timezone
from django.utils.html import format_html

from apps.tenant.facturas.models import Factura

_BADGE_DIAN = {
    "ACEPTADA": ("bg-success", "bi-check-circle-fill", "Aceptada"),
    "ENVIADA": ("bg-info", "bi-send-fill", "Enviada"),
    "BORRADOR": ("bg-secondary", "bi-pencil", "Borrador"),
    "RECHAZADA": ("bg-danger", "bi-x-circle-fill", "Rechazada"),
    "ANULADA": ("bg-dark", "bi-slash-circle", "Anulada"),
}


class FacturaTable(tables.Table):
    """Tabla de Facturas. Instanciar con `naturaleza="VENTA"|"COMPRA"`."""

    numero = tables.Column(verbose_name="Factura")
    contraparte = tables.Column(empty_values=(), orderable=False, verbose_name="Cliente / Proveedor")
    vencimiento = tables.Column(accessor="payment_due_date", verbose_name="Vencimiento")
    total = tables.Column(verbose_name="Total")
    estado = tables.Column(verbose_name="DIAN")
    estado_pago = tables.Column(verbose_name="Pago")
    cotizacion_numero = tables.Column(verbose_name="Cot.", orderable=False)
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = Factura
        fields = ()
        sequence = (
            "numero", "contraparte", "vencimiento", "total",
            "estado", "estado_pago", "cotizacion_numero", "acciones",
        )
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-facturas"}
        empty_text = "No hay facturas registradas"
        order_by = "-fecha_emision"

    def __init__(self, *args, naturaleza="VENTA", **kwargs):
        self.naturaleza = naturaleza
        super().__init__(*args, **kwargs)

    def render_numero(self, record):
        nc = getattr(record, "nota_credito", None)
        nc_badge = (
            format_html('<span class="badge bg-warning text-dark ms-1" style="font-size:0.65rem;">NC</span>')
            if nc else ""
        )
        fecha = ""
        if record.fecha_emision:
            fecha = format_html(
                '<div class="text-muted small"><i class="bi bi-calendar2 me-1"></i>{}</div>',
                record.fecha_emision.strftime("%d %b %y"),
            )
        return format_html('<div class="fw-semibold">{}{}</div>{}', record.numero or "---", nc_badge, fecha)

    def render_contraparte(self, record):
        is_venta = self.naturaleza == "VENTA"
        nombre = record.receptor_razon_social if is_venta else record.emisor_razon_social
        nit = record.receptor_nit if is_venta else record.emisor_nit
        # Simplificacion respecto a Tabulator: el pin de "vinculado" solo indica
        # que hay un cliente_uuid/proveedor_uuid en la factura, no que resuelva
        # a un registro existente (esa verificacion vivia en el serializer viejo
        # y se dejo fuera de este piloto para no reintroducir el N+1 de PERF-A1).
        vinculado = bool(record.cliente_uuid) if is_venta else bool(record.proveedor_uuid)
        pin = format_html('<i class="bi bi-link-45deg text-success me-1"></i>') if vinculado else ""
        return format_html(
            '<div class="text-truncate">{}{}</div><div class="text-muted small">NIT: {}</div>',
            pin, nombre or "---", nit or "—",
        )

    def render_vencimiento(self, record):
        val = record.payment_due_date or record.fecha_vencimiento
        if not val:
            return format_html('<span class="text-muted">—</span>')
        vencida = record.estado_pago != Factura.EstadoPago.PAGADA and val < timezone.localdate()
        cls = "text-danger fw-semibold" if vencida else ""
        icono = format_html('<i class="bi bi-exclamation-triangle-fill me-1"></i>') if vencida else ""
        return format_html('<span class="{}">{}{}</span>', cls, icono, val.strftime("%d %b %y"))

    def render_total(self, value):
        return format_html('<span class="fw-semibold">${}</span>', f"{value:,.0f}")

    def render_estado(self, value):
        cls, ico, txt = _BADGE_DIAN.get(value, ("bg-secondary", "bi-question-circle", value or "---"))
        return format_html('<span class="badge {} badge-sm"><i class="bi {} me-1"></i>{}</span>', cls, ico, txt)

    def render_estado_pago(self, value):
        if value == Factura.EstadoPago.PAGADA:
            return format_html('<span class="badge bg-success badge-sm"><i class="bi bi-check2-all me-1"></i>Pagada</span>')
        if value == Factura.EstadoPago.PAGO_PARCIAL:
            return format_html('<span class="badge bg-warning text-dark badge-sm"><i class="bi bi-clock-history me-1"></i>Parcial</span>')
        return format_html('<span class="badge bg-danger badge-sm"><i class="bi bi-exclamation-circle me-1"></i>Pendiente</span>')

    def render_cotizacion_numero(self, value):
        if not value:
            return format_html('<span class="text-muted">—</span>')
        return format_html(
            '<span class="badge text-bg-light border text-truncate" title="{0}" style="font-size:0.7rem;max-width:80px;">'
            '<i class="bi bi-receipt me-1"></i>{0}</span>',
            value,
        )

    def render_acciones(self, record):
        return format_html(
            '<div class="btn-group btn-group-sm">'
            '<button type="button" class="btn btn-outline-secondary btn-edit-factura" data-id="{0}" title="Editar">'
            '<i class="bi bi-pencil"></i></button>'
            '<button type="button" class="btn btn-outline-primary btn-view-factura" data-id="{0}" title="Ver">'
            '<i class="bi bi-eye"></i></button>'
            '<button type="button" class="btn btn-outline-danger btn-delete-factura" data-id="{0}" title="Eliminar">'
            '<i class="bi bi-trash"></i></button>'
            "</div>",
            record.uuid,
        )
