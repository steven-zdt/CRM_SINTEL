"""
Tablas server-rendered (django-tables2) para Empresa: Empresa, Sede, Area y
MailInboxConfig.

Expansion Fase 5-BIS (ver documentacion/plan_refactorizacion.md). Replica las
grillas de empresa_list.js, sede_list.js, area_list.js y
mailinboxconfig_list.js (getColumns). Reutiliza EmpresaSelector/SedeSelector/
AreaSelector/MailInboxConfigSelector.get_list, la misma SSoT que consume la
API DRF -- ver views.py.
"""
import django_tables2 as tables
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.tenant.empresa.models import Area, Empresa, MailInboxConfig, Sede

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


class AreaTable(tables.Table):
    # Nota: la columna "Responsable" de area_list.js (Tabulator) leia el
    # campo responsable_nombre, que NO existe en el modelo Area ni lo
    # calcula ningun serializer -- siempre mostraba "Sin asignar" en
    # produccion. Se omite aqui deliberadamente (columna huerfana sin dato
    # real posible detras).
    nombre = tables.Column(verbose_name="Área / Departamento", empty_values=())
    codigo_funcionamiento = tables.Column(verbose_name="Código", empty_values=())
    sede = tables.Column(accessor="sede__nombre", verbose_name="Sede", order_by=("sede__nombre",), empty_values=())
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = Area
        fields = ()
        sequence = ("nombre", "codigo_funcionamiento", "sede", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-areas"}
        empty_text = "No hay áreas registradas"
        order_by = "nombre"

    def render_nombre(self, value):
        if not value:
            return _SIN_DATO
        return format_html('<i class="bi bi-diagram-3 text-success me-2"></i><span class="fw-semibold">{}</span>', value)

    def render_codigo_funcionamiento(self, value):
        if not value:
            return _SIN_DATO
        return format_html('<code class="bg-light px-2 py-1 rounded small">{}</code>', value)

    def render_sede(self, record):
        if not record.sede_id:
            return _SIN_DATO
        return format_html('<i class="bi bi-geo-alt text-primary me-1"></i><span class="small">{}</span>', record.sede.nombre)

    def render_acciones(self, record):
        return format_html(
            '<div class="btn-group btn-group-sm" role="group">'
            '<button type="button" class="btn btn-outline-primary btn-edit-area" data-uuid="{0}" title="Editar Área">'
            '<i class="bi bi-pencil"></i></button>'
            '<button type="button" class="btn btn-outline-danger btn-delete-area" data-uuid="{0}" title="Eliminar Área">'
            '<i class="bi bi-trash"></i></button>'
            "</div>",
            record.uuid,
        )


class EmpresaTable(tables.Table):
    # Empresa es singleton por tenant (una sola fila) -- solo accion "Editar",
    # sin "Eliminar" (igual que empresa_list.js, que nunca tuvo boton de
    # borrar). Lookup por pk (id), no uuid: el modelo Empresa no tiene campo
    # uuid (excepcion documentada, coherente con EmpresaViewSet que tampoco
    # lo usa).
    nit = tables.Column(verbose_name="NIT", empty_values=())
    razon_social = tables.Column(verbose_name="Razón Social", empty_values=())
    direccion = tables.Column(verbose_name="Dirección", empty_values=())
    telefono = tables.Column(verbose_name="Teléfono", empty_values=())
    email_contacto = tables.Column(verbose_name="Email", empty_values=())
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = Empresa
        fields = ()
        sequence = ("nit", "razon_social", "direccion", "telefono", "email_contacto", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-empresa"}
        empty_text = "No hay empresa registrada"

    def render_nit(self, record):
        if not record.nit:
            return _SIN_DATO
        nit_full = f"{record.nit}-{record.dv}" if record.dv else record.nit
        return format_html('<code class="text-muted">{}</code>', nit_full)

    def render_razon_social(self, value):
        if not value:
            return _SIN_DATO
        return format_html('<span class="fw-semibold text-dark">{}</span>', value)

    def render_direccion(self, value):
        if not value:
            return _SIN_DATO
        return format_html('<i class="bi bi-geo-alt text-primary me-1"></i><span class="small">{}</span>', value)

    def render_telefono(self, value):
        if not value:
            return _SIN_DATO
        return format_html('<i class="bi bi-telephone text-success me-1"></i><span>{}</span>', value)

    def render_email_contacto(self, value):
        if not value:
            return _SIN_DATO
        return format_html('<i class="bi bi-envelope text-info me-1"></i><span class="small">{}</span>', value)

    def render_acciones(self, record):
        return format_html(
            '<div class="btn-group btn-group-sm" role="group">'
            '<button type="button" class="btn btn-outline-primary btn-edit-empresa" data-id="{0}" title="Editar Empresa">'
            '<i class="bi bi-pencil"></i></button>'
            "</div>",
            record.id,
        )


class MailInboxConfigTable(tables.Table):
    # Modelo sin campo uuid (excepcion documentada, igual que Empresa) --
    # lookup por pk (id), coherente con MailInboxConfigViewSet y con el
    # boton data-id que ya usaba mailinboxconfig_list.js.
    nombre = tables.Column(verbose_name="Nombre", empty_values=())
    email_address = tables.Column(verbose_name="Email", empty_values=())
    imap_host = tables.Column(verbose_name="Servidor IMAP", empty_values=())
    is_active = tables.Column(verbose_name="Estado", empty_values=())
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = MailInboxConfig
        fields = ()
        sequence = ("nombre", "email_address", "imap_host", "is_active", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-mailinboxconfig"}
        empty_text = "No hay configuraciones de buzón registradas"
        order_by = "-updated_at"

    def render_nombre(self, record):
        if not record.nombre:
            return _SIN_DATO
        badge = (
            '<span class="badge bg-danger-subtle text-danger border border-danger-subtle ms-1 small">Gmail</span>'
            if record.provider == "gmail"
            else '<span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle ms-1 small">IMAP</span>'
        )
        return format_html('<span class="fw-semibold">{}</span>{}', record.nombre, mark_safe(badge))

    def render_email_address(self, value):
        if not value:
            return _SIN_DATO
        return value

    def render_imap_host(self, record):
        if not record.imap_host:
            return _SIN_DATO
        port = f":{record.imap_port}" if record.imap_port else ""
        ssl_badge = (
            '<span class="badge bg-success-subtle text-success border border-success-subtle ms-1 small">SSL</span>'
            if record.imap_ssl else ""
        )
        return format_html('<code class="small">{}{}</code>{}', record.imap_host, port, mark_safe(ssl_badge))

    def render_is_active(self, value):
        if value:
            return mark_safe('<span class="badge bg-success">Activa</span>')
        return mark_safe('<span class="badge bg-secondary">Inactiva</span>')

    def render_acciones(self, record):
        return format_html(
            '<div class="btn-group btn-group-sm" role="group">'
            '<button type="button" class="btn btn-outline-primary btn-edit-mailinbox" data-id="{0}" title="Editar">'
            '<i class="bi bi-pencil"></i></button>'
            '<button type="button" class="btn btn-outline-danger btn-delete-mailinbox" data-id="{0}" title="Eliminar">'
            '<i class="bi bi-trash"></i></button>'
            "</div>",
            record.id,
        )
