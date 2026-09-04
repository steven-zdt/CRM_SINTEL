"""Pipeline de indexacion: registros de dominio -> Vector Store (AI-VECTOR-08).

Itera los origenes de `sources.INDEXABLE_SOURCES` (allowlist = frontera de
seguridad) y para cada registro real del tenant actual:

    registro -> texto del campo allowlisted -> EmbeddingService.index_text()
             (chunk -> embedding -> persistencia, idempotente por source_version)

`source_version` = hash SHA-256 del texto -> si el texto no cambio, el
`EmbeddingService` salta el registro sin llamar al proveedor.

Lectura de los modelos de dominio: via `django.apps.get_model(model_label)`
+ `.filter(empresa_id=...).only(...)` -- mismo criterio que `ai_project_map`
usa `apps.get_models()` (no se importa el modulo del dominio). Es una lectura
empresa-scoped y la allowlist (`_assert_allowlist_safe`) garantiza que el
campo nunca es FORBIDDEN/MASKED.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field

from django.apps import apps as django_apps

from apps.tenant.ai_knowledge.models import AIKnowledgeDocument
from apps.tenant.ai_knowledge.services.embedding_service import EmbeddingService
from apps.tenant.ai_knowledge.services.sources import INDEXABLE_SOURCES, get_source

logger = logging.getLogger(__name__)


@dataclass
class IndexStats:
    source_type: str
    scanned: int = 0
    indexed: int = 0      # (re)embebidos
    skipped: int = 0      # idempotencia: source_version sin cambios
    emptied: int = 0      # texto en blanco -> des-indexado / no indexado
    pruned: int = 0       # el registro de origen ya no existe

    def as_dict(self) -> dict:
        return {
            "source_type": self.source_type,
            "scanned": self.scanned,
            "indexed": self.indexed,
            "skipped": self.skipped,
            "emptied": self.emptied,
            "pruned": self.pruned,
        }


@dataclass
class ReindexResult:
    schema: str
    stats: list[IndexStats] = field(default_factory=list)

    def totals(self) -> dict:
        return {
            "scanned": sum(s.scanned for s in self.stats),
            "indexed": sum(s.indexed for s in self.stats),
            "skipped": sum(s.skipped for s in self.stats),
            "emptied": sum(s.emptied for s in self.stats),
            "pruned": sum(s.pruned for s in self.stats),
        }


class IndexingService:
    """Orquesta la (re)indexacion de un tenant a partir de la allowlist."""

    def __init__(self, embedding_service: EmbeddingService | None = None):
        self._emb = embedding_service or EmbeddingService()

    def reindex_source_type(self, *, empresa, source_type: str, prune: bool = True) -> IndexStats:
        src = get_source(source_type)
        if src is None:
            raise ValueError(
                f"source_type '{source_type}' no esta en INDEXABLE_SOURCES (allowlist)."
            )

        model = django_apps.get_model(src.model_label)
        only_fields = ["id", "uuid", src.text_field, "updated_at", *src.metadata_fields]
        qs = model.objects.filter(empresa_id=empresa.id).only(*only_fields)

        stats = IndexStats(source_type=source_type)
        seen: set[str] = set()

        for obj in qs.iterator():
            stats.scanned += 1
            source_id = str(obj.uuid)
            seen.add(source_id)
            text = (getattr(obj, src.text_field) or "").strip()

            if not text:
                # El registro existe pero su texto quedo vacio -> quitarlo del store.
                stats.emptied += 1
                self._emb.deindex(empresa=empresa, source_type=source_type, source_id=source_id)
                continue

            version = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
            metadata = {
                mf: getattr(obj, mf)
                for mf in src.metadata_fields
                if getattr(obj, mf, None) is not None
            }
            res = self._emb.index_text(
                empresa=empresa,
                source_type=source_type,
                source_id=source_id,
                text=text,
                source_version=version,
                metadata=metadata,
            )
            if res.skipped:
                stats.skipped += 1
            else:
                stats.indexed += 1

        if prune:
            stale = AIKnowledgeDocument.objects.filter(
                empresa=empresa, source_type=source_type
            ).exclude(source_id__in=seen)
            stats.pruned = stale.count()
            if stats.pruned:
                stale.delete()

        logger.info("[IndexingService] %s -> %s", source_type, stats.as_dict())
        return stats

    def reindex_all(self, *, empresa, source_types: list[str] | None = None) -> ReindexResult:
        types = source_types or [s.source_type for s in INDEXABLE_SOURCES]
        result = ReindexResult(schema="")
        for st in types:
            result.stats.append(self.reindex_source_type(empresa=empresa, source_type=st))
        return result
