"""AI-VECTOR-04: contrato AIEmbeddingProvider + FastEmbedProvider."""

import logging

import pytest

from apps.services.ai.providers import (
    EmbeddingProviderError,
    EmbeddingResult,
    FastEmbedProvider,
    get_embedding_provider,
)
from apps.services.ai.providers import fastembed_provider as fep


class _FakeModel:
    """Sustituto del modelo ONNX: devuelve vectores deterministas de dim fija."""

    def __init__(self, dim: int = 768):
        self.dim = dim

    def embed(self, texts):
        import numpy as np

        for i, _ in enumerate(texts):
            yield np.full(self.dim, float(i + 1) / 10.0)


@pytest.fixture
def fake_fastembed(monkeypatch):
    fep._MODEL_CACHE.clear()
    fep._MODEL_CACHE["fake"] = _FakeModel(768)
    provider = FastEmbedProvider(model="fake", dimension=768, timeout_s=5)
    yield provider
    fep._MODEL_CACHE.clear()


def test_embedding_result_valida_dimension():
    with pytest.raises(ValueError):
        EmbeddingResult(vectors=[[0.1, 0.2]], model="m", provider="p", dimension=3)


def test_embed_documents_shape_y_metadata(fake_fastembed):
    res = fake_fastembed.embed_documents(["hola", "mundo", "erp"])
    assert isinstance(res, EmbeddingResult)
    assert len(res.vectors) == 3
    assert all(len(v) == 768 for v in res.vectors)
    assert res.model == "fake"
    assert res.provider == "fastembed"
    assert res.dimension == 768
    assert "elapsed_ms" in res.raw


def test_embed_documents_lista_vacia(fake_fastembed):
    res = fake_fastembed.embed_documents([])
    assert res.vectors == []


def test_embed_documents_texto_vacio_es_error_no_transitorio(fake_fastembed):
    with pytest.raises(EmbeddingProviderError) as exc:
        fake_fastembed.embed_documents(["ok", ""])
    assert exc.value.transient is False


def test_embed_query_devuelve_un_vector(fake_fastembed):
    v = fake_fastembed.embed_query("cual es la politica de descuentos")
    assert len(v) == 768


def test_logging_no_incluye_el_texto(fake_fastembed, caplog):
    with caplog.at_level(logging.INFO, logger="apps.services.ai.providers.fastembed_provider"):
        fake_fastembed.embed_documents(["texto secreto que no debe loguearse"])
    joined = " ".join(r.message for r in caplog.records)
    assert "secreto" not in joined
    assert "n=1" in joined and "dim=768" in joined


def test_timeout_marca_error_transitorio(monkeypatch):
    import time as _time

    class _SlowModel:
        def embed(self, texts):
            _time.sleep(2)
            return []

    fep._MODEL_CACHE.clear()
    fep._MODEL_CACHE["slow"] = _SlowModel()
    provider = FastEmbedProvider(model="slow", dimension=768, timeout_s=0.2)
    with pytest.raises(EmbeddingProviderError) as exc:
        provider.embed_documents(["x"])
    assert exc.value.transient is True
    fep._MODEL_CACHE.clear()


def test_factory_default_es_fastembed():
    provider = get_embedding_provider()
    assert isinstance(provider, FastEmbedProvider)
    assert provider.name == "fastembed"


def test_factory_proveedor_desconocido():
    with pytest.raises(ValueError):
        get_embedding_provider("no-existe")


@pytest.mark.slow
def test_modelo_real_jina_es_768d_y_bilingue():
    """Descarga jina-embeddings-v2-base-es (~0.64 GB) y verifica calidad basica."""
    import numpy as np

    fep._MODEL_CACHE.clear()
    provider = FastEmbedProvider()
    assert provider.model == "jinaai/jina-embeddings-v2-base-es"

    res = provider.embed_documents(
        [
            "tornillo de acero inoxidable",
            "stainless steel screw",
            "cliente mayorista con credito a 30 dias",
        ]
    )
    assert res.dimension == 768
    assert all(len(v) == 768 for v in res.vectors)

    def cos(a, b):
        a, b = np.array(a), np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    # ES <-> EN del mismo concepto: alta similitud (cross-lingual).
    assert cos(res.vectors[0], res.vectors[1]) > 0.5
    # Conceptos no relacionados: baja similitud.
    assert cos(res.vectors[0], res.vectors[2]) < 0.3
    fep._MODEL_CACHE.clear()
