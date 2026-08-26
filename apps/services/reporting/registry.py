"""
ReportRegistry -- FASE 8 (mision Reporting Hub).

Registro de datasets por dataset_id + resolucion de su Provider dueño.
Mismo patron que apps/services/document_intake/dispatcher.py: una sola
instancia compartida a nivel de modulo, poblada lazily por cada dominio via
su propio AppConfig.ready(). No conoce logica de negocio de ningun dominio.
"""
from __future__ import annotations

import logging

from apps.services.reporting.contracts import ReportDataset, ReportProvider

logger = logging.getLogger("apps.services.reporting")


class ReportRegistry:
    """Catalogo de datasets disponibles + Provider dueño de cada uno."""

    def __init__(self) -> None:
        self._providers: dict[str, ReportProvider] = {}
        self._datasets: dict[str, ReportDataset] = {}

    def register(self, provider: ReportProvider) -> None:
        """Registra un Provider y todos los datasets que declara. Un
        dataset_id duplicado entre dos Providers es un error de
        configuracion (dos dominios reclamando el mismo dataset) -- se
        registra el ultimo y se loguea la colision en vez de fallar el
        arranque del proceso completo."""
        for dataset in provider.list_datasets():
            if dataset.dataset_id in self._datasets:
                logger.warning(
                    "reporting.dataset_id_collision",
                    extra={"dataset_id": dataset.dataset_id, "owner_app": dataset.owner_app},
                )
            self._datasets[dataset.dataset_id] = dataset
            self._providers[dataset.dataset_id] = provider
        logger.info(
            "reporting.provider_registered",
            extra={
                "provider": type(provider).__name__,
                "datasets": [d.dataset_id for d in provider.list_datasets()],
            },
        )

    def get_dataset(self, dataset_id: str) -> ReportDataset | None:
        return self._datasets.get(dataset_id)

    def get_provider(self, dataset_id: str) -> ReportProvider | None:
        return self._providers.get(dataset_id)

    def list_datasets(self) -> list[ReportDataset]:
        return list(self._datasets.values())


# Instancia modulo-level compartida -- un solo registry para todo el
# proyecto, igual que apps/services/document_intake/dispatcher.py's
# `dispatcher`. Poblado por cada apps/tenant/<dominio>/reporting/provider.py
# via su AppConfig.ready().
registry = ReportRegistry()
