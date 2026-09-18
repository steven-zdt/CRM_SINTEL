"""
FacturasResumenReportProvider -- dataset `facturas.resumen` (mision Reporting
Hub, loop de expansion documentado en docs/reporting/REPORTING_ARCHITECTURE.md
§8). Diferido explicitamente en REPORTING_CATALOG.md hasta esta iteracion.

Distinto de `tax.iva` (que solo cuenta estado='ACEPTADA', es fiscal): este
dataset expone TODAS las Facturas (cualquier estado/tipo), pensado para
visibilidad operativa del ciclo documental completo (documento/estado),
mismo criterio que `ventas.resumen` para Venta.

No incluye "saldo pendiente" -- desde la reestructuracion v4.0.0 (Facturas
= document store) ese dato ya no existe en Facturas en absoluto
(`Factura.saldo_pendiente`/`total_pagado_bancos` y `BancosBridge` fueron
removidos, era la direccion de dependencia inversa a la deseada). Si se
necesita un reporte de conciliacion bancaria por factura, ese dataset
deberia vivir del lado de Bancos (que ya expone `MovimientoBancarioAplicacion`
y `TransaccionBancaria.conciliado`), no aqui.
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

_DATASET_ID = "facturas.resumen"

_DIMENSIONS = (
    ReportField("fecha", "Fecha", FieldType.DATE, source="fecha_emision__date"),
    ReportField("naturaleza", "Naturaleza (venta/compra)", FieldType.STRING, source="naturaleza"),
    ReportField("estado", "Estado", FieldType.STRING, source="estado"),
    ReportField("tipo", "Tipo (FE/NC/ND)", FieldType.STRING, source="tipo"),
)

_MEASURES = (
    ReportMeasure("cantidad_documentos", "Cantidad de documentos", FieldType.INTEGER, Aggregation.COUNT, source="id"),
    ReportMeasure("subtotal", "Subtotal", FieldType.DECIMAL, Aggregation.SUM, source="subtotal"),
    ReportMeasure("impuestos", "Impuestos", FieldType.DECIMAL, Aggregation.SUM, source="impuestos"),
    ReportMeasure("total", "Total", FieldType.DECIMAL, Aggregation.SUM, source="total"),
)

_FILTERS = (
    ReportFilterSpec("fecha_inicio", "Fecha inicio", FieldType.DATE),
    ReportFilterSpec("fecha_fin", "Fecha fin", FieldType.DATE),
    ReportFilterSpec("naturaleza", "Naturaleza", FieldType.STRING),
    ReportFilterSpec("estado", "Estado", FieldType.STRING),
    ReportFilterSpec("tipo", "Tipo", FieldType.STRING),
)

_DATASET = ReportDataset(
    dataset_id=_DATASET_ID,
    owner_app="facturas",
    name="Resumen de Facturas",
    description=(
        "Todas las Facturas/Notas (cualquier estado y tipo) agregadas por "
        "fecha, naturaleza, estado y/o tipo. Para el detalle fiscal de IVA "
        "(solo ACEPTADA) usar tax.iva."
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
    "impuestos": lambda source: Sum(source),
    "total": lambda source: Sum(source),
}


class FacturasResumenReportProvider:
    def list_datasets(self) -> list[ReportDataset]:
        return [_DATASET]

    def get_dataset(self, dataset_id: str) -> ReportDataset | None:
        return _DATASET if dataset_id == _DATASET_ID else None

    def execute(self, request: ReportRequest, scope) -> ReportResult:
        from apps.tenant.facturas.models import Factura

        qs = scope.filter(Factura)

        filters = request.filters
        if filters.get("fecha_inicio"):
            qs = qs.filter(fecha_emision__date__gte=filters["fecha_inicio"])
        if filters.get("fecha_fin"):
            qs = qs.filter(fecha_emision__date__lte=filters["fecha_fin"])
        if filters.get("naturaleza"):
            qs = qs.filter(naturaleza=filters["naturaleza"])
        if filters.get("estado"):
            qs = qs.filter(estado=filters["estado"])
        if filters.get("tipo"):
            qs = qs.filter(tipo=filters["tipo"])

        group_by = request.group_by or ("estado",)
        measures = request.measures or tuple(m.name for m in _MEASURES)

        group_sources = {name: _DATASET.get_dimension(name).source for name in group_by}

        # Alias internos prefijados (m__<medida>) -- ver
        # docs/reporting/REPORTING_ARCHITECTURE.md §8.1 (bug real encontrado
        # en inventario.movimientos: alias de medida colisionando con un
        # campo real del modelo dentro de una expresion compuesta).
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
