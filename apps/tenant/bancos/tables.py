"""
Tablas server-rendered (django-tables2) para los listados de Bancos.

Expansion Fase 5-BIS (ver PLAN_UNICO_CORRECCIONES.md) del patron ya aplicado
en gastos/facturas/compras/contabilidad/ventas. Cubre las 2 grillas reales
del modulo (cuentas, extractos). `TransaccionBancaria` no tiene grilla propia
-- sus filas ya se renderizan server-side dentro del offcanvas de detalle de
extracto (offcanvas_detalle_extracto.html), nunca uso Tabulator.
"""
import django_tables2 as tables
from django.utils.html import format_html

from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario

_BANCOS_MAP = {
    "BANCOLOMBIA": "Bancolombia",
    "BANCO_BOGOTA": "Banco de Bogotá",
    "DAVIVIENDA": "Davivienda",
    "BBVA": "BBVA",
    "OCCIDENTE": "Banco de Occidente",
    "POPULAR": "Banco Popular",
    "AV_VILLAS": "Banco AV Villas",
}

_TIPOS_CUENTA_MAP = {
    "AHORROS": "Ahorros",
    "CORRIENTE": "Corriente",
}

_MESES_MAP = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


class CuentaBancariaTable(tables.Table):
    nombre = tables.Column(verbose_name="Nombre de la Cuenta")
    banco = tables.Column(verbose_name="Banco")
    tipo = tables.Column(verbose_name="Tipo", orderable=False)
    numero = tables.Column(verbose_name="Número", orderable=False)
    estado = tables.Column(accessor="activo", verbose_name="Estado", orderable=False)
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = CuentaBancaria
        fields = ()
        sequence = ("nombre", "banco", "tipo", "numero", "estado", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-cuentas-bancarias"}
        empty_text = "No hay cuentas bancarias registradas"
        order_by = "nombre"

    def render_banco(self, value):
        return _BANCOS_MAP.get(value, value or "—")

    def render_tipo(self, value):
        return _TIPOS_CUENTA_MAP.get(value, value or "—")

    def render_estado(self, value):
        # B-4: badge de activo/inactivo -- antes no existia ningun indicio
        # visual de que una cuenta pudiera estar oculta/desactivada.
        if value:
            return format_html('<span class="badge bg-success">Activa</span>')
        return format_html('<span class="badge bg-secondary">Inactiva</span>')

    def render_acciones(self, record):
        toggle_btn = (
            format_html(
                '<button type="button" class="btn btn-outline-secondary btn-desactivar-cuenta" data-id="{0}" title="Desactivar">'
                '<i class="bi bi-eye-slash"></i></button>',
                record.uuid,
            )
            if record.activo
            else format_html(
                '<button type="button" class="btn btn-outline-success btn-activar-cuenta" data-id="{0}" title="Activar">'
                '<i class="bi bi-eye"></i></button>',
                record.uuid,
            )
        )
        # B-4: eliminar fisico solo tiene sentido si ya esta inactiva
        # (crud_service.eliminar_cuenta ahora lo rechaza si activo=True).
        delete_btn = format_html(
            '<button type="button" class="btn btn-outline-danger btn-delete-cuenta" data-id="{0}" title="Eliminar">'
            '<i class="bi bi-trash"></i></button>',
            record.uuid,
        ) if not record.activo else ""
        return format_html(
            '<div class="btn-group btn-group-sm" role="group">'
            '<button type="button" class="btn btn-outline-primary btn-edit-cuenta" data-id="{0}" title="Editar">'
            '<i class="bi bi-pencil"></i></button>'
            "{1}{2}"
            "</div>",
            record.uuid, toggle_btn, delete_btn,
        )


class ExtractoBancarioTable(tables.Table):
    cuenta = tables.Column(accessor="cuenta__nombre", verbose_name="Cuenta Bancaria", order_by=("cuenta__nombre",))
    periodo = tables.Column(accessor="mes", verbose_name="Periodo", orderable=False)
    archivo_s3 = tables.Column(verbose_name="Archivo", orderable=False)
    procesado = tables.Column(verbose_name="Estado")
    conciliacion = tables.Column(empty_values=(), orderable=False, verbose_name="Conciliación")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = ExtractoBancario
        fields = ()
        sequence = ("cuenta", "periodo", "archivo_s3", "procesado", "conciliacion", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-extractos-bancarios"}
        empty_text = "No hay extractos bancarios registrados"
        order_by = ("-anio", "-mes")

    def render_cuenta(self, record):
        nombre = record.cuenta.nombre if record.cuenta_id else "—"
        numero = format_html('<span class="text-muted small d-block">{}</span>', record.cuenta.numero) if record.cuenta_id else ""
        return format_html('<div class="py-1"><span class="fw-semibold">{}</span>{}</div>', nombre, numero)

    def render_periodo(self, record):
        mes = _MESES_MAP.get(record.mes, "—")
        return f"{mes} / {record.anio or '—'}"

    def render_archivo_s3(self, value):
        if not value:
            return "—"
        nombre = value.name.rsplit("/", 1)[-1]
        return format_html(
            '<a href="{0}" target="_blank" class="text-decoration-none small text-truncate d-inline-block" '
            'style="max-width:150px;" title="{1}"><i class="bi bi-file-earmark-excel text-success me-1"></i>{1}</a>',
            value.url, nombre,
        )

    def render_procesado(self, value):
        if value:
            return format_html('<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Procesado</span>')
        return format_html('<span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle me-1"></i>Pendiente</span>')

    def render_conciliacion(self, record):
        total = getattr(record, "total_transacciones", 0) or 0
        conc = getattr(record, "tx_conciliadas", 0) or 0
        pend = total - conc

        if not record.procesado or total == 0:
            return format_html('<span class="text-muted small">Sin transacciones</span>')

        pct = round((conc / total) * 100) if total > 0 else 0
        color = "bg-success" if pct == 100 else "bg-warning" if pct > 0 else "bg-danger"
        txt_color = "text-success" if pct >= 50 else "text-danger"
        pend_badge = (
            format_html('<span class="badge bg-danger" style="font-size:.6rem;">{} pendiente{}</span>', pend, "s" if pend > 1 else "")
            if pend > 0
            else format_html('<span class="badge bg-success" style="font-size:.6rem;"><i class="bi bi-check2-all"></i></span>')
        )
        return format_html(
            '<div style="font-size:.72rem;line-height:1.2;">'
            '<div class="d-flex justify-content-between mb-1">'
            '<span class="fw-semibold {}">{}/{}</span>{}'
            "</div>"
            '<div class="progress" style="height:4px;border-radius:2px;">'
            '<div class="progress-bar {}" style="width:{}%;transition:width .3s;"></div>'
            "</div></div>",
            txt_color, conc, total, pend_badge, color, pct,
        )

    def render_acciones(self, record):
        total = getattr(record, "total_transacciones", 0) or 0
        conc = getattr(record, "tx_conciliadas", 0) or 0
        pend = total - conc

        btns = format_html(
            '<button type="button" class="btn btn-outline-info btn-view-extracto" data-id="{0}" title="Ver Detalle / Conciliar">'
            '<i class="bi bi-eye"></i></button>',
            record.uuid,
        )
        if record.procesado and pend > 0:
            btns += format_html(
                '<button type="button" class="btn btn-outline-primary btn-conciliar-extracto" data-id="{0}" '
                'title="Conciliar Transacciones ({1} pendientes)"><i class="bi bi-link-45deg"></i></button>',
                record.uuid, pend,
            )
        if not record.procesado:
            btns += format_html(
                '<button type="button" class="btn btn-outline-warning btn-procesar-extracto" data-id="{0}" title="Procesar Transacciones">'
                '<i class="bi bi-cpu"></i></button>',
                record.uuid,
            )
        if record.procesado and total > 0:
            # BAN-12: descarga directa (GET simple), no requiere JS.
            btns += format_html(
                '<a class="btn btn-outline-success" href="/api/v1/bancos/extractos/{0}/exportar/" '
                'title="Exportar reporte de conciliacion (CSV)"><i class="bi bi-file-earmark-spreadsheet"></i></a>',
                record.uuid,
            )
        btns += format_html(
            '<button type="button" class="btn btn-outline-danger btn-delete-extracto" data-id="{0}" title="Eliminar">'
            '<i class="bi bi-trash"></i></button>',
            record.uuid,
        )
        return format_html('<div class="btn-group btn-group-sm">{}</div>', btns)
