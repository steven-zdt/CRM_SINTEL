"""
ContabilidadReportProvider -- datasets `contabilidad.balance_prueba` (mision
Reporting Hub, FASE 19) y `tax.retenciones` (mision Tax Service).

IMPORTANTE (regla explicita de ambas misiones): el calculo del Balance de
Prueba NO se mueve fuera de Contabilidad -- este adapter unicamente ENVUELVE
`balance_prueba_selector` (apps/tenant/contabilidad/services/selectors.py,
corregido y verificado en vivo en la mision CONT-19). `tax.retenciones` lee
el modelo `Retencion` (el libro real, escrito exclusivamente por
`RetencionesService`) directo -- no hay selector de resumen existente que
envolver (confirmado en docs/tax/TAX_BASELINE.md §2), asi que la agregacion
vive aqui, en la app dueña del dato, no en Reporting.

Solo se adapta `balance_prueba` de los 3 reportes contables existentes.
`estado_resultados`/`get_libro_diario_periodo` tienen una forma de salida
distinta (listas anidadas, no filas planas) -- quedan diferidos (ver
docs/reporting/REPORTING_ARCHITECTURE.md, loop de expansion).
"""
from __future__ import annotations

from datetime import UTC, date, datetime
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
from apps.services.reporting.query_engine import ReportValidationError

# ============================================================================
# contabilidad.balance_prueba
# ============================================================================

_BALANCE_DATASET_ID = "contabilidad.balance_prueba"

_BALANCE_DIMENSIONS = (
    ReportField("codigo", "Codigo PUC", FieldType.STRING, source="codigo"),
    ReportField("nombre", "Nombre de cuenta", FieldType.STRING, source="nombre"),
)

_BALANCE_MEASURES = (
    ReportMeasure("saldo_anterior", "Saldo anterior", FieldType.DECIMAL, Aggregation.SUM, source="saldo_anterior"),
    ReportMeasure("debito", "Debito del periodo", FieldType.DECIMAL, Aggregation.SUM, source="debito"),
    ReportMeasure("credito", "Credito del periodo", FieldType.DECIMAL, Aggregation.SUM, source="credito"),
    ReportMeasure("nuevo_saldo", "Nuevo saldo", FieldType.DECIMAL, Aggregation.SUM, source="nuevo_saldo"),
)

_BALANCE_DATASET = ReportDataset(
    dataset_id=_BALANCE_DATASET_ID,
    owner_app="contabilidad",
    name="Balance de Prueba",
    description=(
        "Saldos y movimientos por cuenta PUC para un periodo. Adapter de "
        "solo lectura sobre balance_prueba_selector -- el calculo permanece "
        "en Contabilidad. Siempre devuelve el desglose completo por cuenta; "
        "group_by/measures del request se ignoran (el selector ya agrupa)."
    ),
    dimensions=_BALANCE_DIMENSIONS,
    measures=_BALANCE_MEASURES,
    filters=(
        ReportFilterSpec("fecha_inicio", "Fecha inicio", FieldType.DATE, required=True),
        ReportFilterSpec("fecha_fin", "Fecha fin", FieldType.DATE, required=True),
    ),
    default_ordering="codigo",
    export_formats=("json", "csv", "xlsx"),
    scope_fields=("empresa",),
)


