"""
Tabla server-rendered (django-tables2) para categorias de Inventario. Los
listados de Productos, Servicios y Activos Fijos migraron a DataTables (ver
docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md) -- ProductoTable
retirada, ver ProductoViewSet.dt(); ServicioTable retirada, ver
ServicioViewSet.dt(); ActivoFijoTable retirada, ver ActivoFijoViewSet.dt()
(sus KPIs se extrajeron a ActivoFijoKpisView, ver views.py).

"Movimientos Recientes" (Kardex) NO se migra -- consume
`get_movimientos_timeline()`, que combina MovimientoInventario +
HistorialServicio en una lista de dicts en Python (Ledger Universal), el
mismo tipo de vista agregada cross-model que ya quedo fuera de alcance en
`contabilidad` (ver REPORTE_FASE_5_BIS_CONTABILIDAD.md §2).
"""

import django_tables2 as tables
from django.utils.html import format_html

from apps.tenant.inventario.models import CategoriaItem

_BADGE_APLICACION = {
    "TODO": ("bg-primary", "Todos"),
    "PRODUCTO": ("bg-info", "Productos"),
    "SERVICIO": ("bg-warning", "Servicios"),
    "ACTIVO": ("bg-secondary", "Activos"),
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
