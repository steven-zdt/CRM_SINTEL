"""
ReportQueryEngine -- FASE 12 (mision Reporting Hub).

Orquesta: Registry -> Dataset -> validacion contra catalogo (Regla Absoluta
#4: nada que el frontend envie puede saltarse el catalogo) -> Scope Engine
(FASE 10/11) -> Provider.execute() -> ReportResult. No conoce modelos
Django de ningun dominio -- solo el vocabulario declarado en contracts.py.
"""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from apps.services.reporting.contracts import ReportRequest, ReportResult
from apps.services.reporting.registry import ReportRegistry
from apps.services.reporting.registry import registry as default_registry
from apps.services.reporting.scope import enforce_requested_filters, resolve_effective_scope

logger = logging.getLogger("apps.services.reporting")


class ReportValidationError(Exception):
    """El ReportRequest solicita algo no declarado en el catalogo del
    dataset (filtro/dimension/medida desconocidos, dataset inexistente).
    Se mapea a HTTP 400 en la capa API."""


class ReportQueryEngine:
    def __init__(self, registry: ReportRegistry | None = None) -> None:
        self._registry = registry or default_registry

    def _validate_request(self, request: ReportRequest):
        dataset = self._registry.get_dataset(request.dataset_id)
        if dataset is None:
            raise ReportValidationError(f"Dataset desconocido: {request.dataset_id}")

        valid_dimensions = {d.name for d in dataset.dimensions}
        valid_measures = {m.name for m in dataset.measures}
        valid_filters = {f.name for f in dataset.filters}

        for dim in request.group_by:
            if dim not in valid_dimensions:
                raise ReportValidationError(
                    f"Dimension no declarada en el dataset '{dataset.dataset_id}': {dim}"
                )

        measures = request.measures or tuple(m.name for m in dataset.measures)
        for measure in measures:
            if measure not in valid_measures:
                raise ReportValidationError(
                    f"Medida no declarada en el dataset '{dataset.dataset_id}': {measure}"
                )

        for filter_name in request.filters:
            if filter_name not in valid_filters and filter_name not in ("sede", "area"):
                raise ReportValidationError(
                    f"Filtro no declarado en el dataset '{dataset.dataset_id}': {filter_name}"
                )

        for filter_spec in dataset.filters:
            if filter_spec.required and filter_spec.name not in request.filters:
                raise ReportValidationError(
                    f"Filtro obligatorio faltante para '{dataset.dataset_id}': {filter_spec.name}"
                )

        if request.order_by:
            order_field = request.order_by.lstrip("-")
            if order_field not in valid_dimensions and order_field not in valid_measures:
                raise ReportValidationError(
                    f"Campo de orden no declarado en el dataset '{dataset.dataset_id}': {request.order_by}"
                )

        if request.page < 1:
            raise ReportValidationError("page debe ser >= 1")
        if not (1 <= request.page_size <= 1000):
            raise ReportValidationError("page_size debe estar entre 1 y 1000")

        return dataset, measures

    def execute(self, request: ReportRequest, django_request) -> ReportResult:
        dataset, measures = self._validate_request(request)
        if measures != request.measures:
            request = ReportRequest(
                dataset_id=request.dataset_id,
                filters=request.filters,
                group_by=request.group_by,
                measures=measures,
                order_by=request.order_by,
                page=request.page,
                page_size=request.page_size,
            )

        scope = resolve_effective_scope(django_request)
        enforce_requested_filters(scope, request.filters)

        provider = self._registry.get_provider(request.dataset_id)
        if provider is None:
            raise ReportValidationError(f"Sin provider registrado para: {request.dataset_id}")

        started = time.monotonic()
        result = provider.execute(request, scope)
        elapsed_ms = (time.monotonic() - started) * 1000

        result.execution_time_ms = round(elapsed_ms, 2)
        if result.generated_at is None:
            result.generated_at = datetime.now(UTC)

        logger.info(
            "reporting.query_executed",
            extra={
                "dataset_id": request.dataset_id,
                "empresa_id": getattr(scope, "empresa_id", None),
                "execution_time_ms": result.execution_time_ms,
                "row_count": len(result.rows),
            },
        )
        return result
