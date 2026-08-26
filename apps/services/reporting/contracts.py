"""
Contratos genericos del Reporting Hub (mision Reporting Hub, FASE 4/7/9/13).

WARNING: PRINCIPIO CENTRAL (igual que apps/services/document_intake/contracts.py):
este modulo NO conoce Factura/Venta/Compra/Cliente/Producto/Empleado ni ningun
modelo Django. Solo conoce el VOCABULARIO de un reporte (dataset, dimension,
medida, filtro, request, result) -- cada app de dominio decide que datos
expone implementando ReportProvider en su propio paquete
(apps/tenant/<dominio>/reporting/provider.py).

Reporting NO es dueño de los datos (ver docs/reporting/REPORTING_BASELINE.md).
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


class FieldType(str, enum.Enum):
    """Tipo declarado de una dimension/medida/filtro -- usado para validar
    el ReportRequest contra el catalogo antes de ejecutar nada (Regla
    Absoluta #4: el frontend nunca envia SQL/campo/tabla libre)."""
    STRING = "STRING"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    DATE = "DATE"
    DATETIME = "DATETIME"
    BOOLEAN = "BOOLEAN"


class Aggregation(str, enum.Enum):
    """Funcion de agregacion declarada de una medida."""
    SUM = "SUM"
    COUNT = "COUNT"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"


@dataclass(frozen=True)
class ReportField:
    """Dimension declarada de un dataset (FASE 5). `source` es el nombre
    interno que el Provider usa para resolverla contra su propio queryset --
    Reporting nunca interpreta `source`, solo lo pasa de vuelta al Provider
    dueño del dataset."""
    name: str
    label: str
    field_type: FieldType
    source: str
    description: str = ""


@dataclass(frozen=True)
class ReportMeasure:
    """Medida declarada de un dataset (FASE 6)."""
    name: str
    label: str
    field_type: FieldType
    aggregation: Aggregation
    source: str
    description: str = ""


@dataclass(frozen=True)
class ReportFilterSpec:
    """Filtro declarado que el catalogo permite solicitar para un dataset.
    Solo metadata -- el VALOR del filtro llega en ReportRequest.filters."""
    name: str
    label: str
    field_type: FieldType
    description: str = ""
    required: bool = False


@dataclass(frozen=True)
class ReportDataset:
    """Contrato de un dataset publicado por una app de dominio (FASE 4).

    NO incluye modelos Django, nombres de tabla, ni SQL -- solo metadata
    declarativa. `scope_fields` le dice al Scope Engine que niveles
    organizacionales aplican a este dataset (ej. un dataset sin campo sede no
    debe intentar filtrar por sede).
    """
    dataset_id: str
    owner_app: str
    name: str
    description: str
    dimensions: tuple[ReportField, ...] = ()
    measures: tuple[ReportMeasure, ...] = ()
    filters: tuple[ReportFilterSpec, ...] = ()
    default_ordering: str | None = None
    export_formats: tuple[str, ...] = ("json", "csv")
    scope_fields: tuple[str, ...] = ("empresa",)  # subset of ("empresa", "sede", "area")

    def get_measure(self, name: str) -> ReportMeasure | None:
        return next((m for m in self.measures if m.name == name), None)

    def get_dimension(self, name: str) -> ReportField | None:
        return next((d for d in self.dimensions if d.name == name), None)

    def get_filter_spec(self, name: str) -> ReportFilterSpec | None:
        return next((f for f in self.filters if f.name == name), None)


@dataclass(frozen=True)
class ReportRequest:
    """Solicitud de ejecucion de un reporte (FASE 9). Solo admite lo que el
    Dataset declara -- ReportQueryEngine valida cada campo contra el
    catalogo antes de llamar al Provider (Regla Absoluta #4)."""
    dataset_id: str
    filters: dict[str, Any] = field(default_factory=dict)
    group_by: tuple[str, ...] = ()
    measures: tuple[str, ...] = ()
    order_by: str | None = None
    page: int = 1
    page_size: int = 50


@dataclass
class ReportResult:
    """Resultado estandar de una ejecucion (FASE 13). No incluye nada que el
    usuario no tenga permiso de ver -- el Provider es responsable de eso
    dentro del scope recibido."""
    dataset_id: str
    columns: tuple[str, ...]
    rows: list[dict[str, Any]]
    totals: dict[str, Any]
    filters_applied: dict[str, Any]
    dimensions: tuple[str, ...]
    generated_at: datetime
    execution_time_ms: float
    page: int = 1
    page_size: int = 50
    count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "columns": list(self.columns),
            "rows": self.rows,
            "totals": self.totals,
            "filters_applied": self.filters_applied,
            "dimensions": list(self.dimensions),
            "generated_at": self.generated_at.isoformat(),
            "execution_time_ms": self.execution_time_ms,
            "page": self.page,
            "page_size": self.page_size,
            "count": self.count,
        }


@runtime_checkable
class ReportProvider(Protocol):
    """Contrato que cada dominio implementa (FASE 7). Vive en
    apps/tenant/<dominio>/reporting/provider.py. El Query Engine NUNCA
    conoce los modelos internos de ningun Provider -- solo llama estos tres
    metodos."""

    def list_datasets(self) -> list[ReportDataset]:
        ...

    def get_dataset(self, dataset_id: str) -> ReportDataset | None:
        ...

    def execute(self, request: ReportRequest, scope: Any) -> ReportResult:
        """`scope` es un apps.tenant.core.services.organizational_scope.
        OrganizationalScope ya resuelto -- el Provider debe aplicarlo a su
        propio queryset (via scope.filter(Model) o manualmente) antes de
        agregar. Reporting no valida esto por el Provider; es la misma
        confianza de dominio que ya existe en Contabilidad/Facturas/etc."""
        ...
