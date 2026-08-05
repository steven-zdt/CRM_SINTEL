"""
Tabla server-rendered (django-tables2) para el listado de Proveedores.

Expansion Fase 5-BIS (ver documentacion/plan_refactorizacion.md). Replica la
grilla "Directorio de Proveedores" de proveedores_main.js (getColumns).
Reutiliza ProveedorSelector.get_list/get_cuentas_pagar_resumen -- la misma
SSoT que consume la API DRF (ver views.py).

Fuera de alcance de esta migracion (quedan con Tabulator por ahora, unidades
separadas): grilla "Cuentas por Pagar" (cuentas_pagar_list.js) y el historial
de compras dentro del offcanvas de detalle (proveedores_form.js).
"""
import django_tables2 as tables
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.tenant.proveedores.models import Proveedor

_SIN_DATO = mark_safe('<span class="text-muted small">—</span>')


def _fmt_cop(value):
    try:
        n = float(value or 0)
    except (TypeError, ValueError):
        return "$ 0"
    return "$ {:,.0f}".format(n).replace(",", ".")


class ProveedorTable(tables.Table):
    # empty_values=(): django-tables2 solo llama a render_<campo>() cuando el
    # valor no esta en empty_values (por defecto (None, '')) -- forzamos ()
    # para que el render propio maneje siempre el caso vacio/legacy.
    razon_social = tables.Column(verbose_name="Razón Social", empty_values=())
    numero_documento = tables.Column(verbose_name="NIT/Documento", empty_values=())
    cuentas_pagar = tables.Column(empty_values=(), orderable=False, verbose_name="Cuentas por Pagar")
    activo = tables.Column(verbose_name="Estado")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = Proveedor
        fields = ()
        sequence = ("razon_social", "numero_documento", "cuentas_pagar", "activo", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-proveedores"}
        # data-uuid habilita "click en la fila abre el detalle" (excepto sobre
        # los botones de accion) -- replica el rowClick de Tabulator que tenia
        # proveedores_main.js. Ver delegacion en proveedores_main.js.
        row_attrs = {"data-uuid": lambda record: record.uuid, "style": "cursor:pointer;"}
        empty_text = "No hay proveedores registrados"
        order_by = "razon_social"

    def __init__(self, *args, cuentas_pagar_map=None, **kwargs):
        self.cuentas_pagar_map = cuentas_pagar_map or {}
        super().__init__(*args, **kwargs)

    def render_razon_social(self, value):
        return value or "—"

    def render_numero_documento(self, value):
        return value or _SIN_DATO

    def render_cuentas_pagar(self, record):
        c = self.cuentas_pagar_map.get(str(record.uuid))
        if not c or c.get("total_count", 0) == 0:
            return mark_safe('<span class="text-muted small">Sin facturas</span>')
        parts = []
        if c["pendiente_count"] > 0:
            parts.append(format_html(
                '<span class="badge bg-warning text-dark" title="Facturas pendientes de pago">'
                '<i class="bi bi-clock me-1"></i>{} pend.</span> '
                '<span class="small text-warning fw-semibold">{}</span>',
                c["pendiente_count"], _fmt_cop(c["pendiente_monto"]),
            ))
        if c["pagada_count"] > 0 and c["pendiente_count"] == 0:
            parts.append(format_html(
                '<span class="badge bg-success" title="Todas las facturas pagadas">'
                '<i class="bi bi-check-circle me-1"></i>{} pagadas</span>',
                c["pagada_count"],
            ))
        elif c["pagada_count"] > 0:
            parts.append(format_html(
                '<span class="badge bg-light text-success border border-success" title="{} facturas pagadas">{} pag.</span>',
                c["pagada_count"], c["pagada_count"],
            ))
        if not parts:
            return _SIN_DATO
        return mark_safe(" ".join(parts))

    def render_activo(self, value):
        if value:
            return mark_safe('<span class="badge bg-success">Activo</span>')
        return mark_safe('<span class="badge bg-secondary">Inactivo</span>')

    def render_acciones(self, record):
        is_active = record.activo is True
        delete_disabled = "disabled" if is_active else ""
        delete_class = "opacity-50" if is_active else ""
        return format_html(
            '<div class="btn-group btn-group-sm">'
            '<button type="button" class="btn btn-outline-primary btn-edit-proveedor" data-id="{0}" title="Editar">'
            '<i class="bi bi-pencil"></i></button>'
            '<button type="button" class="btn btn-outline-danger btn-delete-proveedor {1}" data-id="{0}" {2} title="Eliminar">'
            '<i class="bi bi-trash"></i></button>'
            "</div>",
            record.uuid, delete_class, delete_disabled,
        )
