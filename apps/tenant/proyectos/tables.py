"""
Tabla server-rendered (django-tables2) para el listado de Proyectos.

Expansion Fase 5-BIS (ver documentacion/plan_refactorizacion.md). Replica
exactamente las 10 columnas que antes vivian en getColumns() de
proyectos_list.js. Los KPIs agregados (antes calculados client-side desde
las filas de Tabulator) ahora se calculan server-side via
selectors.kpis_list() -- ver views.py.
"""
import django_tables2 as tables
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.tenant.proyectos.models import Proyecto

_SIN_DATO = mark_safe('<span class="text-muted small">—</span>')

_FASE_MAP = {
    "BORRADOR": ("bg-secondary", "Borrador"),
    "INICIO": ("bg-info text-dark", "Inicio"),
    "PLANEACION": ("bg-primary", "Planeación"),
    "EJECUCION": ("bg-warning text-dark", "Ejecución"),
    "CIERRE": ("bg-success", "Cierre"),
}

_ESTADO_MAP = {
    "PENDIENTE": ("bg-secondary", "Pendiente"),
    "EN_PROCESO": ("bg-primary", "En Proceso"),
    "DETENIDO": ("bg-danger", "Detenido"),
    "COMPLETADO": ("bg-success", "Completado"),
}


def _fmt_moneda(value):
    try:
        n = float(value or 0)
    except (TypeError, ValueError):
        return "—"
    return "$ {:,.0f}".format(n).replace(",", ".")


def _fmt_fecha(value):
    if not value:
        return "—"
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    return f"{value.day:02d} {meses[value.month - 1]} {value.year}"


