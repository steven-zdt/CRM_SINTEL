"""Implementacion local de `AIEmbeddingProvider` con fastembed (AI-VECTOR-04).

fastembed = runtime ONNX (sin torch). El modelo por defecto
`jinaai/jina-embeddings-v2-base-es` es bilingue ES/EN, 768 dimensiones.

Ventajas para el POC (decision del usuario, ver AI_VECTOR_POC_EXECUTION.md):
- Sin API key, sin coste por token.
- CERO egress: el texto nunca sale del contenedor -> la regla de aislamiento
  del mandato se cumple de forma estructural, no por politica.

Limitaciones honestas frente a un proveedor hosted:
- "timeout" solo aplica a la inferencia local (guard de wall-clock), no hay
  latencia de red que acotar.
- "retry" solo tiene sentido para el fallo de carga/descarga del modelo
  (disco/red al bajar los pesos la primera vez), no para un 5xx remoto.
"""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from .embedding_base import AIEmbeddingProvider, EmbeddingProviderError, EmbeddingResult

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "jinaai/jina-embeddings-v2-base-es"
DEFAULT_DIMENSION = 768
DEFAULT_TIMEOUT_S = 60.0

# Cache de modelos por nombre: cargar el runtime ONNX cuesta ~1-2 s y la
# primera vez descarga ~0.64 GB. Se comparte entre instancias del provider.
_MODEL_CACHE: dict = {}


class FastEmbedProvider(AIEmbeddingProvider):
    name = "fastembed"

    def __init__(
        self,
        model: str | None = None,
        *,
        dimension: int | None = None,
        timeout_s: float | None = None,
    ):
        self.model = model or os.environ.get("AI_EMBEDDING_MODEL", DEFAULT_MODEL)
        self.dimension = int(
            dimension
            or os.environ.get("AI_EMBEDDING_DIMENSION", DEFAULT_DIMENSION)
        )
        self.timeout_s = float(
            timeout_s or os.environ.get("AI_EMBEDDING_TIMEOUT_S", DEFAULT_TIMEOUT_S)
        )

    # ------------------------------------------------------------------ #
    def _get_model(self):
        cached = _MODEL_CACHE.get(self.model)
        if cached is not None:
            return cached
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:  # pragma: no cover - dependencia declarada
            raise EmbeddingProviderError(
                "Paquete 'fastembed' no instalado.", transient=False
            ) from exc

        last_exc: Exception | None = None
        for intento in (1, 2):  # un reintento: la 1a carga puede fallar bajando pesos
            try:
                model = TextEmbedding(model_name=self.model)
                _MODEL_CACHE[self.model] = model
                return model
            except Exception as exc:  # noqa: BLE001 - clasificamos abajo
                last_exc = exc
                logger.warning(
                    "[FastEmbedProvider] fallo al cargar modelo %s (intento %d): %s",
                    self.model,
                    intento,
                    exc.__class__.__name__,
                )
                time.sleep(1.0)
        raise EmbeddingProviderError(
            f"No se pudo cargar el modelo de embeddings '{self.model}'.", transient=True
        ) from last_exc

    def _embed_raw(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()

        def _run() -> list[list[float]]:
            return [vec.tolist() for vec in model.embed(list(texts))]

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_run)
            try:
                return future.result(timeout=self.timeout_s)
            except FuturesTimeout as exc:
                raise EmbeddingProviderError(
                    f"Timeout ({self.timeout_s}s) generando {len(texts)} embeddings "
                    f"con '{self.model}'.",
                    transient=True,
                ) from exc

    # ------------------------------------------------------------------ #
    def embed_documents(self, texts: list[str]) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(
                vectors=[], model=self.model, provider=self.name, dimension=self.dimension
            )
        if any((t is None or t == "") for t in texts):
            raise EmbeddingProviderError(
                "No se puede generar embedding de un texto vacio.", transient=False
            )

        t0 = time.perf_counter()
        vectors = self._embed_raw(texts)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        # Logging seguro: SOLO metadatos, nunca el texto ni el vector.
        logger.info(
            "[FastEmbedProvider] embed_documents n=%d model=%s dim=%d elapsed_ms=%.0f",
            len(texts),
            self.model,
            self.dimension,
            elapsed_ms,
        )
        return EmbeddingResult(
            vectors=vectors,
            model=self.model,
            provider=self.name,
            dimension=self.dimension,
            raw={"elapsed_ms": round(elapsed_ms, 1)},
        )

    def embed_query(self, text: str) -> list[float]:
        # jina-embeddings-v2-base-es no usa prefijo distinto para consulta.
        return self.embed_documents([text]).vectors[0]
