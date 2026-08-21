"""
Tablas server-rendered (django-tables2) para los listados de Empleados.

Expansion Fase 5-BIS (ver PLAN_UNICO_CORRECCIONES.md) del patron ya aplicado
en gastos/facturas/compras/contabilidad/ventas/bancos. Cubre las 3 grillas
CRUD planas del modulo (empleados, contratos, resoluciones DIAN) mas las 2
grillas Master-Detail (nominas, liquidaciones): una tabla "master" de
empleados cuyas filas disparan (via row_attrs -> hx-get) la carga de la
tabla "detail" correspondiente (historial de nominas/liquidaciones de ESE
empleado) dentro de un panel HTMX aparte -- ver views.py para el detalle
de como se resuelve el filtrado por empleado_uuid.
"""
import django_tables2 as tables
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from apps.tenant.empleados.models import Contrato, Devengo, Empleado, LiquidacionPrestacion, PeriodoNomina, ResolucionDIAN

_BADGE_ESTADO_EMPLEADO = {
    "ACTIVO": ("bg-success", "bi-check-circle"),
    "RETIRADO": ("bg-danger", "bi-x-circle"),
}

_BADGE_TIPO_CONTRATO = {
    "INDEFINIDO": "bg-success",
    "FIJO": "bg-primary",
    "OBRA": "bg-warning text-dark",
    "PRESTACION": "bg-secondary",
}

_ICON_TIPO_CONTRATO = {
    "INDEFINIDO": "bi-infinite",
    "FIJO": "bi-hourglass",
    "OBRA": "bi-briefcase",
    "PRESTACION": "bi-person-check",
}

_BADGE_ESTADO_CONTRATO = {
    "ACTIVO": ("bg-success", "bi-check-circle"),
    "INACTIVO": ("bg-danger", "bi-pause-circle"),
    "HISTORICO": ("bg-secondary", ""),
    "CANCELADO": ("bg-dark", "bi-x-circle"),
}

_BADGE_TIPO_LIQUIDACION = {
    "PRIMA_SERVICIOS": ("bg-info text-dark", "bi-award", "Prima"),
    "CESANTIAS": ("bg-warning text-dark", "bi-piggy-bank", "Cesantías"),
    "VACACIONES": ("bg-success", "bi-sun", "Vacaciones"),
    "LIQUIDACION_DEFINITIVA": ("bg-danger", "bi-file-earmark-break", "Liquidación"),
}