class ProyectoTable(tables.Table):
    # empty_values=(): django-tables2 solo llama a render_<campo>() cuando el
    # valor no esta en empty_values (por defecto (None, '')) -- con blank=True
    # el valor vacio nunca invocaria el render y mostraria el placeholder
    # generico de la libreria en vez del badge/"—" propio.
    nombre = tables.Column(verbose_name="Proyecto", orderable=True, empty_values=())
    fase_actual = tables.Column(verbose_name="Fase", empty_values=())
    estado_tarea = tables.Column(verbose_name="Estado", empty_values=())
    porcentaje_avance = tables.Column(verbose_name="Avance")
    responsable_actual_nombre = tables.Column(verbose_name="Responsable", empty_values=())
    cliente_nombre = tables.Column(verbose_name="Cliente", empty_values=())
    documentos = tables.Column(empty_values=(), orderable=False, verbose_name="Documentos")
    periodo = tables.Column(empty_values=(), orderable=False, verbose_name="Período")
    contrato = tables.Column(empty_values=(), orderable=False, verbose_name="Contrato / Margen")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = Proyecto
        fields = ()
        sequence = (
            "nombre", "fase_actual", "estado_tarea", "porcentaje_avance",
            "responsable_actual_nombre", "cliente_nombre", "documentos",
            "periodo", "contrato", "acciones",
        )
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-proyectos"}
        empty_text = "No hay proyectos registrados"
        order_by = "-updated_at"

    def render_nombre(self, record):
        tipo = record.get_tipo_servicio_display() if record.tipo_servicio else ""
        tipo_html = (
            format_html(
                '<span class="badge bg-light text-secondary border fw-normal me-1" style="font-size:0.65rem;">{}</span>',
                tipo,
            ) if tipo else ""
        )
        codigo_html = (
            format_html('<code class="text-muted" style="font-size:0.7rem;">{}</code>', record.codigo)
            if record.codigo else ""
        )
        return format_html(
            '<div style="line-height:1.35;">'
            '<div class="fw-semibold text-truncate" style="max-width:200px;" title="{}">{}</div>'
            '<div class="mt-1">{}{}</div>'
            "</div>",
            record.nombre, record.nombre or "—", tipo_html, codigo_html,
        )

    def render_fase_actual(self, value):
        cls, label = _FASE_MAP.get(value, ("bg-secondary", value or "—"))
        return format_html('<span class="badge {} px-2 py-1">{}</span>', cls, label)

    def render_estado_tarea(self, value):
        cls, label = _ESTADO_MAP.get(value, ("bg-light text-dark", value or "—"))
        return format_html('<span class="badge {} px-2 py-1">{}</span>', cls, label)

    def render_porcentaje_avance(self, value):
        pct = value or 0
        color = "#198754" if pct >= 80 else "#ffc107" if pct >= 40 else "#6c757d"
        return format_html(
            '<div style="line-height:1.2;">'
            '<div class="fw-semibold" style="font-size:0.8rem;color:{0};">{1}%</div>'
            '<div class="progress mt-1" style="height:5px;border-radius:3px;">'
            '<div class="progress-bar" style="width:{1}%;background:{0};"></div>'
            "</div></div>",
            color, pct,
        )

    def render_responsable_actual_nombre(self, record):
        nombre = record.responsable_actual_nombre
        if not nombre:
            return _SIN_DATO
        iniciales = "".join(w[0] for w in nombre.split(" ")[:2]).upper()
        return format_html(
            '<div class="d-flex align-items-center gap-2">'
            '<div class="rounded-circle bg-primary bg-opacity-10 text-primary d-flex align-items-center '
            'justify-content-center flex-shrink-0 fw-bold" style="width:26px;height:26px;font-size:0.65rem;">{}</div>'
            '<span class="text-truncate small" style="max-width:110px;" title="{}">{}</span>'
            "</div>",
            iniciales, nombre, nombre,
        )

    def render_cliente_nombre(self, value):
        if not value:
            return _SIN_DATO
        return format_html('<span class="text-truncate d-block small" style="max-width:145px;" title="{}">{}</span>', value, value)

    def render_documentos(self, record):
        parts = []
        if record.factura_costo_numero:
            parts.append(format_html(
                '<span class="badge bg-light text-dark border fw-semibold" style="font-size:0.7rem;">'
                '<i class="bi bi-receipt me-1"></i>{}</span>',
                record.factura_costo_numero,
            ))
        cotizacion_numero = getattr(record.factura_costo, "cotizacion_numero", None) if record.factura_costo_id else None
        if cotizacion_numero:
            parts.append(format_html(
                '<span class="badge bg-info-subtle text-info-emphasis border border-info fw-semibold" style="font-size:0.7rem;">'
                '<i class="bi bi-file-earmark-text me-1"></i>{}</span>',
                cotizacion_numero,
            ))
        if not parts:
            return _SIN_DATO
        html = mark_safe("".join(parts))
        return format_html('<div class="d-flex flex-column gap-1 align-items-center">{}</div>', html)

    def render_periodo(self, record):
        return format_html(
            '<div style="line-height:1.35;font-size:0.78rem;">'
            '<div><i class="bi bi-calendar-event text-muted me-1"></i>{}</div>'
            '<div class="text-muted"><i class="bi bi-calendar-x me-1"></i>{}</div>'
            "</div>",
            _fmt_fecha(record.fecha_inicio), _fmt_fecha(record.fecha_fin_estimada),
        )

    def render_contrato(self, record):
        margen = float(record.margen_rentabilidad or 0)
        badge_cls = "bg-success" if margen > 0 else "bg-danger" if margen < 0 else "bg-secondary"
        # format_html() escapa cada argumento posicional (via conditional_escape)
        # ANTES de aplicar .format() -- un float pasado directamente llega a
        # .format() ya convertido a string, por lo que un format-spec como
        # "{:.1f}" fallaria con ValueError. El float se formatea a string aqui,
        # en Python puro, antes de entrar a format_html().
        margen_fmt = f"{margen:.1f}"
        return format_html(
            '<div style="line-height:1.35; text-align:right;">'
            '<div class="fw-semibold" style="font-size:0.85rem;">{}</div>'
            '<div class="mt-1"><span class="badge {} px-1" style="font-size:0.7rem;">'
            '<i class="bi bi-graph-up me-1"></i>{}%</span></div>'
            "</div>",
            _fmt_moneda(record.valor_contrato_proyectado), badge_cls, margen_fmt,
        )

    def render_acciones(self, record):
        emp_uuid = getattr(record, "responsable_empleado_uuid", "") or ""
        emp_nombre = record.responsable_actual_nombre or ""
        btns = format_html(
            '<button type="button" class="btn btn-outline-secondary btn-tareas-cortas" '
            'data-uuid="{}" data-emp-uuid="{}" data-emp-nombre="{}" title="Tareas Cortas">'
            '<i class="bi bi-list-task"></i></button>',
            record.uuid, emp_uuid, emp_nombre,
        )
        btns += format_html(
            '<button type="button" class="btn btn-outline-primary btn-edit-proyecto" data-uuid="{}" title="Editar proyecto">'
            '<i class="bi bi-pencil"></i></button>',
            record.uuid,
        )
        btns += format_html(
            '<button type="button" class="btn btn-outline-danger btn-delete-proyecto" data-uuid="{}" title="Eliminar proyecto">'
            '<i class="bi bi-trash"></i></button>',
            record.uuid,
        )
        return format_html('<div class="btn-group btn-group-sm">{}</div>', btns)
