"""
Tablas server-rendered (django-tables2) para los listados de Inventario.

Expansion Fase 5-BIS (ver PLAN_UNICO_CORRECCIONES.md) del patron ya aplicado
en gastos/facturas/compras/contabilidad/ventas/bancos/empleados. Cubre las
4 grillas CRUD planas del modulo (categorias, productos, servicios, activos
fijos). "Movimientos Recientes" (Kardex) NO se migra -- consume
`get_movimientos_timeline()`, que combina MovimientoInventario +
HistorialServicio en una lista de dicts en Python (Ledger Universal), el
mismo tipo de vista agregada cross-model que ya quedo fuera de alcance en
`contabilidad` (ver REPORTE_FASE_5_BIS_CONTABILIDAD.md §2).
"""
import django_tables2 as tables
from django.utils.html import format_html

from apps.tenant.inventario.models import ActivoFijo, CategoriaItem, Producto, Servicio

_BADGE_APLICACION = {
    "TODO": ("bg-primary", "Todos"),
    "PRODUCTO": ("bg-info", "Productos"),
    "SERVICIO": ("bg-warning", "Servicios"),
    "ACTIVO": ("bg-secondary", "Activos"),
}

_BADGE_ESTADO_ACTIVO = {
    "ACTIVO": ("bg-success", "bi-check-circle-fill", "En Uso"),
    "MANTENIMIENTO": ("bg-warning", "bi-tools", "Mantenimiento"),
    "BAJA": ("bg-danger", "bi-x-circle-fill", "De Baja"),
    "VENDIDO": ("bg-secondary", "bi-tag-fill", "Vendido"),
}


