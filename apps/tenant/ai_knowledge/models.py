"""Vector Store tenant-scoped del AI Engine (AI-VECTOR-03).

Trazabilidad completa: `embedding -> chunk -> document -> registro de origen`.
Sin FK a los modelos de dominio (Cliente, Producto, ...): el vinculo es
`source_type` + `source_id` (string), para no acoplar esta app a cada dominio
ni forzar `on_delete` cascades cruzados. `metadata` (JSON) guarda cualquier
contexto adicional (sede, area, etc.) sin migraciones nuevas.

Diseno: `AI_VECTOR_POC_AUDIT.md` FASE 7. Reglas de tenant: todos los modelos
heredan `SintelTenantBaseModel` (empresa FK obligatoria, aislamiento por
schema real de PostgreSQL).
"""

import uuid

from django.db import models
from pgvector.django import VectorField

from apps.tenant.core.models import SintelTenantBaseModel


class AIKnowledgeDocument(SintelTenantBaseModel):
    """Una unidad de conocimiento indexable, ligada a un registro de origen.

    Un `AIKnowledgeDocument` por (empresa, source_type, source_id). El
    contenido real troceado vive en los `AIKnowledgeChunk` relacionados.
    """

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)

    source_type = models.CharField(
        max_length=50,
        help_text="Origen logico del texto, ej. 'cliente_observaciones', 'producto_descripcion'.",
    )
    source_id = models.CharField(
        max_length=64,
        help_text="PK/UUID del registro de origen (trazabilidad, no es una FK).",
    )
    source_version = models.CharField(
        max_length=64,
        blank=True,
        help_text="Hash o updated_at del origen. Clave de idempotencia: si no cambia, "
        "no se vuelve a chunkear/embeber (AI-VECTOR-08).",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Contexto adicional no sensible (sede, area, tipo de documento, ...).",
    )

    class Meta:
        verbose_name = "AI Knowledge Document"
        verbose_name_plural = "AI Knowledge Documents"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "source_type", "source_id"],
                name="uniq_aikdoc_empresa_source",
            )
        ]
        # Django NO fusiona los indexes de la Meta abstracta cuando la hija
        # declara los suyos (mismo comportamiento verificado en SedeAwareModel).
        # Se repiten explicitamente los de SintelTenantBaseModel (CLAUDE.md).
        indexes = [
            models.Index(fields=["empresa"]),
            models.Index(fields=["empresa", "-created_at"]),
            models.Index(fields=["empresa", "source_type", "source_id"]),
            models.Index(fields=["empresa", "source_type"]),
        ]

    def __str__(self):
        return f"{self.source_type}:{self.source_id}"


class AIKnowledgeChunk(SintelTenantBaseModel):
    """Un fragmento de texto de un `AIKnowledgeDocument` y su embedding.

    El chunk se crea primero solo con `content`; el `embedding` se genera
    despues, de forma asincrona (AI-VECTOR-05/08) -- por eso es nullable.
    """

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)

    document = models.ForeignKey(
        AIKnowledgeDocument,
        on_delete=models.CASCADE,
        related_name="chunks",
        help_text="Documento de conocimiento al que pertenece este chunk.",
    )
    chunk_index = models.PositiveIntegerField(
        help_text="Posicion del chunk dentro del documento (0-based).",
    )
    content = models.TextField(
        help_text="Texto del fragmento. NUNCA debe contener campos FORBIDDEN/MASKED "
        "(la exclusion se aplica en el ChunkingService, AI-VECTOR-06).",
    )

    # --- Embedding (se rellena de forma asincrona) ---
    # dimensions=None: `vector` sin dimension fija. El proveedor -- y por tanto la
    # dimension -- se decide en AI-VECTOR-04; entonces se fijara con un AlterField
    # y se podra crear un indice ANN (HNSW) si el benchmark lo justifica (plan S13).
    embedding = VectorField(
        dimensions=None,
        null=True,
        blank=True,
        help_text="Vector de embedding del `content`. NULL hasta que se genere.",
    )
    embedding_model = models.CharField(
        max_length=100,
        blank=True,
        help_text="Identificador del modelo que genero el embedding (ej. 'voyage-3').",
    )
    embedding_version = models.PositiveIntegerField(
        default=0,
        help_text="0 = sin embeber. Se incrementa al reindexar con otro modelo/version.",
    )
    embedding_dimension = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Dimension real del vector guardado (redundante con el modelo, "
        "explicito para validacion y reindexado).",
    )
    embedded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Momento en que se genero el embedding actual.",
    )

    class Meta:
        verbose_name = "AI Knowledge Chunk"
        verbose_name_plural = "AI Knowledge Chunks"
        ordering = ["document_id", "chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="uniq_aikchunk_document_index",
            )
        ]
        indexes = [
            models.Index(fields=["empresa"]),
            models.Index(fields=["empresa", "-created_at"]),
            models.Index(fields=["empresa", "document"]),
            models.Index(fields=["empresa", "embedding_version"]),
        ]

    def __str__(self):
        return f"{self.document_id}#{self.chunk_index}"
