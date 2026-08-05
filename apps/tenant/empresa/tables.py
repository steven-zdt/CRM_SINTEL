"""
Tabla server-rendered (django-tables2) para el listado de Sedes.

Expansion Fase 5-BIS (ver documentacion/plan_refactorizacion.md). Replica la
grilla de sede_list.js (getColumns). Reutiliza SedeSelector.get_list, la
misma SSoT que consume la API DRF -- ver views.py.

Fuera de alcance de esta migracion (quedan con Tabulator por ahora, unidades
separadas): Area (area_list.js), Empresa (empresa_list.js) y
MailInboxConfig (mailinboxconfig_list.js).
"""
import django_tables2 as tables
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.tenant.empresa.models import Sede

_SIN_DATO = mark_safe('<span class="text-muted">—</span>')
_SIN_ASIGNAR = mark_safe('<span class="text-muted">Sin asignar</span>')


class SedeTable(tables.Table):
    # empty_values=() en cada columna: django-tables2 solo llama a
    # render_<campo>() cuando el valor NO esta en empty_values (por defecto
    # (None, '')) -- con el default, un campo blank=True vacio ('') nunca
    # invoca el render y muestra el placeholder generico de la libreria en
    # vez del texto personalizado ("Sin asignar", etc.). Forzamos () para
    # que el render propio maneje siempre el caso vacio.
    nombre = tables.Column(verbose_name="Sede", empty_values=())
    direccion = tables.Column(verbose_name="Dirección", empty_values=())
    telefono = tables.Column(verbose_name="Teléfono", empty_values=())
    encargado_nombre = tables.Column(verbose_name="Encargado", empty_values=())
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = Sede
        fields = ()
        sequence = ("nombre", "direccion", "telefono", "encargado_nombre", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-sedes"}
        empty_text = "No hay sedes registradas"
        order_by = "nombre"

    def render_nombre(self, value):
        if not value:
            return _SIN_DATO
        return format_html('<i class="bi bi-geo-alt-fill text-primary me-2"></i><span class="fw-semibold">{}</span>', value)

    def render_direccion(self, value):
        if not value:
            return _SIN_DATO
        return format_html('<i class="bi bi-house text-secondary me-1"></i><span class="small">{}</span>', value)

    def render_telefono(self, value):
        if not value:
            return _SIN_DATO
        return format_html('<i class="bi bi-telephone text-success me-1"></i><span class="text-monospace">{}</span>', value)

    def render_encargado_nombre(self, value):
        if not value:
            return _SIN_ASIGNAR
        return format_html('<i class="bi bi-person text-info me-1"></i><span>{}</span>', value)

    def render_acciones(self, record):
        return format_html(
            '<div class="btn-group btn-group-sm" role="group">'
            '<button type="button" class="btn btn-outline-primary btn-edit-sede" data-uuid="{0}" title="Editar Sede">'
            '<i class="bi bi-pencil"></i></button>'
            '<button type="button" class="btn btn-outline-danger btn-delete-sede" data-uuid="{0}" title="Eliminar Sede">'
            '<i class="bi bi-trash"></i></button>'
            "</div>",
            record.uuid,
        )
