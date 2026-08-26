"""
InventarioReportProvider -- dataset `inventario.movimientos` (mision
Reporting Hub, loop de expansion documentado en
docs/reporting/REPORTING_ARCHITECTURE.md §8).

Fuente real: `MovimientoInventario` (el Kardex real, escrito exclusivamente
por `KardexService` -- Reporting NO escribe inventario, solo lee). Se
escopea a movimientos de PRODUCTO (`producto__isnull=False`) -- los
movimientos de ActivoFijo (asignacion/mantenimiento) son un dominio
conceptualmente distinto (gestion de activos, no Kardex de stock) y quedan
fuera de este dataset hasta que exista evidencia de necesidad real.

No se expone una medida "stock actual" -- eso es un SALDO (snapshot de
`Producto.stock_actual`/`StockPorSedeSelector`), no un dato agregable por
periodo como los movimientos; mezclar ambos en un mismo dataset tabular
confundiria "cuanto se movio en el periodo" con "cuanto hay ahora". Se deja
como un dataset futuro si hay demanda real (mismo criterio de "no inventar"
usado en la mision Tax Service).
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from django.db.models import Count, ExpressionWrapper, F, Sum
from django.db.models import DecimalField as DecimalFieldType

from apps.services.reporting.contracts import (
    Aggregation,
    FieldType,
    ReportDataset,
    ReportField,
    ReportFilterSpec,
    ReportMeasure,
    ReportRequest,
    ReportResult,
)

_DATASET_ID = "inventario.movimientos"

_DIMENSIONS = (
    ReportField("fecha", "Fecha", FieldType.DATE, source="created_at__date"),
    ReportField("sede", "Sede", FieldType.STRING, source="sede__nombre"),
    ReportField("producto", "Producto", FieldType.STRING, source="producto__nombre"),
    ReportField("categoria", "Categoria", FieldType.STRING, source="producto__categoria__nombre"),
    ReportField("tipo", "Tipo de movimiento", FieldType.STRING, source="tipo"),
)

_MEASURES = (
    ReportMeasure("cantidad_movimientos", "Cantidad de movimientos", FieldType.INTEGER, Aggregation.COUNT, source="id"),
    ReportMeasure("cantidad", "Cantidad (unidades)", FieldType.DECIMAL, Aggregation.SUM, source="cantidad"),
    ReportMeasure("costo_total", "Costo total", FieldType.DECIMAL, Aggregation.SUM, source="__costo_total__"),
)

_FILTERS = (
    ReportFilterSpec("fecha_inicio", "Fecha inicio", FieldType.DATE),
    ReportFilterSpec("fecha_fin", "Fecha fin", FieldType.DATE),
    ReportFilterSpec("tipo", "Tipo de movimiento", FieldType.STRING),
    ReportFilterSpec("producto_id", "Producto", FieldType.INTEGER),
)

_DATASET = ReportDataset(
    dataset_id=_DATASET_ID,
    owner_app="inventario",
    name="Movimientos de Inventario",
    description=(
        "Entradas, salidas y traslados de producto (Kardex), leidos directo "
        "de MovimientoInventario -- KardexService sigue siendo el SSoT de "
        "escritura. `tipo` expone los valores reales (ENTRADA_COMPRA, "
        "SALIDA_VENTA, etc.) -- filtrar/agrupar por tipo para separar "
        "entradas de salidas, en vez de una clasificacion inventada."
    ),
    dimensions=_DIMENSIONS,
    measures=_MEASURES,
    filters=_FILTERS,
    default_ordering="-fecha",
    export_formats=("json", "csv", "xlsx"),
    scope_fields=("empresa", "sede"),
)

def _costo_total_expr() -> ExpressionWrapper:
    # WARNING: BUGFIX: confirmado en vivo -- reusar la MISMA instancia de
    # ExpressionWrapper (creada una sola vez a nivel de modulo) entre el
    # .annotate() de values_qs y el .aggregate() de totals_qs rompia con
    # "'...' is an aggregate" (Django marca/resuelve la expresion la primera
    # vez que se usa en una query; una segunda query con la misma instancia
    # ya no es valida). Se construye una instancia NUEVA en cada llamada.
    return ExpressionWrapper(F("cantidad") * F("costo_unitario"), output_field=DecimalFieldType(max_digits=18, decimal_places=2))


_AGGREGATORS = {
    "cantidad_movimientos": lambda source: Count(source),
    "cantidad": lambda source: Sum(source),
    "costo_total": lambda source: Sum(_costo_total_expr()),
}


class InventarioReportProvider:
    def list_datasets(self) -> list[ReportDataset]:
        return [_DATASET]

    def get_dataset(self, dataset_id: str) -> ReportDataset | None:
        return _DATASET if dataset_id == _DATASET_ID else None

    def execute(self, request: ReportRequest, scope) -> ReportResult:
        from apps.tenant.inventario.models import MovimientoInventario

        qs = scope.filter(MovimientoInventario).filter(producto__isnull=False)

        filters = request.filters
        if filters.get("fecha_inicio"):
            qs = qs.filter(created_at__date__gte=filters["fecha_inicio"])
        if filters.get("fecha_fin"):
            qs = qs.filter(created_at__date__lte=filters["fecha_fin"])
        if filters.get("tipo"):
            qs = qs.filter(tipo=filters["tipo"])
        if filters.get("producto_id"):
            qs = qs.filter(producto_id=filters["producto_id"])

        group_by = request.group_by or ("tipo",)
        measures = request.measures or tuple(m.name for m in _MEASURES)

        group_sources = {name: _DATASET.get_dimension(name).source for name in group_by}

        # WARNING: BUGFIX (confirmado en vivo): la medida `cantidad` colisiona
        # con el nombre real del campo del modelo `MovimientoInventario.cantidad`.
        # Al pasar ambos en el MISMO annotate()/aggregate() (`cantidad=Sum('cantidad')`
        # junto a `costo_total=Sum(F('cantidad')*F('costo_unitario'))`), Django
        # resuelve el `F('cantidad')` del segundo contra el ALIAS ya agregado
        # del primero (no contra el campo crudo), y explota con "'...' is an
        # aggregate". Se usa un alias interno prefijado (`m__<medida>`) para
        # que nunca coincida con un nombre de campo real, y se remapea al
        # nombre publico de la medida al leer los resultados.
        def _build_annotations() -> dict:
            # Se reconstruye (no se reutiliza un dict/expresion ya armado)
            # para cada query -- ver _costo_total_expr().
            return {f"m__{name}": _AGGREGATORS[name](_DATASET.get_measure(name).source) for name in measures}

        values_qs = qs.values(*group_sources.values()).annotate(**_build_annotations())

        if request.order_by:
            order_field = request.order_by.lstrip("-")
            prefix = "-" if request.order_by.startswith("-") else ""
            resolved = group_sources.get(order_field, order_field if order_field in measures else None)
            if resolved:
                values_qs = values_qs.order_by(f"{prefix}{resolved}")
        else:
            values_qs = values_qs.order_by(*[f"-{s}" for s in group_sources.values()][:1] or ["-created_at__date"])

        count = values_qs.count()
        start = (request.page - 1) * request.page_size
        page_rows = list(values_qs[start:start + request.page_size])

        rows = []
        for raw in page_rows:
            row = {}
            for dim_name, source in group_sources.items():
                value = raw[source]
                row[dim_name] = value.isoformat() if hasattr(value, "isoformat") else value
            for measure_name in measures:
                value = raw[f"m__{measure_name}"]
                row[measure_name] = float(value) if isinstance(value, Decimal) else value
            rows.append(row)

        totals_qs = qs.aggregate(**_build_annotations())
        totals = {
            name[len("m__"):]: (float(value) if isinstance(value, Decimal) else value)
            for name, value in totals_qs.items()
        }

        return ReportResult(
            dataset_id=_DATASET_ID,
            columns=tuple(group_by) + tuple(measures),
            rows=rows,
            totals=totals,
            filters_applied=dict(filters),
            dimensions=tuple(group_by),
            generated_at=datetime.now(UTC),
            execution_time_ms=0.0,
            page=request.page,
            page_size=request.page_size,
            count=count,
        )
