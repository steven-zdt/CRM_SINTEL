"""
Tabla server-rendered (django-tables2) para el listado de Ordenes de Compra.

Expansion Fase 5-BIS (ver PLAN_UNICO_CORRECCIONES.md) del piloto ya aplicado
en `gastos`. Reutiliza OrdenCompraSelector.get_list() (ya soporta `estado`
como filtro server-side, no hubo que agregar nada al Service Layer).
"""
import django_tables2 as tables
from django.utils.html import format_html

from apps.tenant.compras.models import OrdenCompra

_BADGE_ESTADO = {
    "BORRADOR": ("bg-secondary bg-opacity-10 text-secondary", "border-secondary border-opacity-20"),
    "PENDIENTE": ("bg-warning bg-opacity-10 text-warning-emphasis", "border-warning border-opacity-20"),
    "APROBADA": ("bg-success bg-opacity-10 text-success", "border-success border-opacity-20"),
    "RECIBIDA": ("bg-info bg-opacity-10 text-info-emphasis", "border-info border-opacity-20"),
    "ANULADA": ("bg-danger bg-opacity-10 text-danger", "border-danger border-opacity-20"),
}


class OrdenCompraTable(tables.Table):
    consecutivo = tables.Column(verbose_name="Consecutivo")
    fecha = tables.DateColumn(verbose_name="Fecha Emisión", format="d M Y")
    fecha_entrega = tables.DateColumn(verbose_name="Fecha Entrega", format="d M Y")
    proveedor = tables.Column(
        accessor="proveedor__razon_social", verbose_name="Proveedor", order_by=("proveedor__razon_social",)
    )
    proyecto = tables.Column(
        accessor="proyecto__nombre", verbose_name="Proyecto", orderable=False
    )
    total = tables.Column(verbose_name="Total")
    estado = tables.Column(verbose_name="Estado")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = OrdenCompra
        fields = ()
        sequence = (
            "consecutivo", "fecha", "fecha_entrega", "proveedor",
            "proyecto", "total", "estado", "acciones",
        )
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-ordenes-compra"}
        empty_text = "No se encontraron órdenes de compra registradas"
        order_by = "-fecha"

    def render_consecutivo(self, value):
        return format_html('<span class="fw-bold text-primary" style="font-size:0.85rem;">{}</span>', value or "—")

    def render_fecha_entrega(self, value):
        if not value:
            return format_html('<span class="text-muted fst-italic small">No definida</span>')
        return format_html('<i class="bi bi-calendar-check text-muted me-1"></i>{}', value.strftime("%d %b %Y"))

    def render_proveedor(self, record):
        nombre = record.proveedor.razon_social if record.proveedor_id else "—"
        nit = record.proveedor.numero_documento if record.proveedor_id else None
        nit_html = format_html('<div class="mt-1 small text-muted">NIT: <code class="text-secondary">{}</code></div>', nit) if nit else ""
        return format_html('<div class="fw-semibold text-dark small">{}</div>{}', nombre, nit_html)

    def render_proyecto(self, record):
        if not record.proyecto_id:
            return format_html('<span class="text-muted small">—</span>')
        return format_html(
            '<span class="badge bg-light text-dark border border-secondary"><i class="bi bi-folder text-secondary me-1"></i>{}</span>',
            record.proyecto.nombre,
        )

    def render_total(self, value):
        return format_html('<span class="fw-bold text-dark">${}</span>', f"{value:,.0f}")

    def render_estado(self, value):
        bg, border = _BADGE_ESTADO.get(value, ("bg-secondary text-white", "border-secondary"))
        return format_html('<span class="badge {} border {} px-2 py-1">{}</span>', bg, border, value)

    def render_acciones(self, record):
        can_edit = record.estado in ("BORRADOR", "PENDIENTE")
        can_delete = record.estado == "BORRADOR"
        edit_cls = "btn-outline-primary" if can_edit else "btn-light disabled"
        delete_cls = "btn-outline-danger" if can_delete else "btn-light disabled"
        return format_html(
            '<div class="btn-group btn-group-sm">'
            '<button type="button" class="btn btn-outline-info btn-view-compra" data-uuid="{0}" title="Ver Detalle">'
            '<i class="bi bi-eye"></i></button>'
            '<button type="button" class="btn {1} btn-edit-compra" data-uuid="{0}" title="Editar">'
            '<i class="bi bi-pencil"></i></button>'
            '<button type="button" class="btn {2} btn-delete-compra" data-uuid="{0}" title="Eliminar">'
            '<i class="bi bi-trash"></i></button>'
            "</div>",
            record.uuid, edit_cls, delete_cls,
        )
