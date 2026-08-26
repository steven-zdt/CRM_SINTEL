"""
ContabilidadReportProvider -- FASE 19 (mision Reporting Hub).

IMPORTANTE (regla explicita de la mision): el calculo del Balance de Prueba
NO se mueve fuera de Contabilidad. Este adapter unicamente ENVUELVE
`balance_prueba_selector` (apps/tenant/contabilidad/services/selectors.py,
corregido y verificado en vivo en la mision CONT-19) para exponerlo en el
catalogo transversal -- cero logica contable vive aqui.

Solo se adapta `balance_prueba` en esta pasada. `estado_resultados` y
`get_libro_diario_periodo` tienen una forma de salida distinta (listas
anidadas ingresos/gastos/costos + totales, no filas planas) que no encaja
sin diseño adicional en el contrato tabular generico de ReportResult --
quedan diferidos (ver docs/reporting/REPORTING_ARCHITECTURE.md, loop de
expansion) en vez de forzar un aplanado apresurado.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

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
from apps.services.reporting.query_engine import ReportValidationError

_DATASET_ID = "contabilidad.balance_prueba"

_DIMENSIONS = (
    ReportField("codigo", "Codigo PUC", FieldType.STRING, source="codigo"),
    ReportField("nombre", "Nombre de cuenta", FieldType.STRING, source="nombre"),
)

_MEASURES = (
    ReportMeasure("saldo_anterior", "Saldo anterior", FieldType.DECIMAL, Aggregation.SUM, source="saldo_anterior"),
    ReportMeasure("debito", "Debito del periodo", FieldType.DECIMAL, Aggregation.SUM, source="debito"),
    ReportMeasure("credito", "Credito del periodo", FieldType.DECIMAL, Aggregation.SUM, source="credito"),
    ReportMeasure("nuevo_saldo", "Nuevo saldo", FieldType.DECIMAL, Aggregation.SUM, source="nuevo_saldo"),
)

_FILTERS = (
    ReportFilterSpec("fecha_inicio", "Fecha inicio", FieldType.DATE, required=True),
    ReportFilterSpec("fecha_fin", "Fecha fin", FieldType.DATE, required=True),
)

_DATASET = ReportDataset(
    dataset_id=_DATASET_ID,
    owner_app="contabilidad",
    name="Balance de Prueba",
    description=(
        "Saldos y movimientos por cuenta PUC para un periodo. Adapter de "
        "solo lectura sobre balance_prueba_selector -- el calculo permanece "
        "en Contabilidad. Siempre devuelve el desglose completo por cuenta; "
        "group_by/measures del request se ignoran (el selector ya agrupa)."
    ),
    dimensions=_DIMENSIONS,
    measures=_MEASURES,
    filters=_FILTERS,
    default_ordering="codigo",
    export_formats=("json", "csv", "xlsx"),
    scope_fields=("empresa",),
)


class ContabilidadReportProvider:
    def list_datasets(self) -> list[ReportDataset]:
        return [_DATASET]

    def get_dataset(self, dataset_id: str) -> ReportDataset | None:
        return _DATASET if dataset_id == _DATASET_ID else None

    def execute(self, request: ReportRequest, scope) -> ReportResult:
        from apps.tenant.contabilidad.services.selectors import balance_prueba_selector

        fecha_inicio = _parse_date(request.filters.get("fecha_inicio"))
        fecha_fin = _parse_date(request.filters.get("fecha_fin"))

        filas = balance_prueba_selector(scope.empresa_id, fecha_inicio, fecha_fin)

        columns = ("codigo", "nombre") + tuple(m.name for m in _MEASURES)
        rows = []
        totals = {m.name: Decimal("0") for m in _MEASURES}
        for fila in filas:
            row = {"codigo": fila["codigo"], "nombre": fila["nombre"]}
            for measure in _MEASURES:
                value = fila[measure.name]
                row[measure.name] = float(value)
                totals[measure.name] += value
            rows.append(row)

        return ReportResult(
            dataset_id=_DATASET_ID,
            columns=columns,
            rows=rows,
            totals={k: float(v) for k, v in totals.items()},
            filters_applied={"fecha_inicio": str(fecha_inicio), "fecha_fin": str(fecha_fin)},
            dimensions=("codigo", "nombre"),
            generated_at=datetime.now(UTC),
            execution_time_ms=0.0,
            page=1,
            page_size=len(rows) or 1,
            count=len(rows),
        )


def _parse_date(value) -> date:
    if value is None:
        raise ReportValidationError("fecha_inicio/fecha_fin son obligatorios para 'contabilidad.balance_prueba'")
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