class EmpleadoTable(tables.Table):
    foto_url = tables.Column(empty_values=(), orderable=False, verbose_name="")
    nombre_completo = tables.Column(accessor="primer_nombre", verbose_name="Empleado", order_by=("primer_nombre", "primer_apellido"))
    estado = tables.Column(verbose_name="Estado")
    fecha_ingreso = tables.DateColumn(verbose_name="Ingreso", format="d M Y")
    cargo = tables.Column(empty_values=(), orderable=False, verbose_name="Cargo")
    contacto = tables.Column(empty_values=(), orderable=False, verbose_name="Contacto")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = Empleado
        fields = ()
        sequence = ("foto_url", "nombre_completo", "estado", "fecha_ingreso", "cargo", "contacto", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-empleados"}
        empty_text = "No hay empleados registrados"
        order_by = "primer_nombre"

    def render_foto_url(self, record):
        if record.foto:
            return format_html(
                '<img src="{}" alt="" style="width:36px;height:36px;border-radius:50%;object-fit:cover;border:2px solid #dee2e6;">',
                record.foto.url,
            )
        iniciales = (f"{record.primer_nombre[:1]}{record.primer_apellido[:1]}").upper() or "?"
        color = "#adb5bd" if record.estado == "RETIRADO" else "#0d6efd"
        return format_html(
            '<div style="width:36px;height:36px;border-radius:50%;background:{0}20;'
            'border:2px solid {0}40;display:flex;align-items:center;justify-content:center;'
            'font-size:.75rem;font-weight:700;color:{0};">{1}</div>',
            color, iniciales,
        )

    def render_nombre_completo(self, record):
        nombre = f"{record.primer_nombre} {record.primer_apellido}".strip()
        doc = format_html('<div class="small text-muted">{}</div>', record.numero_documento) if record.numero_documento else ""
        return format_html('<div class="fw-semibold lh-sm">{}</div>{}', nombre, doc)

    def render_estado(self, value):
        cls, icon = _BADGE_ESTADO_EMPLEADO.get(value, ("bg-secondary", ""))
        icon_html = format_html('<i class="bi {} me-1"></i>', icon) if icon else ""
        return format_html('<span class="badge {}">{}{}</span>', cls, icon_html, value or "N/A")

    def render_cargo(self, record):
        if not record.cargo:
            return format_html('<span class="text-muted">—</span>')
        return format_html('<i class="bi bi-briefcase text-info me-1"></i><span>{}</span>', record.cargo)

    def render_contacto(self, record):
        filas = []
        if record.email:
            filas.append(('<i class="bi bi-envelope text-info me-1"></i><span class="small">{}</span>', (record.email,)))
        if record.telefono:
            filas.append(('<i class="bi bi-telephone text-success me-1"></i><span class="small">{}</span>', (record.telefono,)))
        if not filas:
            return format_html('<span class="text-muted">—</span>')
        return format_html_join(format_html("<br>"), "{}", ((format_html(tpl, *args),) for tpl, args in filas))

    def render_acciones(self, record):
        return format_html(
            '<div class="btn-group btn-group-sm">'
            '<button type="button" class="btn btn-outline-info btn-ver-empleado" data-uuid="{0}" title="Ver detalle">'
            '<i class="bi bi-eye"></i></button>'
            '<button type="button" class="btn btn-outline-primary btn-editar-empleado" data-uuid="{0}" title="Editar empleado">'
            '<i class="bi bi-pencil"></i></button>'
            '<button type="button" class="btn btn-outline-danger btn-eliminar-empleado" data-uuid="{0}" title="Eliminar permanentemente">'
            '<i class="bi bi-trash"></i></button>'
            "</div>",
            record.uuid,
        )


class ContratoTable(tables.Table):
    empleado = tables.Column(accessor="empleado__primer_nombre", verbose_name="Empleado", order_by=("empleado__primer_nombre",))
    tipo = tables.Column(verbose_name="Tipo Contrato")
    fecha_inicio = tables.DateColumn(verbose_name="Inicio", format="d M Y")
    fecha_fin = tables.Column(empty_values=(), orderable=False, verbose_name="Fin")
    salario_mensual = tables.Column(verbose_name="Salario")
    estado = tables.Column(verbose_name="Estado")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = Contrato
        fields = ()
        sequence = ("empleado", "tipo", "fecha_inicio", "fecha_fin", "salario_mensual", "estado", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-contratos"}
        empty_text = "No hay contratos registrados"
        order_by = "-fecha_inicio"

    def render_empleado(self, record):
        if not record.empleado_id:
            return format_html('<span class="text-muted">—</span>')
        return format_html(
            '<i class="bi bi-person text-primary me-2"></i><span class="fw-semibold">{}</span>',
            record.empleado.nombre_completo,
        )

    def render_tipo(self, record):
        cls = _BADGE_TIPO_CONTRATO.get(record.tipo, "bg-secondary")
        icon = _ICON_TIPO_CONTRATO.get(record.tipo, "")
        icon_html = format_html('<i class="bi {}"></i>', icon) if icon else ""
        return format_html('<span class="badge {} px-2">{} {}</span>', cls, icon_html, record.get_tipo_display())

    def render_fecha_fin(self, record):
        if record.tipo == "INDEFINIDO" or not record.fecha_fin:
            return format_html('<span class="badge bg-light text-dark"><i class="bi bi-infinite me-1"></i>Indefinido</span>')
        return format_html('<i class="bi bi-calendar-x text-danger me-1"></i><span class="small">{}</span>', record.fecha_fin)

    def render_salario_mensual(self, value):
        if not value:
            return format_html('<span class="text-muted">—</span>')
        return format_html('<span class="text-success fw-semibold"><i class="bi bi-cash-coin me-1"></i>${}</span>', f"{value:,.0f}")

    def render_estado(self, record):
        cls, icon = _BADGE_ESTADO_CONTRATO.get(record.estado, ("bg-secondary", ""))
        icon_html = format_html('<i class="bi {} me-1"></i>', icon) if icon else ""
        return format_html('<span class="badge {} px-2">{}{}</span>', cls, icon_html, record.get_estado_display())

    def render_acciones(self, record):
        botones = format_html(
            '<button type="button" class="btn btn-outline-secondary btn-ver-contrato" data-uuid="{0}" title="Ver Detalle">'
            '<i class="bi bi-eye"></i></button>',
            record.uuid,
        )
        if record.estado == "ACTIVO":
            botones += format_html(
                '<button type="button" class="btn btn-outline-primary btn-editar-contrato" data-uuid="{0}" title="Editar">'
                '<i class="bi bi-pencil"></i></button>'
                '<button type="button" class="btn btn-outline-danger btn-cancelar-contrato" data-uuid="{0}" title="Cancelar Contrato">'
                '<i class="bi bi-x-circle"></i></button>',
                record.uuid,
            )
        return format_html('<div class="btn-group btn-group-sm">{}</div>', botones)


class ResolucionDIANTable(tables.Table):
    numero_resolucion = tables.Column(verbose_name="Nro Resolución")
    prefijo = tables.Column(verbose_name="Prefijo")
    rango = tables.Column(empty_values=(), orderable=False, verbose_name="Rango")
    consecutivo = tables.Column(verbose_name="Consecutivo")
    vigencia = tables.Column(empty_values=(), orderable=False, verbose_name="Vigencia")
    vigente = tables.Column(verbose_name="Estado")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = ResolucionDIAN
        fields = ()
        sequence = ("numero_resolucion", "prefijo", "rango", "consecutivo", "vigencia", "vigente", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-resoluciones-empleados"}
        empty_text = "No hay resoluciones registradas"
        order_by = ("-vigente", "-fecha_resolucion")

    def render_numero_resolucion(self, value):
        if not value:
            return format_html('<span class="text-muted">—</span>')
        return format_html('<i class="bi bi-file-earmark-lock text-primary me-2"></i><span class="fw-semibold">{}</span>', value)

    def render_prefijo(self, value):
        if not value:
            return "—"
        return format_html('<span class="badge bg-secondary font-monospace">{}</span>', value)

    def render_rango(self, record):
        return format_html(
            '<span class="font-monospace small">{} – {}</span>',
            f"{record.rango_desde:,}", f"{record.rango_hasta:,}",
        )

    def render_consecutivo(self, record):
        pct = round((record.consecutivo / record.rango_hasta) * 100) if record.rango_hasta else 0
        cls = "text-danger fw-bold" if pct >= 90 else "text-warning fw-semibold" if pct >= 70 else "text-success fw-semibold"
        return format_html('<span class="{}">{}</span>', cls, f"{record.consecutivo:,}")

    def render_vigencia(self, record):
        return format_html(
            '<span class="small"><i class="bi bi-calendar-range text-muted me-1"></i>{} → {}</span>',
            record.fecha_inicio, record.fecha_fin,
        )

    def render_vigente(self, value):
        if value:
            return format_html('<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Vigente</span>')
        return format_html('<span class="badge bg-secondary">Inactiva</span>')

    def render_acciones(self, record):
        return format_html(
            '<button type="button" class="btn btn-outline-danger btn-sm py-0 px-2 btn-eliminar-resolucion" '
            'data-uuid="{0}" title="Eliminar"><i class="bi bi-trash"></i></button>',
            record.uuid,
        )


_BADGE_ESTADO_PERIODO = {
    "ABIERTO": ("bg-primary", "bi-unlock"),
    "PRELIQUIDADO": ("bg-info text-dark", "bi-calculator"),
    "EN_REVISION": ("bg-warning text-dark", "bi-eye"),
    "APROBADO": ("bg-info text-dark", "bi-hand-thumbs-up"),
    "PAGADO": ("bg-success", "bi-cash-coin"),
    "CERRADO": ("bg-secondary", "bi-lock"),
    "ANULADO": ("bg-danger", "bi-x-circle"),
    "BLOQUEADO": ("bg-dark", "bi-slash-circle"),
}


class PeriodoNominaTable(tables.Table):
    periodo_mes = tables.Column(verbose_name="Período")
    vigencia = tables.Column(empty_values=(), orderable=False, verbose_name="Vigencia")
    fecha_pago = tables.Column(verbose_name="Fecha de Pago")
    estado = tables.Column(verbose_name="Estado")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = PeriodoNomina
        fields = ()
        sequence = ("periodo_mes", "vigencia", "fecha_pago", "estado", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-periodos-nomina"}
        empty_text = "No hay períodos de nómina registrados"
        order_by = ("-periodo_mes",)

    def render_periodo_mes(self, value):
        return format_html('<span class="fw-semibold font-monospace">{}</span>', value)

    def render_vigencia(self, record):
        return format_html(
            '<span class="small"><i class="bi bi-calendar-range text-muted me-1"></i>{} → {}</span>',
            record.fecha_inicio, record.fecha_fin,
        )

    def render_estado(self, value, record):
        cls, icon = _BADGE_ESTADO_PERIODO.get(value, ("bg-secondary", "bi-question-circle"))
        return format_html(
            '<span class="badge {}"><i class="bi {} me-1"></i>{}</span>',
            cls, icon, record.get_estado_display(),
        )

    def render_acciones(self, record):
        return format_html(
            '<button type="button" class="btn btn-outline-primary btn-sm py-0 px-2 btn-gestionar-periodo" '
            'data-uuid="{0}" title="Ver / Gestionar"><i class="bi bi-arrow-right-circle me-1"></i>Gestionar</button>',
            record.uuid,
        )


# ============================================================================
# MASTER-DETAIL: Nominas
# ============================================================================

class NominaEmpleadoMasterTable(tables.Table):
    """Master: empleados que tienen al menos 1 nomina registrada (Count > 0)."""

    empleado = tables.Column(accessor="primer_nombre", verbose_name="Empleado", orderable=False)

    class Meta:
        model = Empleado
        fields = ()
        sequence = ("empleado",)
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-nomina-master"}
        empty_text = "Sin empleados con nóminas"
        row_attrs = {
            "hx-get": lambda record: reverse("empleados:nomina-detalle-tabla") + f"?empleado_uuid={record.uuid}",
            "hx-target": "#nomina-detail-panel",
            "hx-swap": "innerHTML",
            "style": "cursor:pointer;",
            "data-empleado-uuid": lambda record: record.uuid,
            "class": "fila-master-nomina",
        }

    def render_empleado(self, record):
        nombre = f"{record.primer_nombre} {record.primer_apellido}".strip()
        total = getattr(record, "total_nominas", 0) or 0
        return format_html(
            '<div class="d-flex align-items-start justify-content-between gap-1 py-1">'
            '<div class="lh-sm"><div class="fw-semibold small">{}</div>'
            '<div class="text-muted" style="font-size:.72rem;"><code>{}</code></div></div>'
            '<span class="badge bg-primary-subtle text-primary border border-primary-subtle flex-shrink-0 mt-1">{}</span>'
            "</div>",
            nombre, record.numero_documento, total,
        )


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
            "periodo", "dias_laborados", "fecha_pago", "salario_base",
            "valor_horas_extras", "neto_pagar", "anulado", "acciones",
        )
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-nomina-detail"}
        empty_text = "Sin nóminas para este empleado"
        order_by = ("-fecha_pago", "-periodo_mes")

    def render_periodo(self, record):
        if record.fecha_inicio and record.fecha_fin:
            return format_html(
                '<div class="small lh-sm fw-semibold">{}</div><div class="small text-muted lh-sm">al {}</div>',
                record.fecha_inicio, record.fecha_fin,
            )
        return record.periodo_mes or "—"

    def render_dias_laborados(self, value):
        return format_html('<span class="badge bg-primary-subtle text-primary border border-primary-subtle">{}</span>', value or 0)

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
        if record.anulado:
            return format_html('<span class="text-muted">—</span>')
        return format_html(
            '<button type="button" class="btn btn-sm btn-outline-danger btn-anular-nomina" data-uuid="{0}" title="Anular nómina">'
            '<i class="bi bi-slash-circle"></i></button>',
            record.uuid,
        )


# ============================================================================
# MASTER-DETAIL: Liquidaciones
# ============================================================================

class LiquidacionEmpleadoMasterTable(tables.Table):
    """Master: TODOS los empleados del tenant, ordenados por total de liquidaciones DESC."""

    empleado = tables.Column(accessor="primer_nombre", verbose_name="Empleado", orderable=False)

    class Meta:
        model = Empleado
        fields = ()
        sequence = ("empleado",)
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-liquidacion-master"}
        empty_text = "Sin empleados registrados"
        row_attrs = {
            "hx-get": lambda record: reverse("empleados:liquidacion-detalle-tabla") + f"?empleado_uuid={record.uuid}",
            "hx-target": "#liq-detail-panel-content",
            "hx-swap": "innerHTML",
            "style": "cursor:pointer;",
            "data-empleado-uuid": lambda record: record.uuid,
            "class": "fila-master-liquidacion",
        }

    def render_empleado(self, record):
        nombre = f"{record.primer_nombre} {record.primer_apellido}".strip()
        total = getattr(record, "total_liquidaciones", 0) or 0
        cls = "bg-primary" if total > 0 else "bg-secondary"
        return format_html(
            '<div class="fw-semibold text-truncate" style="font-size:.8rem;" title="{0}">'
            '<i class="bi bi-person-fill text-info me-1"></i>{0}</div>'
            '<div class="text-muted" style="font-size:.68rem;">{1}</div>'
            '<span class="badge {2}" style="font-size:.7rem;">{3}</span>',
            nombre, record.numero_documento or "", cls, total,
        )


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
        sequence = ("tipo_liquidacion", "fecha_corte", "base_salarial", "valor_total", "estado", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-liquidacion-detail"}
        empty_text = "Sin liquidaciones para este empleado"
        order_by = "-fecha_corte"

    def render_tipo_liquidacion(self, value):
        cls, icon, label = _BADGE_TIPO_LIQUIDACION.get(value, ("bg-secondary", "bi-calculator", value or "—"))
        return format_html('<span class="badge {}" style="font-size:.68rem;"><i class="bi {} me-1"></i>{}</span>', cls, icon, label)

    def render_fecha_corte(self, value):
        if not value:
            return "—"
        return format_html('<span class="font-monospace small">{}</span>', value.strftime("%d %b %y"))

    def render_base_salarial(self, value):
        return format_html('<span class="font-monospace small text-muted">${}</span>', f"{value:,.0f}")

    def render_valor_total(self, value):
        return format_html('<span class="font-monospace fw-bold text-success">${}</span>', f"{value:,.0f}")

    def render_estado(self, value):
        if value == "PAGADO":
            return format_html('<span class="badge bg-success" style="font-size:.68rem;"><i class="bi bi-check2-all me-1"></i>Pagado</span>')
        return format_html('<span class="badge bg-warning text-dark" style="font-size:.68rem;"><i class="bi bi-hourglass-split me-1"></i>Proyectado</span>')

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
