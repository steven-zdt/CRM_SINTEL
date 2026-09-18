"""
Tabla server-rendered (django-tables2) para el listado de Ordenes de Compra.

Expansion Fase 5-BIS (ver PLAN_UNICO_CORRECCIONES.md) del piloto ya aplicado
en `gastos`. Reutiliza OrdenCompraSelector.get_list() (ya soporta `estado`
como filtro server-side, no hubo que agregar nada al Service Layer).
"""
import django_tables2 as tables
from django.utils.html import format_html

from apps.tenant.compras.models import OrdenCompra, PlantillaOrdenCompra

_BADGE_ESTADO = {
    "BORRADOR": ("bg-secondary bg-opacity-10 text-secondary", "border-secondary border-opacity-20"),
    "PENDIENTE": ("bg-warning bg-opacity-10 text-warning-emphasis", "border-warning border-opacity-20"),
    "APROBADA": ("bg-success bg-opacity-10 text-success", "border-success border-opacity-20"),
    "PARCIAL": ("bg-info bg-opacity-10 text-info-emphasis", "border-info border-opacity-20"),
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
    # [OSF Fase F5] antes invisible: la tabla puede mostrar ordenes de
    # multiples sedes a la vez (ver OrdenCompraTableView.get_queryset), sin
    # esta columna no habia forma de distinguir de que sede era cada fila.
    sede = tables.Column(
        accessor="sede__nombre", verbose_name="Sede", order_by=("sede__nombre",)
    )
    total = tables.Column(verbose_name="Total")
    estado = tables.Column(verbose_name="Estado")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = OrdenCompra
        fields = ()
        sequence = (
            "consecutivo", "fecha", "fecha_entrega", "proveedor",
            "proyecto", "sede", "total", "estado", "acciones",
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


class PlantillaOrdenCompraTable(tables.Table):
    """
    CO-1 (2026-09-12): pantalla de gestion de plantillas -- antes solo
    existia el formulario "Nueva Plantilla", sin ningun lugar para VER las
    ya creadas (una plantilla con vigente=False era invisible en todas
    partes, incluido el dropdown de "Nueva Orden" que filtra vigente_only=True).
    """
    nombre = tables.Column(verbose_name="Nombre")
    prefijo = tables.Column(verbose_name="Prefijo", empty_values=())
    rango = tables.Column(empty_values=(), orderable=False, verbose_name="Rango")
    consecutivo_actual = tables.Column(verbose_name="Siguiente Consecutivo")
    vigente = tables.Column(verbose_name="Estado")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = PlantillaOrdenCompra
        fields = ()
        sequence = ("nombre", "prefijo", "rango", "consecutivo_actual", "vigente", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-plantillas-compra"}
        empty_text = "No se encontraron plantillas de numeración registradas"
        order_by = "-vigente"

    def render_prefijo(self, value):
        return value or format_html('<span class="text-muted small">—</span>')

    def render_rango(self, record):
        return format_html("{} – {}", record.rango_desde, record.rango_hasta)

    def render_vigente(self, value):
        if value:
            return format_html('<span class="badge bg-success bg-opacity-10 text-success border border-success border-opacity-20 px-2 py-1">Vigente</span>')
        return format_html('<span class="badge bg-secondary bg-opacity-10 text-secondary border border-secondary border-opacity-20 px-2 py-1">Inactiva</span>')

    def render_acciones(self, record):
        toggle_label = "Desactivar" if record.vigente else "Activar"
        toggle_icon = "bi-toggle2-off" if record.vigente else "bi-toggle2-on"
        toggle_cls = "btn-outline-secondary" if record.vigente else "btn-outline-success"
        return format_html(
            '<div class="btn-group btn-group-sm">'
            '<button type="button" class="btn btn-outline-primary"'
            ' hx-get="/api/v1/compras/plantillas/render-offcanvas/editar/?uuid={0}"'
            ' hx-target="#offcanvas-container-plantillas" hx-swap="innerHTML" title="Editar">'
            '<i class="bi bi-pencil"></i></button>'
            '<button type="button" class="btn {1} btn-toggle-plantilla" data-uuid="{0}" data-vigente="{2}" title="{3}">'
            '<i class="bi {4}"></i></button>'
            "</div>",
            record.uuid, toggle_cls, "true" if record.vigente else "false", toggle_label, toggle_icon,
        )