def _parse_date(value, dataset_id: str) -> date:
    if value is None:
        raise ReportValidationError(f"fecha_inicio/fecha_fin son obligatorios para '{dataset_id}'")
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _execute_balance_prueba(request: ReportRequest, scope) -> ReportResult:
    from apps.tenant.contabilidad.services.selectors import balance_prueba_selector

    fecha_inicio = _parse_date(request.filters.get("fecha_inicio"), _BALANCE_DATASET_ID)
    fecha_fin = _parse_date(request.filters.get("fecha_fin"), _BALANCE_DATASET_ID)

    filas = balance_prueba_selector(scope.empresa_id, fecha_inicio, fecha_fin)

    columns = ("codigo", "nombre") + tuple(m.name for m in _BALANCE_MEASURES)
    rows = []
    totals = {m.name: Decimal("0") for m in _BALANCE_MEASURES}
    for fila in filas:
        row = {"codigo": fila["codigo"], "nombre": fila["nombre"]}
        for measure in _BALANCE_MEASURES:
            value = fila[measure.name]
            row[measure.name] = float(value)
            totals[measure.name] += value
        rows.append(row)

    return ReportResult(
        dataset_id=_BALANCE_DATASET_ID,
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


# ============================================================================
# tax.retenciones
# ============================================================================

_RETENCIONES_DATASET_ID = "tax.retenciones"

_RETENCIONES_DIMENSIONS = (
    # WARNING: Retencion no tiene un campo `fecha` propio (es un registro de
    # calculo, no un documento) -- se usa created_at como aproximacion al
    # momento real del documento (el Pull Model crea la Retencion al
    # importar/capturar el documento origen, muy cerca en el tiempo).
    # Documentado explicitamente, no presentado como "fecha del documento".
    ReportField("fecha", "Fecha de registro", FieldType.DATE, source="created_at__date"),
    ReportField("tipo", "Tipo de retencion", FieldType.STRING, source="tipo"),
    ReportField("naturaleza", "Naturaleza (VENTA=sufrida, COMPRA=practicada)", FieldType.STRING, source="naturaleza"),
    ReportField("documento_origen_app", "App origen", FieldType.STRING, source="documento_origen_app"),
)

_RETENCIONES_MEASURES = (
    ReportMeasure("cantidad", "Cantidad de retenciones", FieldType.INTEGER, Aggregation.COUNT, source="id"),
    ReportMeasure("base", "Base", FieldType.DECIMAL, Aggregation.SUM, source="base"),
    ReportMeasure("monto", "Monto neto (incluye reversas)", FieldType.DECIMAL, Aggregation.SUM, source="monto"),
)

_RETENCIONES_DATASET = ReportDataset(
    dataset_id=_RETENCIONES_DATASET_ID,
    owner_app="contabilidad",
    name="Retenciones (Retefuente / ReteICA / ReteIVA)",
    description=(
        "Retenciones aplicadas, leidas directo de Retencion (SSoT, escrito "
        "por RetencionesService). `monto` es neto de reversas: se suman "
        "TODAS las filas sin filtrar por `reversada` -- el original "
        "conserva su valor real (positivo) y la reversa ya viene con monto "
        "negativo, asi que la suma neta correctamente incluso cuando la "
        "reversa cae en otro periodo/documento que el original. WARNING: "
        "esto es DISTINTO del filtro reversada=False que usa "
        "RetencionesService.total_retenciones_por_documento() -- ese filtro "
        "es correcto para el saldo de UN documento especifico (excluye el "
        "original ya superseded), pero subcuenta en una agregacion por "
        "periodo/tipo si la reversa se atribuyo a un documento distinto "
        "(el original quedaria excluido sin que su reversa lo compense)."
    ),
    dimensions=_RETENCIONES_DIMENSIONS,
    measures=_RETENCIONES_MEASURES,
    filters=(
        ReportFilterSpec("fecha_inicio", "Fecha inicio", FieldType.DATE),
        ReportFilterSpec("fecha_fin", "Fecha fin", FieldType.DATE),
        ReportFilterSpec("tipo", "Tipo (RETEFUENTE/RETEICA/RETEIVA)", FieldType.STRING),
        ReportFilterSpec("naturaleza", "Naturaleza (VENTA/COMPRA)", FieldType.STRING),
    ),
    default_ordering="-fecha",
    export_formats=("json", "csv", "xlsx"),
    scope_fields=("empresa",),
)

_RETENCIONES_AGGREGATORS = {
    "cantidad": lambda source: Count(source),
    "base": lambda source: Sum(source),
    "monto": lambda source: Sum(source),
}


def _execute_retenciones(request: ReportRequest, scope) -> ReportResult:
    from apps.tenant.contabilidad.models import Retencion

    # WARNING: BUGFIX (encontrado al trazar la matematica de una reversa
    # cross-documento antes de escribir el test de regresion): NO se filtra
    # `reversada=False` aqui -- ver docstring de _RETENCIONES_DATASET.
    qs = scope.filter(Retencion)

    filters = request.filters
    if filters.get("fecha_inicio"):
        qs = qs.filter(created_at__date__gte=filters["fecha_inicio"])
    if filters.get("fecha_fin"):
        qs = qs.filter(created_at__date__lte=filters["fecha_fin"])
    if filters.get("tipo"):
        qs = qs.filter(tipo=filters["tipo"])
    if filters.get("naturaleza"):
        qs = qs.filter(naturaleza=filters["naturaleza"])

    group_by = request.group_by or ("tipo",)
    measures = request.measures or tuple(m.name for m in _RETENCIONES_MEASURES)

    group_sources = {name: _RETENCIONES_DATASET.get_dimension(name).source for name in group_by}
    annotations = {
        name: _RETENCIONES_AGGREGATORS[name](_RETENCIONES_DATASET.get_measure(name).source)
        for name in measures
    }

    values_qs = qs.values(*group_sources.values()).annotate(**annotations)

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
            value = raw[measure_name]
            row[measure_name] = float(value) if isinstance(value, Decimal) else value
        rows.append(row)

    totals_qs = qs.aggregate(**annotations)
    totals = {
        name: (float(value) if isinstance(value, Decimal) else value)
        for name, value in totals_qs.items()
    }

    return ReportResult(
        dataset_id=_RETENCIONES_DATASET_ID,
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


# ============================================================================
# Provider
# ============================================================================

_DATASETS = {
    _BALANCE_DATASET_ID: (_BALANCE_DATASET, _execute_balance_prueba),
    _RETENCIONES_DATASET_ID: (_RETENCIONES_DATASET, _execute_retenciones),
}


class ContabilidadReportProvider:
    def list_datasets(self) -> list[ReportDataset]:
        return [dataset for dataset, _ in _DATASETS.values()]

    def get_dataset(self, dataset_id: str) -> ReportDataset | None:
        entry = _DATASETS.get(dataset_id)
        return entry[0] if entry else None

    def execute(self, request: ReportRequest, scope) -> ReportResult:
        entry = _DATASETS.get(request.dataset_id)
        if entry is None:
            raise ReportValidationError(f"Dataset desconocido para ContabilidadReportProvider: {request.dataset_id}")
        _, executor = entry
        return executor(request, scope)
