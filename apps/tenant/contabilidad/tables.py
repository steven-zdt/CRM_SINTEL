"""
Tablas server-rendered (django-tables2) para los listados de Contabilidad.

Expansion Fase 5-BIS (ver PLAN_UNICO_CORRECCIONES.md) del patron ya aplicado
en gastos/facturas/compras. Cubre los 5 listados CRUD estandar del modulo
(cuentas, periodos, asientos, retenciones, plantillas). Los 3 restantes
(pendientes, libro-diario, reportes) NO son listados CRUD planos -- son
vistas agregadas/cross-app (ver REPORTE_FASE_5_BIS_CONTABILIDAD.md) y
quedan fuera de este patron deliberadamente.
"""
import django_tables2 as tables
from django.utils.html import format_html

from apps.tenant.contabilidad.models import (
    AsientoContable,
    CuentaContable,
    PeriodoContable,
    PlantillaContable,
    Retencion,
)

_BADGE_TIPO_CUENTA = {
    "ACTIVO": "primary",
    "PASIVO": "danger",
    "PATRIMONIO": "success",
    "INGRESO": "info",
    "GASTO": "warning",
}

_BADGE_ESTADO_PERIODO = {
    "ABIERTO": "success",
    "CERRADO": "danger",
}

_BADGE_ESTADO_ASIENTO = {
    "BORRADOR": "secondary",
    "APROBADO": "success",
    "CERRADO": "info",
}

_BADGE_TIPO_RETENCION = {
    "RETEFUENTE": ("bg-danger", "Retefuente"),
    "RETEICA": ("bg-warning text-dark", "ReteICA"),
    "RETEIVA": ("bg-info text-dark", "ReteIVA"),
}

_BADGE_TIPO_PLANTILLA = {
    "VENTA": ("bg-success", "Venta"),
    "COMPRA": ("bg-primary", "Compra"),
    "GASTO": ("bg-warning", "Gasto"),
    "NOMINA": ("bg-info", "Nomina"),
}


