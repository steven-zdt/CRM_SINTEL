import os

from .anthropic_provider import AnthropicProvider
from .base import AIProvider, AIResponse
from .embedding_base import AIEmbeddingProvider, EmbeddingProviderError, EmbeddingResult
from .fastembed_provider import FastEmbedProvider

__all__ = [
    "AIProvider",
    "AIResponse",
    "AnthropicProvider",
    "AIEmbeddingProvider",
    "EmbeddingProviderError",
    "EmbeddingResult",
    "FastEmbedProvider",
    "get_embedding_provider",
]

_EMBEDDING_PROVIDERS = {
    "fastembed": FastEmbedProvider,
}


def get_embedding_provider(name: str | None = None) -> AIEmbeddingProvider:
    """Devuelve el proveedor de embeddings configurado (default: fastembed).

    Mismo patron directo que `AnthropicProvider()` en el orquestador -- sin
    registro dinamico ni plugins, solo un dict explicito.
    """
    key = (name or os.environ.get("AI_EMBEDDING_PROVIDER", "fastembed")).lower()
    try:
        return _EMBEDDING_PROVIDERS[key]()
    except KeyError as exc:
        raise ValueError(
            f"Proveedor de embeddings desconocido: '{key}'. "
            f"Opciones: {sorted(_EMBEDDING_PROVIDERS)}"
        ) from exc
