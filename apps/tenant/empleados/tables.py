"""
Tablas server-rendered (django-tables2) para los paneles Detail de los
split-pane Master-Detail de Empleados (historial de nominas/liquidaciones
del empleado seleccionado en el Master). El directorio de Empleados,
Contratos, Resoluciones DIAN, Periodos de Nomina, y los paneles Master de
Nominas/Liquidaciones migraron a DataTables (ver
docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md) -- EmpleadoTable/
ContratoTable/ResolucionDIANTable/PeriodoNominaTable/
NominaEmpleadoMasterTable/LiquidacionEmpleadoMasterTable retiradas, ver
apps/tenant/empleados/api/viewsets.py (EmpleadoViewSet.dt()/
con_nominas_dt()/con_liquidaciones_dt(), ContratoViewSet.dt(),
ResolucionDIANViewSet.dt(), PeriodoNominaViewSet.dt()).

Los paneles Detail se quedan aqui: no son listados planos independientes,
dependen de la seleccion hecha en el Master (?empleado_uuid=) -- ver views.py
para el detalle de como se resuelve ese filtrado.
"""

import django_tables2 as tables
from django.utils.html import format_html

from apps.tenant.empleados.models import Devengo, LiquidacionPrestacion

_BADGE_TIPO_LIQUIDACION = {
    "PRIMA_SERVICIOS": ("bg-info text-dark", "bi-award", "Prima"),
    "CESANTIAS": ("bg-warning text-dark", "bi-piggy-bank", "Cesantías"),
    "VACACIONES": ("bg-success", "bi-sun", "Vacaciones"),
    "LIQUIDACION_DEFINITIVA": ("bg-danger", "bi-file-earmark-break", "Liquidación"),
}


class DevengoDetailTable(tables.Table):
    """Detail: historico de nominas (Devengo) del empleado seleccionado en el master."""

    # accessor="periodo_mes" (no "fecha_inicio", que es opcional/nulo): django-tables2
    # omite render_periodo() cuando el valor resuelto por accessor esta en empty_values
    # (None esta ahi por defecto), y fecha_inicio suele ser None porque el flujo de
    # creacion de nomina solo exige periodo_mes. Con ese accessor la columna salia
    # siempre vacia aunque render_periodo tuviera el fallback correcto a periodo_mes.
    periodo = tables.Column(accessor="periodo_mes", verbose_name="Período", orderable=False)
    dias_laborados = tables.Column(verbose_name="Días")
    fecha_pago = tables.DateColumn(verbose_name="Fecha Pago", format="d M Y")
    salario_base = tables.Column(verbose_name="Salario Base")
    valor_horas_extras = tables.Column(verbose_name="H.E. y Recargos")
    neto_pagar = tables.Column(verbose_name="Neto a Pagar")
    anulado = tables.Column(verbose_name="Estado")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = Devengo
        fields = ()
        sequence = (
            "periodo",
            "dias_laborados",
            "fecha_pago",
            "salario_base",
            "valor_horas_extras",
            "neto_pagar",
            "anulado",
            "acciones",
        )
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-nomina-detail"}
        empty_text = "Sin nóminas para este empleado"
        order_by = ("-fecha_pago", "-periodo_mes")

    def render_periodo(self, record):
        if record.fecha_inicio and record.fecha_fin:
            return format_html(
                '<div class="small lh-sm fw-semibold">{}</div><div class="small text-muted lh-sm">al {}</div>',
                record.fecha_inicio,
                record.fecha_fin,
            )
        return record.periodo_mes or "—"

    def render_dias_laborados(self, value):
        return format_html(
            '<span class="badge bg-primary-subtle text-primary border border-primary-subtle">{}</span>',
            value or 0,
        )

    def render_salario_base(self, value):
        return f"${value:,.0f}"

    def render_valor_horas_extras(self, value):
        if value:
            return format_html('<span class="text-warning fw-semibold">${}</span>', f"{value:,.0f}")
        return format_html('<span class="text-muted">—</span>')

    def render_neto_pagar(self, record):
        if record.anulado:
            return format_html(
                '<span class="text-decoration-line-through text-muted small">${}</span> <span class="badge bg-danger ms-1">Anulada</span>',
                f"{record.neto_pagar:,.0f}",
            )
        return format_html('<strong class="text-success">${}</strong>', f"{record.neto_pagar:,.0f}")

    def render_anulado(self, value):
        if value:
            return format_html('<span class="badge bg-danger">Anulado</span>')
        return format_html('<span class="badge bg-success">Activo</span>')

    def render_acciones(self, record):
        # feature 2026-09-10: "Ver" (detalle solo lectura) + "PDF" (desprendible
        # para enviar al empleado) -- antes esta columna solo tenia "Anular".
        botones = format_html(
            '<button type="button" class="btn btn-sm btn-outline-info btn-ver-nomina" data-uuid="{0}" title="Ver detalle">'
            '<i class="bi bi-eye"></i></button>'
            '<a href="/api/v1/empleados/devengos/{0}/pdf/" target="_blank" class="btn btn-sm btn-outline-danger" title="Generar desprendible PDF">'
            '<i class="bi bi-file-earmark-pdf"></i></a>',
            record.uuid,
        )
        if record.anulado:
            return format_html('<div class="btn-group btn-group-sm">{}</div>', botones)
        return format_html(
            '<div class="btn-group btn-group-sm">{0}'
            '<button type="button" class="btn btn-outline-danger btn-anular-nomina" data-uuid="{1}" title="Anular nómina">'
            '<i class="bi bi-slash-circle"></i></button></div>',
            botones,
            record.uuid,
        )


