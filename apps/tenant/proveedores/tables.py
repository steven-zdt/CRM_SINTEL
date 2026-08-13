"""
Tabla server-rendered (django-tables2) para el listado de Proveedores.

Expansion Fase 5-BIS (ver documentacion/plan_refactorizacion.md). Replica la
grilla "Directorio de Proveedores" de proveedores_main.js (getColumns).
Reutiliza ProveedorSelector.get_list/get_cuentas_pagar_resumen -- la misma
SSoT que consume la API DRF (ver views.py).

Fuera de alcance de esta migracion (queda con Tabulator por ahora, unidad
separada): el historial de compras dentro del offcanvas de detalle
(proveedores_form.js).
"""
import django_tables2 as tables
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.tenant.facturas.models import Factura
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


class CuentasPagarTable(tables.Table):
    # Fuente: Factura.naturaleza='COMPRA' (fuente de verdad, ver
    # CuentasPagarSelector.qs_list_facturas_compra en services/selectors.py
    # y CuentasPagarViewSet.list en la API DRF -- misma SSoT). El modelo
    # CuentasPagar (distinto) solo se usa para persistir abonos.
    numero_factura = tables.Column(accessor="numero", verbose_name="Factura", empty_values=())
    proveedor_nombre = tables.Column(accessor="emisor_razon_social", verbose_name="Proveedor", empty_values=())
    valor_total = tables.Column(accessor="total", verbose_name="Monto Total", empty_values=())
    saldo = tables.Column(accessor="total", verbose_name="Saldo Pendiente", empty_values=(), orderable=False)
    fecha_vencimiento = tables.Column(accessor="payment_due_date", verbose_name="Vencimiento", empty_values=())
    estado_pago = tables.Column(verbose_name="Estado", empty_values=())
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = Factura
        fields = ()
        sequence = ("numero_factura", "proveedor_nombre", "valor_total", "saldo", "fecha_vencimiento", "estado_pago", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-cuentas-pagar"}
        empty_text = "No se encontraron registros de cuentas por pagar"
        order_by = "payment_due_date"

    def render_numero_factura(self, value):
        return format_html('<span class="fw-bold text-primary">{}</span>', value or "S/N")

    def render_proveedor_nombre(self, value):
        return value or _SIN_DATO

    def render_valor_total(self, value):
        return _fmt_cop(value)

    def render_saldo(self, record):
        # Saldo = 0 si PAGADA, total en cualquier otro caso (misma logica
        # que FacturaCxPListSerializer.get_saldo en api/serializers.py).
        if record.estado_pago == "PAGADA":
            return _fmt_cop(0)
        return _fmt_cop(record.total)

    def render_fecha_vencimiento(self, value):
        return value.strftime("%Y-%m-%d") if value else _SIN_DATO

    def render_estado_pago(self, record):
        # django-tables2 sustituye automaticamente el valor de una columna
        # ligada a un CharField con choices por su get_FOO_display() humano
        # ("Pagada", "No Pagada"...) -- usamos record.estado_pago directo
        # para comparar contra el valor crudo del choice (mismo patron que
        # render_saldo/render_acciones en esta misma clase).
        if record.estado_pago == "PAGADA":
            return mark_safe('<span class="badge bg-success">Pagada</span>')
        if record.estado_pago == "PAGO_PARCIAL":
            return mark_safe('<span class="badge bg-warning text-dark">Pago Parcial</span>')
        return mark_safe('<span class="badge bg-danger">Sin Pago</span>')

    def render_acciones(self, record):
        es_pagada = record.estado_pago == "PAGADA"
        btn_disabled = "disabled" if es_pagada else ""
        btn_class = "opacity-50" if es_pagada else ""
        return format_html(
            '<div class="btn-group btn-group-sm">'
            '<button type="button" class="btn btn-outline-success btn-abono-cuentas-pagar {0}" data-uuid="{1}" {2} title="Registrar Abono">'
            '<i class="bi bi-cash-coin"></i> Abono</button>'
            "</div>",
            btn_class, record.uuid, btn_disabled,
        )
