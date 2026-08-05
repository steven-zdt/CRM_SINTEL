"""
Tabla server-rendered (django-tables2) para el listado de Clientes.

Expansion Fase 5-BIS (ver documentacion/plan_refactorizacion.md). Replica la
grilla "clientes" de clientes.list.js (getColumns / TABLE_COLUMNS.clientes).
Reutiliza los selectors ya existentes (ClienteSelector.get_cliente_list/
get_kpis/get_cartera_resumen), la misma SSoT que ya consume la API DRF -- ver
views.py.

Fuera de alcance de esta migracion (quedan con Tabulator por ahora, unidades
separadas): grilla "contactos" y "historial de facturas" (ambas en
clientes.list.js) y la grilla "cartera" (clientes.cartera.js).
"""
import django_tables2 as tables
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.tenant.clientes.models import Cliente

_SIN_DATO = mark_safe('<span class="text-muted">—</span>')

_TIPO_PERSONA_MAP = {
    "JURIDICA": ("bg-info", "Jurídica"),
    "NATURAL": ("bg-secondary", "Natural"),
}


def _fmt_cop(value):
    try:
        n = float(value or 0)
    except (TypeError, ValueError):
        return "$ 0"
    return "$ {:,.0f}".format(n).replace(",", ".")


class ClienteTable(tables.Table):
    # empty_values=(): django-tables2 solo llama a render_<campo>() cuando el
    # valor no esta en empty_values (por defecto (None, '')) -- forzamos ()
    # para que el render propio maneje siempre el caso vacio/legacy.
    razon_social = tables.Column(verbose_name="Cliente", empty_values=())
    tipo_persona = tables.Column(verbose_name="Tipo", empty_values=())
    regimen_tributario = tables.Column(verbose_name="Régimen / Ret.", empty_values=())
    cartera = tables.Column(empty_values=(), orderable=False, verbose_name="Cartera")
    contacto = tables.Column(empty_values=(), orderable=False, verbose_name="Contacto")
    activo = tables.Column(verbose_name="Estado")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = Cliente
        fields = ()
        sequence = ("razon_social", "tipo_persona", "regimen_tributario", "cartera", "contacto", "activo", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-clientes"}
        empty_text = "No hay clientes registrados"
        order_by = "razon_social"

    def __init__(self, *args, cartera_map=None, **kwargs):
        self.cartera_map = cartera_map or {}
        super().__init__(*args, **kwargs)

    def render_razon_social(self, record):
        nombre = record.razon_social or record.nombre_comercial or "—"
        doc_html = (
            format_html(
                '<div><small class="text-muted">{} {}</small></div>',
                record.get_tipo_documento_display() if record.tipo_documento else "",
                record.numero_documento,
            ) if record.numero_documento else ""
        )
        return format_html('<div class="lh-sm">{}{}</div>', nombre, doc_html)

    def render_tipo_persona(self, value):
        cls, label = _TIPO_PERSONA_MAP.get(value, ("bg-light text-dark", value or "—"))
        return format_html('<span class="badge {}">{}</span>', cls, label)

    def render_regimen_tributario(self, record):
        label = record.get_regimen_tributario_display() if record.regimen_tributario else "—"
        ret_html = (
            mark_safe('<span class="badge bg-warning ms-1" title="Retenedor"><i class="bi bi-shield-check"></i></span>')
            if record.es_retenedor else ""
        )
        return format_html('<span class="small">{}</span>{}', label, ret_html)

    def render_cartera(self, record):
        c = self.cartera_map.get(str(record.uuid))
        if not c or c.get("total_count", 0) == 0:
            return mark_safe('<span class="text-muted small">Sin facturas</span>')
        parts = []
        if c["pendiente_count"] > 0:
            parts.append(format_html(
                '<span class="badge bg-danger" title="Facturas pendientes de cobro">'
                '<i class="bi bi-exclamation-circle me-1"></i>{} x cobrar</span> '
                '<span class="small text-danger fw-semibold">{}</span>',
                c["pendiente_count"], _fmt_cop(c["pendiente_monto"]),
            ))
        if c["cobrada_count"] > 0 and c["pendiente_count"] == 0:
            parts.append(format_html(
                '<span class="badge bg-success" title="Todas las facturas cobradas">'
                '<i class="bi bi-check-circle me-1"></i>{} cobradas</span>',
                c["cobrada_count"],
            ))
        elif c["cobrada_count"] > 0:
            parts.append(format_html(
                '<span class="badge bg-light text-success border border-success" title="{} facturas cobradas">{} cobr.</span>',
                c["cobrada_count"], c["cobrada_count"],
            ))
        if not parts:
            return _SIN_DATO
        return mark_safe(" ".join(parts))

    def render_contacto(self, record):
        parts = []
        if record.email:
            parts.append(format_html('<div class="text-truncate small"><i class="bi bi-envelope me-1 text-muted"></i>{}</div>', record.email))
        if record.telefono:
            parts.append(format_html('<div class="small"><i class="bi bi-telephone me-1 text-muted"></i>{}</div>', record.telefono))
        if record.ciudad:
            parts.append(format_html('<div class="small text-muted"><i class="bi bi-geo-alt me-1"></i>{}</div>', record.ciudad))
        if not parts:
            return _SIN_DATO
        return format_html('<div class="lh-sm">{}</div>', mark_safe("".join(parts)))

    def render_activo(self, value):
        if value:
            return mark_safe('<span class="badge bg-success">Activo</span>')
        return mark_safe('<span class="badge bg-danger">Inactivo</span>')

    def render_acciones(self, record):
        return format_html(
            '<div class="btn-group btn-group-sm" role="group">'
            '<button class="btn btn-outline-primary" data-action="edit" data-uuid="{0}" title="Editar"><i class="bi bi-pencil"></i></button>'
            '<button class="btn btn-outline-info" data-action="view" data-uuid="{0}" title="Ver"><i class="bi bi-eye"></i></button>'
            '<button class="btn btn-outline-danger" data-action="delete" data-uuid="{0}" data-activo="{1}" data-nombre="{2}" title="Eliminar"><i class="bi bi-trash"></i></button>'
            "</div>",
            record.uuid, "true" if record.activo else "false", record.razon_social or "",
        )
