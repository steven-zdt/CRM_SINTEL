"""
Tests puntuales del Reporting Hub -- registry + validacion del Query Engine.

Sin base de datos: usan un ReportProvider falso (no Django ORM) para probar
el contrato en aislamiento, igual que tests/services/document_ingest/ prueba
sus contratos sin tocar apps de dominio reales.
"""
from datetime import UTC, datetime

import pytest

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
from apps.services.reporting.query_engine import ReportQueryEngine, ReportValidationError
from apps.services.reporting.registry import ReportRegistry


class _FakeProvider:
    """Provider de prueba: una sola dimension/medida, sin ORM."""

    DATASET = ReportDataset(
        dataset_id="fake.dataset",
        owner_app="fake",
        name="Fake Dataset",
        description="Solo para pruebas del Query Engine.",
        dimensions=(ReportField("categoria", "Categoria", FieldType.STRING, source="categoria"),),
        measures=(ReportMeasure("total", "Total", FieldType.DECIMAL, Aggregation.SUM, source="total"),),
        filters=(ReportFilterSpec("categoria", "Categoria", FieldType.STRING),),
    )

    def list_datasets(self):
        return [self.DATASET]

    def get_dataset(self, dataset_id):
        return self.DATASET if dataset_id == "fake.dataset" else None

    def execute(self, request, scope):
        return ReportResult(
            dataset_id="fake.dataset",
            columns=("categoria", "total"),
            rows=[{"categoria": "A", "total": 100}],
            totals={"total": 100},
            filters_applied=dict(request.filters),
            dimensions=request.group_by,
            generated_at=datetime.now(UTC),
            execution_time_ms=0.0,
        )


@pytest.fixture
def registry():
    reg = ReportRegistry()
    reg.register(_FakeProvider())
    return reg


class TestReportRegistry:
    def test_register_expone_el_dataset(self, registry):
        assert registry.get_dataset("fake.dataset") is not None
        assert [d.dataset_id for d in registry.list_datasets()] == ["fake.dataset"]

    def test_dataset_desconocido_devuelve_none(self, registry):
        assert registry.get_dataset("no.existe") is None
        assert registry.get_provider("no.existe") is None


class TestReportQueryEngineValidation:
    """Regla Absoluta #4: nada fuera del catalogo puede ejecutarse.

    Todas estas solicitudes fallan en _validate_request(), ANTES de resolver
    scope -- por eso django_request=None es seguro aqui (nunca se toca)."""

    def test_dataset_desconocido_rechazado(self, registry):
        engine = ReportQueryEngine(registry=registry)
        request = ReportRequest(dataset_id="no.existe")
        with pytest.raises(ReportValidationError, match="Dataset desconocido"):
            engine.execute(request, django_request=None)

    def test_dimension_no_declarada_rechazada(self, registry):
        engine = ReportQueryEngine(registry=registry)
        request = ReportRequest(dataset_id="fake.dataset", group_by=("campo_inventado",))
        with pytest.raises(ReportValidationError, match="Dimension no declarada"):
            engine.execute(request, django_request=None)

    def test_medida_no_declarada_rechazada(self, registry):
        engine = ReportQueryEngine(registry=registry)
        request = ReportRequest(dataset_id="fake.dataset", measures=("medida_inventada",))
        with pytest.raises(ReportValidationError, match="Medida no declarada"):
            engine.execute(request, django_request=None)

    def test_filtro_no_declarado_rechazado(self, registry):
        engine = ReportQueryEngine(registry=registry)
        request = ReportRequest(dataset_id="fake.dataset", filters={"campo_inventado": "x"})
        with pytest.raises(ReportValidationError, match="Filtro no declarado"):
            engine.execute(request, django_request=None)

    def test_orden_no_declarado_rechazado(self, registry):
        engine = ReportQueryEngine(registry=registry)
        request = ReportRequest(dataset_id="fake.dataset", order_by="campo_inventado")
        with pytest.raises(ReportValidationError, match="Campo de orden no declarado"):
            engine.execute(request, django_request=None)

    def test_page_size_fuera_de_rango_rechazado(self, registry):
        engine = ReportQueryEngine(registry=registry)
        request = ReportRequest(dataset_id="fake.dataset", page_size=5000)
        with pytest.raises(ReportValidationError, match="page_size"):
            engine.execute(request, django_request=None)

    def test_filtro_declarado_pasa_validacion(self, registry):
        """No-regresion: un filtro SI declarado no debe ser rechazado por
        _validate_request -- llega hasta resolver_effective_scope, que aqui
        fallara (sin request real) confirmando que la validacion de
        catalogo ya paso limpio."""
        from apps.tenant.core.services.organizational_scope import OrganizationalScopeError

        engine = ReportQueryEngine(registry=registry)
        request = ReportRequest(dataset_id="fake.dataset", filters={"categoria": "A"})
        with pytest.raises(OrganizationalScopeError):
            engine.execute(request, django_request=None)
