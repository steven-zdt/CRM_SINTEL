"""
FacturasTaxReportProvider -- dataset `tax.iva` (mision Tax Service).

Fuente real: `FacturaImpuesto` (tipo_impuesto='IVA') + `Factura.naturaleza`.
Confirmado en docs/tax/TAX_BASELINE.md §1/§3: esta es la UNICA fuente de IVA
generado/descontable con evidencia solida en el codigo -- NO se incluye
`compras.ItemOrdenCompra.valor_iva` (riesgo de doble conteo no descartado,
ver REVIEW en el baseline).

naturaleza='VENTA' -> IVA generado (la empresa emite, cobra IVA a clientes).
naturaleza='COMPRA' -> IVA descontable (la empresa recibe, paga IVA a proveedores).

Solo cuenta facturas estado='ACEPTADA' -- mismo criterio ya usado en
apps/tenant/dashboard/services/extractores/facturas_ext.py para "facturas
reales" (documentos rechazados/borrador no representan una obligacion fiscal
real).
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

_DATASET_ID = "tax.iva"

_DIMENSIONS = (
    ReportField("fecha", "Fecha", FieldType.DATE, source="factura__fecha_emision__date"),
    ReportField("naturaleza", "Naturaleza (VENTA=generado, COMPRA=descontable)", FieldType.STRING, source="factura__naturaleza"),
)

_MEASURES = (
    ReportMeasure("cantidad_lineas", "Cantidad de lineas", FieldType.INTEGER, Aggregation.COUNT, source="id"),
    ReportMeasure("base_imponible", "Base imponible", FieldType.DECIMAL, Aggregation.SUM, source="base_imponible"),
    ReportMeasure("valor_iva", "Valor IVA", FieldType.DECIMAL, Aggregation.SUM, source="valor_impuesto"),
)

_FILTERS = (
    ReportFilterSpec("fecha_inicio", "Fecha inicio", FieldType.DATE),
    ReportFilterSpec("fecha_fin", "Fecha fin", FieldType.DATE),
    ReportFilterSpec("naturaleza", "Naturaleza", FieldType.STRING),
)

_DATASET = ReportDataset(
    dataset_id=_DATASET_ID,
    owner_app="facturas",
    name="IVA (generado / descontable)",
    description=(
        "IVA generado (ventas) y descontable (compras) desde FacturaImpuesto. "
        "IVA_NETO = generado - descontable es un SALDO FISCAL CALCULADO, no un "
        "valor definitivo a pagar (no hay proceso formal de declaracion en "
        "este sistema todavia -- ver docs/tax/TAX_BASELINE.md §6)."
    ),
    dimensions=_DIMENSIONS,
    measures=_MEASURES,
    filters=_FILTERS,
    default_ordering="-fecha",
    export_formats=("json", "csv", "xlsx"),
    scope_fields=("empresa", "sede"),
)

_AGGREGATORS = {
    "cantidad_lineas": lambda source: Count(source),
    "base_imponible": lambda source: Sum(source),
    "valor_iva": lambda source: Sum(source),
}


class FacturasTaxReportProvider:
    def list_datasets(self) -> list[ReportDataset]:
        return [_DATASET]

    def get_dataset(self, dataset_id: str) -> ReportDataset | None:
        return _DATASET if dataset_id == _DATASET_ID else None

    def execute(self, request: ReportRequest, scope) -> ReportResult:
        from apps.tenant.facturas.models import Factura, FacturaImpuesto

        facturas_qs = scope.filter(Factura).filter(estado="ACEPTADA")
        qs = FacturaImpuesto.objects.filter(factura__in=facturas_qs, tipo_impuesto="IVA")

        filters = request.filters
        if filters.get("fecha_inicio"):
            qs = qs.filter(factura__fecha_emision__date__gte=filters["fecha_inicio"])
        if filters.get("fecha_fin"):
            qs = qs.filter(factura__fecha_emision__date__lte=filters["fecha_fin"])
        if filters.get("naturaleza"):
            qs = qs.filter(factura__naturaleza=filters["naturaleza"])

        group_by = request.group_by or ("naturaleza",)
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
            values_qs = values_qs.order_by(*[f"-{s}" for s in group_sources.values()][:1] or ["-factura__fecha_emision__date"])

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
        # SALDO_FISCAL_CALCULADO: generado - descontable, computado SOLO si
        # ambas medidas estan presentes -- no se inventa si el usuario pidio
        # un subconjunto de medidas.
        if "valor_iva" in measures and not request.group_by:
            generado = qs.filter(factura__naturaleza="VENTA").aggregate(t=Sum("valor_impuesto"))["t"] or Decimal("0")
            descontable = qs.filter(factura__naturaleza="COMPRA").aggregate(t=Sum("valor_impuesto"))["t"] or Decimal("0")
            totals["iva_generado"] = float(generado)
            totals["iva_descontable"] = float(descontable)
            totals["saldo_fiscal_calculado"] = float(generado - descontable)

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
