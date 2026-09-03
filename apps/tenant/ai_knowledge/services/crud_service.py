"""Persistencia pura del Vector Store (AI-VECTOR-03).

Solo escritura/lectura de `AIKnowledgeDocument` / `AIKnowledgeChunk`, sin
reglas de negocio: el chunking, la generacion de embeddings y el retrieval
son servicios aparte (AI-VECTOR-05). Todos los metodos reciben `empresa`
explicito (SSoT de contexto) y filtran por el.
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.tenant.ai_knowledge.models import AIKnowledgeChunk, AIKnowledgeDocument

logger = logging.getLogger(__name__)


class AIKnowledgeCRUDService:
    """CRUD puro para el Vector Store tenant-scoped."""

    @staticmethod
    @transaction.atomic
    def upsert_document(
        *,
        empresa,
        source_type: str,
        source_id: str,
        source_version: str = "",
        metadata: dict | None = None,
    ) -> tuple[AIKnowledgeDocument, bool]:
        """Crea o actualiza el documento de (empresa, source_type, source_id).

        Devuelve (documento, created). No toca los chunks.
        """
        doc, created = AIKnowledgeDocument.objects.update_or_create(
            empresa=empresa,
            source_type=source_type,
            source_id=str(source_id),
            defaults={
                "source_version": source_version or "",
                "metadata": metadata or {},
            },
        )
        logger.info(
            "[AIKnowledgeCRUD] %s document id=%s source=%s:%s",
            "creado" if created else "actualizado",
            doc.id,
            source_type,
            source_id,
        )
        return doc, created

    @staticmethod
    @transaction.atomic
    def replace_chunks(*, document: AIKnowledgeDocument, contents: list[str]) -> list[AIKnowledgeChunk]:
        """Reemplaza por completo los chunks de un documento (sin embeddings).

        Idempotente a nivel de contenido: borra los chunks previos y crea los
        nuevos en orden. Los embeddings se generan despues (AI-VECTOR-05).
        """
        document.chunks.all().delete()
        chunks = [
            AIKnowledgeChunk(
                empresa=document.empresa,
                document=document,
                chunk_index=idx,
                content=text,
            )
            for idx, text in enumerate(contents)
        ]
        for chunk in chunks:
            chunk.full_clean(exclude=["embedding"])
        AIKnowledgeChunk.objects.bulk_create(chunks)
        logger.info(
            "[AIKnowledgeCRUD] %d chunks para document id=%s", len(chunks), document.id
        )
        return chunks

    @staticmethod
    @transaction.atomic
    def set_chunk_embedding(
        *,
        chunk: AIKnowledgeChunk,
        embedding: list[float],
        embedding_model: str,
        embedding_version: int,
    ) -> AIKnowledgeChunk:
        """Guarda el embedding generado para un chunk."""
        chunk.embedding = embedding
        chunk.embedding_model = embedding_model
        chunk.embedding_version = embedding_version
        chunk.embedding_dimension = len(embedding)
        chunk.embedded_at = timezone.now()
        chunk.save(
            update_fields=[
                "embedding",
                "embedding_model",
                "embedding_version",
                "embedding_dimension",
                "embedded_at",
                "updated_at",
            ]
        )
        return chunk

    @staticmethod
    def get_document(*, empresa, source_type: str, source_id: str) -> AIKnowledgeDocument | None:
        """Lee el documento de un origen, o None."""
        return (
            AIKnowledgeDocument.objects.filter(
                empresa=empresa, source_type=source_type, source_id=str(source_id)
            )
            .prefetch_related("chunks")
            .first()
        )

    @staticmethod
    @transaction.atomic
    def delete_document(*, empresa, source_type: str, source_id: str) -> int:
        """Borra el documento de un origen y sus chunks (CASCADE). Devuelve filas borradas."""
        deleted, _ = AIKnowledgeDocument.objects.filter(
            empresa=empresa, source_type=source_type, source_id=str(source_id)
        ).delete()
        logger.info(
            "[AIKnowledgeCRUD] borrado document source=%s:%s (%d filas)",
            source_type,
            source_id,
            deleted,
        )
        return deleted
