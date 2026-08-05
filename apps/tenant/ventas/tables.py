"""
Tabla server-rendered (django-tables2) para el listado de Ventas.

Expansion Fase 5-BIS (ver PLAN_UNICO_CORRECCIONES.md) del patron ya aplicado
en gastos/facturas/compras/contabilidad. Reutiliza VentaSelector.get_list()
(ya soporta `search`/`estado` como filtros server-side, no hubo que agregar
nada al Service Layer).
"""
import django_tables2 as tables
from django.utils.html import format_html

from apps.tenant.ventas.models import Venta

_BADGE_ESTADO = {
    "BORRADOR": "bg-secondary",
    "FACTURADA_DIAN": "bg-success",
    "ANULADA": "bg-danger",
}

_LABEL_ESTADO = {
    "BORRADOR": "Borrador",
    "FACTURADA_DIAN": "Facturada DIAN",
    "ANULADA": "Anulada",
}


class VentaTable(tables.Table):
    cliente = tables.Column(accessor="cliente__razon_social", verbose_name="Cliente", order_by=("cliente__razon_social",))
    fecha_emision = tables.DateColumn(verbose_name="Fecha", format="d M Y")
    estado = tables.Column(verbose_name="Estado")
    factura_numero = tables.Column(empty_values=(), orderable=False, verbose_name="Factura DIAN")
    total_neto = tables.Column(verbose_name="Total")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = Venta
        fields = ()
        sequence = ("cliente", "fecha_emision", "estado", "factura_numero", "total_neto", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-ventas"}
        empty_text = "No se encontraron ventas"
        order_by = "-created_at"

    def render_cliente(self, record):
        nombre = record.cliente.razon_social if record.cliente_id else "—"
        nit = record.cliente.numero_documento if record.cliente_id else None
        nit_html = format_html('<div class="text-muted" style="font-size:0.72rem;">NIT: {}</div>', nit) if nit else ""
        return format_html(
            '<div class="fw-semibold text-dark text-truncate small">{}</div>{}', nombre, nit_html
        )

    def render_estado(self, value):
        badge = _BADGE_ESTADO.get(value, "bg-dark")
        label = _LABEL_ESTADO.get(value, value)
        return format_html('<span class="badge {} badge-sm">{}</span>', badge, label)

    def render_factura_numero(self, record):
        numero = record.factura_asociada.numero if record.factura_asociada_id else record.numero_factura
        if not numero:
            return format_html('<span class="text-muted" style="font-size:0.78rem;">—</span>')
        return format_html(
            '<span class="badge bg-success-subtle text-success border border-success-subtle badge-sm">'
            '<i class="bi bi-receipt-cutoff me-1"></i>{}</span>',
            numero,
        )

    def render_total_neto(self, value):
        return format_html('<div class="fw-semibold text-end">${}</div>', f"{value:,.0f}")

    def render_acciones(self, record):
        return format_html(
            '<button type="button" class="btn btn-sm btn-outline-secondary btn-ver-venta" data-uuid="{0}" title="Ver detalle">'
            '<i class="bi bi-eye"></i></button>',
            record.uuid,
        )