class CuentaContableTable(tables.Table):
    codigo = tables.Column(verbose_name="Código")
    nombre = tables.Column(verbose_name="Nombre")
    tipo = tables.Column(verbose_name="Tipo")
    activa = tables.Column(verbose_name="Estado")
    created_at = tables.DateTimeColumn(verbose_name="Creado", format="d M Y H:i")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = CuentaContable
        fields = ()
        sequence = ("codigo", "nombre", "tipo", "activa", "created_at", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-cuentas"}
        empty_text = "No se encontraron cuentas contables"
        order_by = "codigo"

    def render_tipo(self, value):
        badge = _BADGE_TIPO_CUENTA.get(value, "secondary")
        return format_html('<span class="badge bg-{}">{}</span>', badge, value or "—")

    def render_activa(self, value):
        if value:
            return format_html('<span class="badge bg-success">Activa</span>')
        return format_html('<span class="badge bg-secondary">Inactiva</span>')

    def render_acciones(self, record):
        return format_html(
            '<div class="btn-group btn-group-sm">'
            '<button type="button" class="btn btn-outline-secondary btn-ver-cuenta" data-uuid="{0}" title="Ver detalle">'
            '<i class="bi bi-eye"></i></button>'
            '<button type="button" class="btn btn-outline-primary btn-editar-cuenta" data-uuid="{0}" title="Editar">'
            '<i class="bi bi-pencil"></i></button>'
            '<button type="button" class="btn btn-outline-danger btn-eliminar-cuenta" data-uuid="{0}" title="Eliminar">'
            '<i class="bi bi-trash"></i></button>'
            "</div>",
            record.uuid,
        )


class PeriodoContableTable(tables.Table):
    periodo = tables.Column(verbose_name="Periodo")
    fecha_inicio = tables.DateColumn(verbose_name="Fecha Inicio", format="d M Y")
    fecha_fin = tables.DateColumn(verbose_name="Fecha Fin", format="d M Y")
    estado = tables.Column(verbose_name="Estado")
    cerrado_por = tables.Column(verbose_name="Cerrado Por", orderable=False)
    fecha_cierre = tables.DateTimeColumn(verbose_name="Fecha Cierre", format="d M Y H:i")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = PeriodoContable
        fields = ()
        sequence = (
            "periodo", "fecha_inicio", "fecha_fin", "estado",
            "cerrado_por", "fecha_cierre", "acciones",
        )
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-periodos"}
        empty_text = "No se encontraron periodos contables"
        order_by = "-periodo"

    def render_estado(self, value):
        badge = _BADGE_ESTADO_PERIODO.get(value, "light text-dark")
        label = "Abierto" if value == "ABIERTO" else "Cerrado" if value == "CERRADO" else value
        return format_html('<span class="badge bg-{}">{}</span>', badge, label)

    def render_cerrado_por(self, record):
        if not record.cerrado_por_id:
            return format_html('<span class="text-muted">—</span>')
        return str(record.cerrado_por)

    def render_fecha_cierre(self, value):
        if not value:
            return format_html('<span class="text-muted">—</span>')
        return value.strftime("%d %b %Y %H:%M")

    def render_acciones(self, record):
        cerrar_btn = ""
        if record.estado == "ABIERTO":
            cerrar_btn = format_html(
                '<button type="button" class="btn btn-outline-warning btn-cerrar-periodo" data-uuid="{0}" title="Cerrar periodo">'
                '<i class="bi bi-lock"></i></button>',
                record.uuid,
            )
        return format_html(
            '<div class="btn-group btn-group-sm">'
            '<button type="button" class="btn btn-outline-secondary btn-ver-periodo" data-uuid="{0}" title="Ver detalle">'
            '<i class="bi bi-eye"></i></button>'
            '<button type="button" class="btn btn-outline-primary btn-editar-periodo" data-uuid="{0}" title="Editar">'
            '<i class="bi bi-pencil"></i></button>'
            "{1}"
            '<button type="button" class="btn btn-outline-danger btn-eliminar-periodo" data-uuid="{0}" title="Eliminar">'
            '<i class="bi bi-trash"></i></button>'
            "</div>",
            record.uuid, cerrar_btn,
        )


class AsientoContableTable(tables.Table):
    numero = tables.Column(verbose_name="Número")
    fecha = tables.DateColumn(verbose_name="Fecha", format="d M Y")
    descripcion = tables.Column(verbose_name="Descripción")
    estado = tables.Column(verbose_name="Estado")
    movimientos_count = tables.Column(verbose_name="Movimientos", orderable=False)
    total_debe = tables.Column(verbose_name="Débito")
    total_haber = tables.Column(verbose_name="Crédito")
    cuadratura = tables.Column(empty_values=(), orderable=False, verbose_name="Cuadratura")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = AsientoContable
        fields = ()
        sequence = (
            "numero", "fecha", "descripcion", "estado", "movimientos_count",
            "total_debe", "total_haber", "cuadratura", "acciones",
        )
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-asientos"}
        empty_text = "No se encontraron asientos contables"
        order_by = "-fecha"

    def render_descripcion(self, value):
        if not value:
            return format_html('<span class="text-muted">—</span>')
        texto = value if len(value) <= 50 else value[:50] + "..."
        return texto

    def render_estado(self, value):
        badge = _BADGE_ESTADO_ASIENTO.get(value, "light text-dark")
        return format_html('<span class="badge bg-{}">{}</span>', badge, value or "—")

    def render_movimientos_count(self, value):
        if not value:
            return format_html('<span class="text-muted">0</span>')
        return format_html('<span class="badge bg-primary">{}</span>', value)

    def render_total_debe(self, value):
        return format_html('<span>${}</span>', f"{value:,.2f}")

    def render_total_haber(self, value):
        return format_html('<span>${}</span>', f"{value:,.2f}")

    def render_cuadratura(self, record):
        diferencia = abs((record.total_debe or 0) - (record.total_haber or 0))
        if diferencia < 0.01:
            return format_html('<span class="badge bg-success"><i class="bi bi-check-circle"></i> Cuadrado</span>')
        return format_html(
            '<span class="badge bg-danger"><i class="bi bi-x-circle"></i> ${}</span>', f"{diferencia:,.2f}"
        )

    def render_acciones(self, record):
        cuadrado = abs((record.total_debe or 0) - (record.total_haber or 0)) < 0.01
        aprobar_btn = ""
        if record.estado == "BORRADOR" and cuadrado:
            aprobar_btn = format_html(
                '<button type="button" class="btn btn-outline-success btn-aprobar-asiento" data-uuid="{0}" title="Aprobar">'
                '<i class="bi bi-check-circle"></i></button>',
                record.uuid,
            )
        return format_html(
            '<div class="btn-group btn-group-sm">'
            '<button type="button" class="btn btn-outline-secondary btn-ver-asiento" data-uuid="{0}" title="Ver detalle">'
            '<i class="bi bi-eye"></i></button>'
            '<button type="button" class="btn btn-outline-primary btn-editar-asiento" data-uuid="{0}" title="Editar">'
            '<i class="bi bi-pencil"></i></button>'
            "{1}"
            '<button type="button" class="btn btn-outline-danger btn-eliminar-asiento" data-uuid="{0}" title="Eliminar">'
            '<i class="bi bi-trash"></i></button>'
            "</div>",
            record.uuid, aprobar_btn,
        )


class RetencionTable(tables.Table):
    """Solo lectura -- las retenciones se generan via Pull Model (RetencionesService)."""

    tipo = tables.Column(verbose_name="Tipo")
    naturaleza = tables.Column(verbose_name="Naturaleza")
    porcentaje = tables.Column(verbose_name="%")
    monto = tables.Column(verbose_name="Monto")
    documento_origen_app = tables.Column(verbose_name="Documento Origen", orderable=False)
    reversada = tables.Column(verbose_name="Estado")
    created_at = tables.DateColumn(verbose_name="Fecha", format="d M Y")

    class Meta:
        model = Retencion
        fields = ()
        sequence = (
            "tipo", "naturaleza", "porcentaje", "monto",
            "documento_origen_app", "reversada", "created_at",
        )
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-retenciones"}
        empty_text = "No se encontraron retenciones"
        order_by = "-created_at"

    def render_tipo(self, value):
        cls, label = _BADGE_TIPO_RETENCION.get(value, ("bg-secondary", value or "—"))
        return format_html('<span class="badge {}">{}</span>', cls, label)

    def render_naturaleza(self, value):
        if value == "VENTA":
            return format_html('<span class="badge bg-success">Venta</span>')
        return format_html('<span class="badge bg-primary">Compra</span>')

    def render_porcentaje(self, value):
        return f"{value:.2f}%"

    def render_monto(self, value):
        return format_html('<span>${}</span>', f"{value:,.2f}")

    def render_documento_origen_app(self, record):
        if not record.documento_origen_app:
            return format_html('<span class="text-muted small">—</span>')
        return format_html(
            '<span class="text-muted small">{} / {} #{}</span>',
            record.documento_origen_app, record.documento_origen_modelo or "", record.documento_origen_id or "",
        )

    def render_reversada(self, value):
        if value:
            return format_html('<span class="badge bg-secondary">Reversada</span>')
        return format_html('<span class="badge bg-success">Activa</span>')


class PlantillaContableTable(tables.Table):
    nombre = tables.Column(verbose_name="Nombre")
    tipo_transaccion = tables.Column(verbose_name="Tipo")
    modo = tables.Column(empty_values=(), orderable=False, verbose_name="Modo")
    lineas_count = tables.Column(verbose_name="Líneas", orderable=False)
    activo = tables.Column(verbose_name="Estado")
    created_at = tables.DateColumn(verbose_name="Creada", format="d M Y")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = PlantillaContable
        fields = ()
        sequence = (
            "nombre", "tipo_transaccion", "modo", "lineas_count",
            "activo", "created_at", "acciones",
        )
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-plantillas"}
        empty_text = "No se encontraron plantillas contables"
        order_by = ("-activo", "tipo_transaccion")

    def render_nombre(self, value):
        if not value:
            return format_html('<span class="text-muted fst-italic">Sin nombre</span>')
        return value

    def render_tipo_transaccion(self, value):
        cls, label = _BADGE_TIPO_PLANTILLA.get(value, ("bg-secondary", value or "Resolver"))
        return format_html('<span class="badge {}">{}</span>', cls, label)

    def render_modo(self, record):
        if record.tipo_transaccion:
            return format_html('<span class="badge bg-dark">Motor</span>')
        return format_html('<span class="badge bg-light text-dark border">Resolver</span>')

    def render_lineas_count(self, value):
        return format_html('<span class="badge bg-secondary">{}</span>', value or 0)

    def render_activo(self, value):
        if value:
            return format_html('<span class="badge bg-success">Activa</span>')
        return format_html('<span class="badge bg-danger">Inactiva</span>')

    def render_acciones(self, record):
        return format_html(
            '<div class="btn-group btn-group-sm">'
            '<button type="button" class="btn btn-outline-secondary btn-ver-plantilla" data-uuid="{0}" title="Ver detalle">'
            '<i class="bi bi-eye"></i></button>'
            '<button type="button" class="btn btn-outline-primary btn-editar-plantilla" data-uuid="{0}" title="Editar">'
            '<i class="bi bi-pencil"></i></button>'
            '<button type="button" class="btn btn-outline-danger btn-eliminar-plantilla" data-uuid="{0}" title="Eliminar">'
            '<i class="bi bi-trash"></i></button>'
            "</div>",
            record.uuid,
        )
