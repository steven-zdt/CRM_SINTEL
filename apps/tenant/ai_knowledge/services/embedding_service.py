"""Orquestacion del indexado: texto -> chunks -> embeddings -> persistencia.

NO es una segunda capa de negocio: no lee modelos de dominio ni decide QUE
indexar (eso lo hace el pipeline de AI-VECTOR-08 usando `sources.py`).
Recibe texto ya extraido y autorizado, y lo deja embebido en el Vector Store
del tenant actual, de forma idempotente.

Idempotencia (mandato AI-VECTOR-05/08): si `source_version` no cambio y los
chunks ya estan embebidos con el mismo modelo/version, no se vuelve a llamar
al proveedor.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import transaction

from apps.services.ai.providers import AIEmbeddingProvider, get_embedding_provider
from apps.tenant.ai_knowledge.models import AIKnowledgeChunk
from apps.tenant.ai_knowledge.services.chunking_service import ChunkingService
from apps.tenant.ai_knowledge.services.crud_service import AIKnowledgeCRUDService

logger = logging.getLogger(__name__)

# Version del esquema de embeddings. Se incrementa a mano si cambia el modelo
# por defecto o la forma de chunkear -> fuerza reindexado.
CURRENT_EMBEDDING_VERSION = 1


@dataclass
class IndexResult:
    source_type: str
    source_id: str
    document_id: int
    created_document: bool
    n_chunks: int
    embedded: int
    skipped: bool  # True si se salto todo por idempotencia


class EmbeddingService:
    """Indexa texto en el Vector Store del tenant activo."""

    def __init__(self, provider: AIEmbeddingProvider | None = None):
        self._provider = provider or get_embedding_provider()

    @transaction.atomic
    def index_text(
        self,
        *,
        empresa,
        source_type: str,
        source_id: str,
        text: str,
        source_version: str = "",
        metadata: dict | None = None,
        force: bool = False,
    ) -> IndexResult:
        source_id = str(source_id)
        existing = AIKnowledgeCRUDService.get_document(
            empresa=empresa, source_type=source_type, source_id=source_id
        )

        # --- Idempotencia -------------------------------------------------
        if (
            not force
            and existing is not None
            and source_version
            and existing.source_version == source_version
        ):
            chunks = list(existing.chunks.all())
            all_current = bool(chunks) and all(
                c.embedding is not None
                and c.embedding_version == CURRENT_EMBEDDING_VERSION
                and c.embedding_model == self._provider.model
                for c in chunks
            )
            if all_current:
                logger.info(
                    "[EmbeddingService] skip source=%s:%s (source_version sin cambios)",
                    source_type,
                    source_id,
                )
                return IndexResult(
                    source_type=source_type,
                    source_id=source_id,
                    document_id=existing.id,
                    created_document=False,
                    n_chunks=len(chunks),
                    embedded=0,
                    skipped=True,
                )

        # --- (Re)indexado ----------------------------------------------------
        doc, created = AIKnowledgeCRUDService.upsert_document(
            empresa=empresa,
            source_type=source_type,
            source_id=source_id,
            source_version=source_version,
            metadata=metadata or {},
        )
        contents = ChunkingService.chunk(text)
        chunks = AIKnowledgeCRUDService.replace_chunks(document=doc, contents=contents)

        embedded = 0
        if chunks:
            result = self._provider.embed_documents([c.content for c in chunks])
            for chunk, vector in zip(chunks, result.vectors):
                AIKnowledgeCRUDService.set_chunk_embedding(
                    chunk=chunk,
                    embedding=vector,
                    embedding_model=result.model,
                    embedding_version=CURRENT_EMBEDDING_VERSION,
                )
                embedded += 1

        logger.info(
            "[EmbeddingService] indexado source=%s:%s doc=%d chunks=%d embedded=%d",
            source_type,
            source_id,
            doc.id,
            len(chunks),
            embedded,
        )
        return IndexResult(
            source_type=source_type,
            source_id=source_id,
            document_id=doc.id,
            created_document=created,
            n_chunks=len(chunks),
            embedded=embedded,
            skipped=False,
        )

    @transaction.atomic
    def deindex(self, *, empresa, source_type: str, source_id: str) -> int:
        """Borra un origen del Vector Store (ej. el registro de origen se elimino)."""
        return AIKnowledgeCRUDService.delete_document(
            empresa=empresa, source_type=source_type, source_id=str(source_id)
        )

    def stale_count(self, *, empresa) -> int:
        """Chunks embebidos con un modelo/version distintos al actual (reindexado pendiente)."""
        return (
            AIKnowledgeChunk.objects.filter(empresa=empresa, embedding__isnull=False)
            .exclude(
                embedding_version=CURRENT_EMBEDDING_VERSION,
                embedding_model=self._provider.model,
            )
            .count()
        )
