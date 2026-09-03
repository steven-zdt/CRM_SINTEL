"""Busqueda semantica tenant-scoped sobre el Vector Store (AI-VECTOR-05).

REGLA (mandato AI-VECTOR-05): este servicio SOLO lee. Nunca crea ni modifica
facturas, clientes, productos, asientos, bancos ni inventario. Devuelve
CANDIDATOS de contexto -- nunca la fuente de verdad de un dato transaccional
(montos, saldos, estados): eso sigue viniendo de las READ Tools deterministas.

Aislamiento: NO filtra por `tenant_id`. El aislamiento lo da el schema de
PostgreSQL (django-tenants) -- ejecutar dentro de `schema_context(tenant)`
hace imposible ver la tabla `ai_knowledge_chunk` de otro tenant.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db.models import Q
from pgvector.django import CosineDistance

from apps.services.ai.providers import AIEmbeddingProvider, get_embedding_provider
from apps.tenant.ai_knowledge.models import AIKnowledgeChunk

logger = logging.getLogger(__name__)

DEFAULT_K = 5
MAX_K = 50


@dataclass(frozen=True)
class RetrievalHit:
    content: str
    source_type: str
    source_id: str
    document_uuid: str
    chunk_index: int
    distance: float          # 0 = identico, 2 = opuesto (distancia coseno)
    metadata: dict

    @property
    def score(self) -> float:
        """Similitud coseno aproximada (1 - distancia), acotada a [0, 1]."""
        return max(0.0, min(1.0, 1.0 - self.distance))


class RetrievalService:
    """Recupera chunks relevantes a una consulta, dentro del tenant activo."""

    def __init__(self, provider: AIEmbeddingProvider | None = None):
        self._provider = provider or get_embedding_provider()

    def search(
        self,
        *,
        empresa,
        query: str,
        k: int = DEFAULT_K,
        source_types: list[str] | None = None,
        sede_ids=None,
        area_ids=None,
        max_distance: float | None = None,
    ) -> list[RetrievalHit]:
        if not query or not query.strip():
            return []
        k = max(1, min(int(k), MAX_K))

        qvec = self._provider.embed_query(query)

        qs = (
            AIKnowledgeChunk.objects.filter(empresa=empresa, embedding__isnull=False)
            .select_related("document")
            .only(
                "content",
                "chunk_index",
                "document__source_type",
                "document__source_id",
                "document__uuid",
                "document__metadata",
            )
        )
        if source_types:
            qs = qs.filter(document__source_type__in=source_types)

        # Filtros organizacionales NULL-safe: un documento cuyo metadata declara
        # sede_id/area_id solo es visible si cae dentro del alcance; los que no
        # declaran ese eje son visibles siempre (mismo criterio que
        # filter_by_scope_null_safe en el resto del ERP). Ningun origen del POC
        # declara sede/area todavia (Cliente/Producto no tienen esos campos).
        qs = self._apply_scope(qs, "sede_id", sede_ids)
        qs = self._apply_scope(qs, "area_id", area_ids)

        qs = qs.annotate(distance=CosineDistance("embedding", qvec)).order_by("distance")

        hits: list[RetrievalHit] = []
        for chunk in qs[: k if max_distance is None else MAX_K]:
            if max_distance is not None and chunk.distance > max_distance:
                break
            hits.append(
                RetrievalHit(
                    content=chunk.content,
                    source_type=chunk.document.source_type,
                    source_id=chunk.document.source_id,
                    document_uuid=str(chunk.document.uuid),
                    chunk_index=chunk.chunk_index,
                    distance=float(chunk.distance),
                    metadata=chunk.document.metadata or {},
                )
            )
            if len(hits) >= k:
                break

        logger.info(
            "[RetrievalService] query_len=%d k=%d source_types=%s hits=%d",
            len(query),
            k,
            source_types or "*",
            len(hits),
        )
        return hits

    @staticmethod
    def _apply_scope(qs, meta_key: str, allowed_ids):
        if allowed_ids is None:
            return qs
        allowed = list(allowed_ids)
        return qs.filter(
            ~Q(document__metadata__has_key=meta_key)
            | Q(**{f"document__metadata__{meta_key}__in": allowed})
        )
