"""Contrato de proveedor de embeddings (AI-VECTOR-04).

Deliberadamente SEPARADO de `AIProvider` (`base.py`): generar texto y generar
embeddings son operaciones distintas, con SDKs, modelos y economia distintos
(Anthropic ni siquiera ofrece embeddings nativos). Compartir una sola
interfaz acoplaria ambos sin ganancia real. El dominio
(`ai_knowledge.services`, `RetrievalTool`) nunca importa un SDK de embeddings
directamente -- solo este contrato.

Regla de aislamiento (mandato AI-VECTOR): un `AIEmbeddingProvider` NUNCA debe
recibir passwords, credenciales, campos MASKED/FORBIDDEN ni datos de otro
tenant. Esa exclusion se aplica ANTES, al construir el texto del chunk
(ChunkingService, AI-VECTOR-06) -- el proveedor solo ve el `content` ya
saneado.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class EmbeddingResult:
    """Resultado normalizado, independiente del proveedor."""

    vectors: list[list[float]]
    model: str
    provider: str
    dimension: int
    input_tokens: int = 0  # 0 si el proveedor no lo reporta (ej. modelos locales)
    raw: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        for v in self.vectors:
            if len(v) != self.dimension:
                raise ValueError(
                    f"Vector de dimension {len(v)} no coincide con la declarada "
                    f"({self.dimension}) por el proveedor '{self.provider}'."
                )


class EmbeddingProviderError(RuntimeError):
    """Fallo del proveedor de embeddings. `transient=True` => reintentable."""

    def __init__(self, message: str, *, transient: bool = False):
        super().__init__(message)
        self.transient = transient


class AIEmbeddingProvider(ABC):
    """Contrato que toda implementacion de embeddings debe cumplir.

    `name`, `model` y `dimension` son atributos de instancia obligatorios:
    quien persiste el vector necesita saber con que modelo/dimension se genero
    (campos `embedding_model` / `embedding_dimension` de `AIKnowledgeChunk`).
    """

    name: str
    model: str
    dimension: int

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> EmbeddingResult:
        """Genera embeddings para textos que se van a INDEXAR (documentos)."""
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Genera el embedding de una CONSULTA del usuario.

        Metodo aparte porque algunos modelos (e5, jina-v3, voyage) usan un
        prompt/prefijo distinto para consulta vs documento. Los que no lo
        distinguen simplemente llaman a `embed_documents([text])`.
        """
        raise NotImplementedError
