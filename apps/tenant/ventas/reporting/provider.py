"""
VentasReportProvider -- FASE 14 (mision Reporting Hub, primer dataset real).

Implementa ReportProvider (apps/services/reporting/contracts.py) para el
dataset `ventas.resumen`. Reporting NO conoce `Venta`/`Cliente` -- toda la
consulta ORM vive aqui, dentro del dominio dueño de los datos.

`Venta` no tiene campo `sede` (verificado: apps/tenant/ventas/models.py no
declara SedeAwareModel) -- `scope_fields=("empresa",)` unicamente, sin
inventar una dimension de sede que el modelo no soporta (FASE 5).
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from django.db.models import Count, Sum

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

_DATASET_ID = "ventas.resumen"

_DIMENSIONS = (
    ReportField("fecha", "Fecha de emision", FieldType.DATE, source="fecha_emision"),
    ReportField("cliente", "Cliente", FieldType.STRING, source="cliente__razon_social"),
    ReportField("estado", "Estado", FieldType.STRING, source="estado"),
)

_MEASURES = (
    ReportMeasure("cantidad_ventas", "Cantidad de ventas", FieldType.INTEGER, Aggregation.COUNT, source="id"),
    ReportMeasure("subtotal", "Subtotal", FieldType.DECIMAL, Aggregation.SUM, source="subtotal"),
    ReportMeasure("impuestos", "Impuestos", FieldType.DECIMAL, Aggregation.SUM, source="impuestos"),
    ReportMeasure("total", "Total", FieldType.DECIMAL, Aggregation.SUM, source="total_neto"),
)

_FILTERS = (
    ReportFilterSpec("fecha_inicio", "Fecha inicio", FieldType.DATE),
    ReportFilterSpec("fecha_fin", "Fecha fin", FieldType.DATE),
    ReportFilterSpec("cliente_id", "Cliente", FieldType.INTEGER),
    ReportFilterSpec("estado", "Estado", FieldType.STRING),
)

_DATASET = ReportDataset(
    dataset_id=_DATASET_ID,
    owner_app="ventas",
    name="Resumen de Ventas",
    description="Ventas agregadas por fecha, cliente y/o estado.",
    dimensions=_DIMENSIONS,
    measures=_MEASURES,
    filters=_FILTERS,
    default_ordering="-fecha",
    export_formats=("json", "csv", "xlsx"),
    scope_fields=("empresa",),
)

_AGGREGATORS = {
    "cantidad_ventas": lambda source: Count(source),
    "subtotal": lambda source: Sum(source),
    "impuestos": lambda source: Sum(source),
    "total": lambda source: Sum(source),
}


class VentasReportProvider:
    def list_datasets(self) -> list[ReportDataset]:
        return [_DATASET]

    def get_dataset(self, dataset_id: str) -> ReportDataset | None:
        return _DATASET if dataset_id == _DATASET_ID else None

    def execute(self, request: ReportRequest, scope) -> ReportResult:
        from apps.tenant.ventas.models import Venta

        qs = scope.filter(Venta)

        filters = request.filters
        if filters.get("fecha_inicio"):
            qs = qs.filter(fecha_emision__date__gte=filters["fecha_inicio"])
        if filters.get("fecha_fin"):
            qs = qs.filter(fecha_emision__date__lte=filters["fecha_fin"])
        if filters.get("cliente_id"):
            qs = qs.filter(cliente_id=filters["cliente_id"])
        if filters.get("estado"):
            qs = qs.filter(estado=filters["estado"])

        group_by = request.group_by or ("fecha",)
        measures = request.measures or tuple(m.name for m in _MEASURES)

        group_sources = {name: _DATASET.get_dimension(name).source for name in group_by}
        annotations = {name: _AGGREGATORS[name](_DATASET.get_measure(name).source) for name in measures}

        values_qs = qs.values(*group_sources.values()).annotate(**annotations)

        if request.order_by:
            order_field = request.order_by.lstrip("-")
            prefix = "-" if request.order_by.startswith("-") else ""
            resolved = group_sources.get(order_field, order_field if order_field in measures else None)
            if resolved:
                values_qs = values_qs.order_by(f"{prefix}{resolved}")
        else:
            values_qs = values_qs.order_by(*[f"-{s}" for s in group_sources.values()][:1] or ["-fecha_emision"])

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
                value = raw[measure_name]
                row[measure_name] = float(value) if isinstance(value, Decimal) else value
            rows.append(row)

        totals_qs = qs.aggregate(**annotations)
        totals = {
            name: (float(value) if isinstance(value, Decimal) else value)
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
