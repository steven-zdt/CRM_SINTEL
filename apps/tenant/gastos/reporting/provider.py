"""
GastosReportProvider -- dataset `gastos.resumen` (mision Reporting Hub, loop
de expansion documentado en docs/reporting/REPORTING_ARCHITECTURE.md §8).

Fuente real: `DocumentoSoporte`. Excluye `anulado=True` -- mismo criterio ya
usado en esta mision para Ventas (excluye ANULADA) y Facturas (solo ACEPTADA):
un documento anulado no representa una obligacion/gasto real.

No incluye IVA/retenciones -- confirmado en la mision Tax Service
(docs/tax/TAX_BASELINE.md §5): `DocumentoSoporte` no tiene ningun campo de
IVA, y sus retenciones ya se exponen en `tax.retenciones`
(documento_origen_app='gastos'). Duplicarlas aqui violaria la misma Regla
Absoluta de "una responsabilidad = una fuente de verdad".
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

_DATASET_ID = "gastos.resumen"

_DIMENSIONS = (
    ReportField("fecha", "Fecha", FieldType.DATE, source="fecha"),
    ReportField("sede", "Sede", FieldType.STRING, source="sede__nombre"),
    ReportField("categoria_contable", "Categoria contable", FieldType.STRING, source="categoria_contable"),
    ReportField("proveedor", "Proveedor", FieldType.STRING, source="proveedor__razon_social"),
)

_MEASURES = (
    ReportMeasure("cantidad_documentos", "Cantidad de documentos", FieldType.INTEGER, Aggregation.COUNT, source="id"),
    ReportMeasure("subtotal", "Subtotal", FieldType.DECIMAL, Aggregation.SUM, source="subtotal"),
    ReportMeasure("total", "Total", FieldType.DECIMAL, Aggregation.SUM, source="total"),
)

_FILTERS = (
    ReportFilterSpec("fecha_inicio", "Fecha inicio", FieldType.DATE),
    ReportFilterSpec("fecha_fin", "Fecha fin", FieldType.DATE),
    ReportFilterSpec("categoria_contable", "Categoria contable", FieldType.STRING),
    ReportFilterSpec("proveedor_id", "Proveedor", FieldType.INTEGER),
)

_DATASET = ReportDataset(
    dataset_id=_DATASET_ID,
    owner_app="gastos",
    name="Resumen de Gastos",
    description=(
        "Documentos Soporte agregados por fecha, sede, categoria contable "
        "y/o proveedor. No incluye IVA (DocumentoSoporte no lo tiene) ni "
        "retenciones (ver dataset tax.retenciones)."
    ),
    dimensions=_DIMENSIONS,
    measures=_MEASURES,
    filters=_FILTERS,
    default_ordering="-fecha",
    export_formats=("json", "csv", "xlsx"),
    scope_fields=("empresa", "sede"),
)

_AGGREGATORS = {
    "cantidad_documentos": lambda source: Count(source),
    "subtotal": lambda source: Sum(source),
    "total": lambda source: Sum(source),
}


class GastosReportProvider:
    def list_datasets(self) -> list[ReportDataset]:
        return [_DATASET]

    def get_dataset(self, dataset_id: str) -> ReportDataset | None:
        return _DATASET if dataset_id == _DATASET_ID else None

    def execute(self, request: ReportRequest, scope) -> ReportResult:
        from apps.tenant.gastos.models import DocumentoSoporte

        qs = scope.filter(DocumentoSoporte).filter(anulado=False)

        filters = request.filters
        if filters.get("fecha_inicio"):
            qs = qs.filter(fecha__gte=filters["fecha_inicio"])
        if filters.get("fecha_fin"):
            qs = qs.filter(fecha__lte=filters["fecha_fin"])
        if filters.get("categoria_contable"):
            qs = qs.filter(categoria_contable=filters["categoria_contable"])
        if filters.get("proveedor_id"):
            qs = qs.filter(proveedor_id=filters["proveedor_id"])

        group_by = request.group_by or ("categoria_contable",)
        measures = request.measures or tuple(m.name for m in _MEASURES)

        group_sources = {name: _DATASET.get_dimension(name).source for name in group_by}

        # WARNING: alias internos prefijados (m__<medida>) por seguridad --
        # evita cualquier colision entre el nombre de una medida y un campo
        # real del modelo si una medida futura se agrega como expresion
        # compuesta. Ver docs/reporting/REPORTING_ARCHITECTURE.md §8.1 (bug
        # real encontrado en inventario.movimientos).
        def _build_annotations() -> dict:
            return {f"m__{name}": _AGGREGATORS[name](_DATASET.get_measure(name).source) for name in measures}

        values_qs = qs.values(*group_sources.values()).annotate(**_build_annotations())

        if request.order_by:
            order_field = request.order_by.lstrip("-")
            prefix = "-" if request.order_by.startswith("-") else ""
            resolved = group_sources.get(order_field, order_field if order_field in measures else None)
            if resolved:
                values_qs = values_qs.order_by(f"{prefix}{resolved}")
        else:
            values_qs = values_qs.order_by(*[f"-{s}" for s in group_sources.values()][:1] or ["-fecha"])

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