class CategoriaItemTable(tables.Table):
    nombre = tables.Column(verbose_name="Nombre")
    descripcion = tables.Column(verbose_name="Descripción")
    aplicacion = tables.Column(verbose_name="Aplicación")
    activo = tables.Column(verbose_name="Estado")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = CategoriaItem
        fields = ()
        sequence = ("nombre", "descripcion", "aplicacion", "activo", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-categorias"}
        empty_text = "No hay categorías registradas"
        order_by = "nombre"

    def render_descripcion(self, value):
        if not value:
            return format_html('<span class="text-muted">Sin descripción</span>')
        return value

    def render_aplicacion(self, value):
        cls, label = _BADGE_APLICACION.get(value, ("bg-secondary", value or "-"))
        return format_html('<span class="badge {}">{}</span>', cls, label)

    def render_activo(self, value):
        if value:
            return format_html('<span class="badge bg-success">Activo</span>')
        return format_html('<span class="badge bg-secondary">Inactivo</span>')

    def render_acciones(self, record):
        return format_html(
            '<div class="btn-group btn-group-sm" role="group">'
            '<button type="button" class="btn btn-outline-primary btn-edit-categoria" data-uuid="{0}" title="Editar" aria-label="Editar categoría">'
            '<i class="bi bi-pencil"></i></button>'
            '<button type="button" class="btn btn-outline-danger btn-delete-categoria" data-uuid="{0}" title="Eliminar" aria-label="Eliminar categoría">'
            '<i class="bi bi-trash"></i></button>'
            "</div>",
            record.uuid,
        )


class ProductoTable(tables.Table):
    nombre = tables.Column(verbose_name="Producto")
    stock_actual = tables.Column(verbose_name="Stock")
    precio_venta = tables.Column(verbose_name="Precio / Costo")
    activo = tables.Column(verbose_name="Estado")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = Producto
        fields = ()
        sequence = ("nombre", "stock_actual", "precio_venta", "activo", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-productos"}
        empty_text = "No hay productos registrados"
        order_by = "nombre"

    def render_nombre(self, record):
        cat = format_html(
            '<span class="badge bg-light text-secondary border" style="font-size:.65rem;font-weight:500">{}</span>',
            record.categoria.nombre,
        ) if record.categoria_id else ""
        cod = format_html(
            '<span class="font-monospace text-muted me-1" style="font-size:.72rem">{}</span>', record.codigo
        ) if record.codigo else ""
        return format_html(
            '<div class="py-1 lh-sm"><div class="fw-semibold">{}</div>'
            '<div class="d-flex align-items-center gap-1 mt-1">{}{}</div></div>',
            record.nombre or "—", cod, cat,
        )

    def render_stock_actual(self, record):
        actual = record.stock_actual or 0
        minimo = record.stock_minimo or 0
        alerta = actual <= minimo
        cls = "bg-danger" if alerta else "bg-success"
        icon = format_html('<i class="bi bi-exclamation-triangle-fill me-1" style="font-size:.7rem"></i>') if alerta else ""
        unidad = format_html('<span class="text-muted">{}</span>', record.unidad) if record.unidad else ""
        return format_html(
            '<div class="text-center lh-sm"><span class="badge {}">{}{} {}</span>'
            '<div class="text-muted mt-1" style="font-size:.68rem">mín {}</div></div>',
            cls, icon, f"{actual:g}", unidad, f"{minimo:g}",
        )

    def render_precio_venta(self, record):
        precio = f"${record.precio_venta:,.0f}" if record.precio_venta else "$0"
        costo = format_html(
            '<div class="text-muted mt-1" style="font-size:.72rem">Costo: ${}</div>', f"{record.costo_promedio:,.0f}"
        ) if record.costo_promedio else ""
        return format_html('<div class="text-end lh-sm"><div class="fw-semibold">{}</div>{}</div>', precio, costo)

    def render_activo(self, value):
        if value:
            return format_html('<span class="badge bg-success-subtle text-success border border-success-subtle">Activo</span>')
        return format_html('<span class="badge bg-secondary-subtle text-secondary border">Inactivo</span>')

    def render_acciones(self, record):
        return format_html(
            '<div class="btn-group btn-group-sm" role="group">'
            '<button type="button" class="btn btn-outline-primary btn-edit-producto" data-uuid="{0}" title="Editar" aria-label="Editar producto">'
            '<i class="bi bi-pencil"></i></button>'
            '<button type="button" class="btn btn-outline-info btn-ver-kardex" data-uuid="{0}" title="Kardex" aria-label="Ver kardex del producto">'
            '<i class="bi bi-list-ul"></i></button>'
            '<button type="button" class="btn btn-outline-danger btn-delete-producto" data-uuid="{0}" title="Eliminar" aria-label="Eliminar producto">'
            '<i class="bi bi-trash"></i></button>'
            "</div>",
            record.uuid,
        )


class ServicioTable(tables.Table):
    codigo = tables.Column(verbose_name="Código")
    nombre = tables.Column(verbose_name="Servicio")
    categoria = tables.Column(accessor="categoria__nombre", verbose_name="Categoría", order_by=("categoria__nombre",))
    precio_venta = tables.Column(verbose_name="Precio Venta")
    activo = tables.Column(verbose_name="Estado")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = Servicio
        fields = ()
        sequence = ("codigo", "nombre", "categoria", "precio_venta", "activo", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-servicios"}
        empty_text = "No hay servicios registrados"
        order_by = "nombre"

    def render_codigo(self, value):
        return value or "---"

    def render_categoria(self, record):
        if not record.categoria_id:
            return format_html('<span class="text-muted">Sin categoría</span>')
        return record.categoria.nombre

    def render_precio_venta(self, value):
        return f"${value:,.0f}" if value else "$0"

    def render_activo(self, value):
        if value:
            return format_html('<span class="badge bg-success">Activo</span>')
        return format_html('<span class="badge bg-secondary">Inactivo</span>')

    def render_acciones(self, record):
        return format_html(
            '<div class="btn-group btn-group-sm" role="group">'
            '<button type="button" class="btn btn-outline-primary btn-edit-servicio" data-uuid="{0}" title="Editar">'
            '<i class="bi bi-pencil"></i></button>'
            '<button type="button" class="btn btn-outline-danger btn-delete-servicio" data-uuid="{0}" title="Eliminar">'
            '<i class="bi bi-trash"></i></button>'
            "</div>",
            record.uuid,
        )


class ActivoFijoTable(tables.Table):
    nombre = tables.Column(verbose_name="Activo")
    fecha_adquisicion = tables.Column(verbose_name="Adquisición")
    estado = tables.Column(verbose_name="Estado")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = ActivoFijo
        fields = ()
        sequence = ("nombre", "fecha_adquisicion", "estado", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-activos"}
        empty_text = "No hay activos fijos registrados"
        order_by = "nombre"

    def render_nombre(self, record):
        cat = format_html(
            '<span class="badge bg-light text-secondary border" style="font-size:.65rem;font-weight:500">{}</span>',
            record.categoria.nombre,
        ) if record.categoria_id else ""
        cod = format_html(
            '<span class="font-monospace text-muted me-1" style="font-size:.72rem">{}</span>', record.codigo
        ) if record.codigo else ""
        resp = format_html(
            '<div class="mt-1"><span class="text-muted" style="font-size:.72rem"><i class="bi bi-person me-1"></i>{}</span></div>',
            record.responsable,
        ) if record.responsable else ""
        return format_html(
            '<div class="py-1 lh-sm"><div class="fw-semibold">{}</div>'
            '<div class="d-flex align-items-center gap-1 mt-1">{}{}</div>{}</div>',
            record.nombre or "—", cod, cat, resp,
        )

    def render_fecha_adquisicion(self, record):
        fecha = record.fecha_adquisicion.strftime("%d %b %Y") if record.fecha_adquisicion else "—"
        costo = format_html(
            '<div class="fw-semibold mt-1">${}</div>', f"{record.costo_adquisicion:,.0f}"
        ) if record.costo_adquisicion else ""
        return format_html(
            '<div class="text-end lh-sm"><div class="text-muted" style="font-size:.8rem">{}</div>{}</div>', fecha, costo
        )

    def render_estado(self, value):
        cls, icon, label = _BADGE_ESTADO_ACTIVO.get(value, ("bg-secondary", "bi-question-circle", value or "—"))
        return format_html('<span class="badge {}"><i class="bi {} me-1"></i>{}</span>', cls, icon, label)

    def render_acciones(self, record):
        return format_html(
            '<div class="btn-group btn-group-sm" role="group">'
            '<button type="button" class="btn btn-outline-primary btn-edit-activo" data-uuid="{0}" title="Editar">'
            '<i class="bi bi-pencil"></i></button>'
            '<button type="button" class="btn btn-outline-danger btn-delete-activo" data-uuid="{0}" title="Eliminar">'
            '<i class="bi bi-trash"></i></button>'
            "</div>",
            record.uuid,
        )