# ============================================================================
# MASTER-DETAIL: Liquidaciones
# ============================================================================


class LiquidacionDetailTable(tables.Table):
    """Detail: historico de liquidaciones del empleado seleccionado en el master."""

    tipo_liquidacion = tables.Column(verbose_name="Tipo")
    fecha_corte = tables.Column(verbose_name="Corte")
    base_salarial = tables.Column(verbose_name="Base Salarial")
    valor_total = tables.Column(verbose_name="Total")
    estado = tables.Column(verbose_name="Estado")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = LiquidacionPrestacion
        fields = ()
        sequence = (
            "tipo_liquidacion",
            "fecha_corte",
            "base_salarial",
            "valor_total",
            "estado",
            "acciones",
        )
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-liquidacion-detail"}
        empty_text = "Sin liquidaciones para este empleado"
        order_by = "-fecha_corte"

    def render_tipo_liquidacion(self, value):
        cls, icon, label = _BADGE_TIPO_LIQUIDACION.get(
            value, ("bg-secondary", "bi-calculator", value or "—")
        )
        return format_html(
            '<span class="badge {}" style="font-size:.68rem;"><i class="bi {} me-1"></i>{}</span>',
            cls,
            icon,
            label,
        )

    def render_fecha_corte(self, value):
        if not value:
            return "—"
        return format_html(
            '<span class="font-monospace small">{}</span>', value.strftime("%d %b %y")
        )

    def render_base_salarial(self, value):
        return format_html(
            '<span class="font-monospace small text-muted">${}</span>', f"{value:,.0f}"
        )

    def render_valor_total(self, value):
        return format_html(
            '<span class="font-monospace fw-bold text-success">${}</span>', f"{value:,.0f}"
        )

    def render_estado(self, value):
        if value == "PAGADO":
            return format_html(
                '<span class="badge bg-success" style="font-size:.68rem;"><i class="bi bi-check2-all me-1"></i>Pagado</span>'
            )
        return format_html(
            '<span class="badge bg-warning text-dark" style="font-size:.68rem;"><i class="bi bi-hourglass-split me-1"></i>Proyectado</span>'
        )

    def render_acciones(self, record):
        return format_html(
            '<div class="btn-group btn-group-sm">'
            '<button class="btn btn-outline-primary py-0 px-2 btn-ver-liquidacion" data-uuid="{0}" title="Ver liquidación">'
            '<i class="bi bi-eye"></i></button>'
            '<a class="btn btn-outline-danger py-0 px-2" href="/api/v1/empleados/liquidaciones-prestaciones/{0}/pdf/" target="_blank" title="PDF">'
            '<i class="bi bi-file-earmark-pdf"></i></a>'
            '<button class="btn btn-outline-secondary py-0 px-2 btn-eliminar-liquidacion" data-uuid="{0}" title="Eliminar">'
            '<i class="bi bi-trash"></i></button>'
            "</div>",
            record.uuid,
        )
