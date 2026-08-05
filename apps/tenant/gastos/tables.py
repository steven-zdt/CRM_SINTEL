"""
Tablas server-rendered (django-tables2) para gastos.

Piloto de reemplazo de Tabulator (PLAN_UNICO_CORRECCIONES.md, Fase 5-BIS):
el HTML de cada fila se genera en el servidor a partir del QuerySet real
(via services/selectors.py), sin un contrato JSON intermedio que pueda
desincronizarse del backend como ocurria con Tabulator.
"""
import django_tables2 as tables
from django.utils.html import format_html

from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN


class DocumentoSoporteTable(tables.Table):
    """Tabla de Documentos Soporte (pestaña "Gastos")."""

    documento = tables.Column(
        accessor="numero_documento_proveedor",
        verbose_name="Documento",
        order_by=("numero_documento_proveedor",),
    )
    fecha = tables.DateColumn(verbose_name="Fecha", format="d M Y")
    proveedor = tables.Column(
        accessor="proveedor__razon_social",
        verbose_name="Vendedor / Proveedor",
        order_by=("proveedor__razon_social",),
    )
    categoria_contable = tables.Column(verbose_name="Clasificación")
    total = tables.Column(verbose_name="Total")
    estado = tables.Column(accessor="anulado", verbose_name="Estado", orderable=False)
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = DocumentoSoporte
        fields = ()
        sequence = ("documento", "fecha", "proveedor", "categoria_contable", "total", "estado", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-gastos"}
        empty_text = "No se encontraron gastos registrados"
        order_by = "-fecha"

    def render_documento(self, record):
        numero = record.numero_documento_proveedor or record.numero_documento
        return format_html(
            '<span class="fw-semibold text-primary" style="font-size:0.85rem;">{}</span>',
            numero,
        )

    def render_categoria_contable(self, record):
        return record.get_categoria_contable_display() or "—"

    def render_total(self, value):
        return format_html('<span class="fw-bold">${}</span>', f"{value:,.0f}")

    def render_estado(self, value):
        if value:
            return format_html(
                '<span class="badge bg-danger bg-opacity-10 text-danger '
                'border border-danger border-opacity-20 px-2 py-1">Anulado</span>'
            )
        return format_html(
            '<span class="badge bg-success bg-opacity-10 text-success '
            'border border-success border-opacity-20 px-2 py-1">Activo</span>'
        )

    def render_acciones(self, record):
        anulado = record.anulado
        edit_cls = "btn-light disabled" if anulado else "btn-outline-primary"
        cancel_cls = "btn-light disabled" if anulado else "btn-outline-warning"
        return format_html(
            '<div class="btn-group btn-group-sm">'
            '<button type="button" class="btn btn-outline-info btn-view-gasto" data-uuid="{0}" title="Ver Detalle">'
            '<i class="bi bi-eye"></i></button>'
            '<button type="button" class="btn {1} btn-edit-gasto" data-uuid="{0}" title="Editar">'
            '<i class="bi bi-pencil"></i></button>'
            '<button type="button" class="btn {2} btn-cancel-gasto" data-uuid="{0}" title="Anular">'
            '<i class="bi bi-x-circle"></i></button>'
            '<button type="button" class="btn btn-outline-danger btn-delete-gasto" data-uuid="{0}" '
            'data-anulado="{3}" title="Eliminar"><i class="bi bi-trash"></i></button>'
            "</div>",
            record.uuid,
            edit_cls,
            cancel_cls,
            "true" if anulado else "false",
        )


class ResolucionDIANTable(tables.Table):
    """Tabla de Resoluciones DIAN (pestaña "Resoluciones DIAN")."""

    numero_resolucion = tables.Column(verbose_name="Resolución")
    rango_desde = tables.Column(verbose_name="Rango Autorizado", orderable=False)
    fecha_fin = tables.DateColumn(verbose_name="Vencimiento", format="d M Y")
    vigente = tables.Column(verbose_name="Estado")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = ResolucionDIAN
        fields = ()
        sequence = ("numero_resolucion", "rango_desde", "fecha_fin", "vigente", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-resoluciones"}
        empty_text = "No hay resoluciones registradas"
        order_by = ("-vigente", "-fecha_resolucion")

    def render_numero_resolucion(self, record):
        return format_html(
            '<div style="line-height:1.35;">'
            '<div class="fw-semibold text-dark" style="font-size:0.85rem;">{}</div>'
            '<div class="mt-1" style="font-size:0.72rem;"><span class="text-muted">Prefijo:</span> '
            '<code class="text-secondary">{}</code></div>'
            "</div>",
            record.numero_resolucion or "—",
            record.prefijo or "—",
        )

    def render_rango_desde(self, record):
        return format_html(
            '<div style="font-size:0.78rem;"><span class="text-muted">Desde:</span> {} '
            '&nbsp;<span class="text-muted">Hasta:</span> {}</div>',
            record.rango_desde,
            record.rango_hasta,
        )

    def render_vigente(self, value):
        if value:
            return format_html(
                '<span class="badge bg-success bg-opacity-10 text-success '
                'border border-success border-opacity-20 px-2 py-1">Vigente</span>'
            )
        return format_html(
            '<span class="badge bg-secondary bg-opacity-10 text-secondary '
            'border border-secondary border-opacity-20 px-2 py-1">Vencida/Inactiva</span>'
        )

    def render_acciones(self, record):
        desactivar_btn = ""
        if record.vigente:
            desactivar_btn = format_html(
                '<button type="button" class="btn btn-outline-warning btn-deactivate-resolucion" '
                'data-uuid="{}" title="Desactivar"><i class="bi bi-slash-circle"></i></button>',
                record.uuid,
            )
        return format_html(
            '<div class="btn-group btn-group-sm">'
            '<button type="button" class="btn btn-outline-primary btn-edit-resolucion" data-uuid="{}" '
            'title="Editar Resolución"><i class="bi bi-pencil"></i></button>{}'
            "</div>",
            record.uuid,
            desactivar_btn,
        )
