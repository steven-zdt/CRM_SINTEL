"""
Tabla server-rendered (django-tables2) para el panel "Nueva Tarea" (tareas
cortas, embebido en Proyectos). El listado principal de Proyectos migro a
DataTables (ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md) --
ProyectoTable retirada, ver apps/tenant/proyectos/api/viewsets.py::ProyectoViewSet.dt().
"""

import django_tables2 as tables
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.tenant.proyectos.models import TareaCorta

_SIN_DATO = mark_safe('<span class="text-muted small">—</span>')

_ESTADO_TAREA_MAP = {
    "PENDIENTE": ("bg-secondary", "Pendiente"),
    "EN_PROCESO": ("bg-primary", "En Proceso"),
    "COMPLETADA": ("bg-success", "Completada"),
    "CANCELADA": ("bg-danger", "Cancelada"),
}

_PRIORIDAD_TAREA_MAP = {
    "ALTA": "text-danger fw-bold",
    "NORMAL": "text-primary",
    "BAJA": "text-muted",
}

# Estado -> (siguiente_estado, icono, clase_btn). Sin entrada = sin avance posible
# (COMPLETADA/CANCELADA son estados terminales, igual que en el Tabulator original).
_SIGUIENTE_ESTADO_TAREA = {
    "PENDIENTE": ("EN_PROCESO", "bi-play-fill", "btn-outline-primary"),
    "EN_PROCESO": ("COMPLETADA", "bi-check-lg", "btn-outline-success"),
}


class TareaCortaTable(tables.Table):
    """Tabla del panel "Nueva Tarea" (tareas cortas, embebido en Proyectos)."""

    titulo = tables.Column(verbose_name="Tarea", empty_values=())
    cliente = tables.Column(
        accessor="cliente__razon_social", verbose_name="Cliente", empty_values=()
    )
    empleado = tables.Column(
        accessor="empleado__primer_nombre", verbose_name="Empleado", empty_values=()
    )
    estado = tables.Column(verbose_name="Estado", empty_values=())
    prioridad = tables.Column(verbose_name="Prior.", empty_values=())
    periodo = tables.Column(
        accessor="fecha_inicio", verbose_name="Periodo", orderable=False, empty_values=()
    )
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = TareaCorta
        fields = ()
        sequence = ("titulo", "cliente", "empleado", "estado", "prioridad", "periodo", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-tareas-cortas"}
        empty_text = "Sin tareas cortas"
        order_by = "fecha_inicio"

    def render_titulo(self, record):
        desc = record.descripcion or ""
        desc_html = (
            format_html(
                '<div class="text-muted" style="font-size:0.7rem;" title="{}">{}</div>',
                desc,
                desc[:40] + "..." if len(desc) > 40 else desc,
            )
            if desc
            else ""
        )
        return format_html(
            '<div style="line-height:1.3;">'
            '<div class="fw-semibold text-truncate" style="max-width:130px;" title="{}">{}</div>{}'
            "</div>",
            record.titulo,
            record.titulo or "-",
            desc_html,
        )

    def render_cliente(self, record):
        if not record.cliente_id:
            return _SIN_DATO
        nombre = record.cliente.razon_social
        doc = record.cliente.numero_documento or ""
        doc_html = (
            format_html('<div class="text-muted" style="font-size:0.7rem;">{}</div>', doc)
            if doc
            else ""
        )
        return format_html(
            '<div style="line-height:1.3;">'
            '<div class="fw-semibold text-truncate" style="max-width:160px;" title="{}">{}</div>{}'
            "</div>",
            nombre,
            nombre,
            doc_html,
        )

    def render_empleado(self, record):
        if not record.empleado_id:
            return _SIN_DATO
        nombre = f"{record.empleado.primer_nombre} {record.empleado.primer_apellido}".strip()
        return format_html(
            '<span class="text-truncate d-block small" style="max-width:145px;" title="{}">{}</span>',
            nombre,
            nombre,
        )

    def render_estado(self, value):
        cls, label = _ESTADO_TAREA_MAP.get(value, ("bg-light text-dark", value or "-"))
        return format_html(
            '<span class="badge {} px-2" style="font-size:0.68rem;">{}</span>', cls, label
        )

    def render_prioridad(self, value):
        cls = _PRIORIDAD_TAREA_MAP.get(value, "text-muted")
        return format_html(
            '<span class="{}" style="font-size:0.78rem;">{}</span>', cls, value or "-"
        )

    def render_periodo(self, record):
        return format_html(
            '<div style="font-size:0.72rem;line-height:1.4;">'
            '<div><i class="bi bi-calendar2 text-muted me-1"></i>{}</div>'
            '<div class="text-muted"><i class="bi bi-arrow-right me-1"></i>{}</div>'
            "</div>",
            record.fecha_inicio,
            record.fecha_fin,
        )

    def render_acciones(self, record):
        next_step = _SIGUIENTE_ESTADO_TAREA.get(record.estado)
        if next_step:
            nuevo_estado, icon, cls = next_step
            advance_btn = format_html(
                '<button class="btn btn-sm {0} btn-nt-avanzar px-1" data-uuid="{1}" data-estado="{2}" title="Avanzar estado">'
                '<i class="{3}"></i></button>',
                cls,
                record.uuid,
                nuevo_estado,
                icon,
            )
        else:
            advance_btn = format_html(
                '<button class="btn btn-sm btn-outline-secondary px-1" disabled title="{}">'
                '<i class="bi bi-lock"></i></button>',
                record.estado or "",
            )
        return format_html(
            '<div class="d-flex gap-1 justify-content-center">{}'
            '<button class="btn btn-sm btn-outline-danger btn-nt-delete px-1" data-uuid="{}" title="Eliminar">'
            '<i class="bi bi-trash3"></i></button></div>',
            advance_btn,
            record.uuid,
        )
