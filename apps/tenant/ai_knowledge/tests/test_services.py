"""AI-VECTOR-05: ChunkingService + EmbeddingService + RetrievalService."""

import pytest
from django_tenants.utils import schema_context

from apps.services.ai.providers.embedding_base import AIEmbeddingProvider, EmbeddingResult
from apps.tenant.ai_knowledge.models import AIKnowledgeChunk, AIKnowledgeDocument
from apps.tenant.ai_knowledge.services import (
    ChunkingService,
    EmbeddingService,
    RetrievalService,
    is_indexable,
)
from apps.tenant.empresa.models import Empresa

pytestmark = pytest.mark.django_db

DIM = 768
_VOCAB = [
    "tornillo", "perno", "acero", "metalico", "sujetador", "galvanizado",
    "cliente", "credito", "mayorista", "ferreteria", "descuento", "politica",
]


class FakeEmbeddingProvider(AIEmbeddingProvider):
    """Embedding determinista por solapamiento de tokens (para tests de ranking)."""

    name = "fake"
    model = "fake-model"
    dimension = DIM

    def _vec(self, text: str) -> list[float]:
        tokens = text.lower().split()
        v = [0.0] * DIM
        for i, word in enumerate(_VOCAB):
            v[i] = float(sum(1 for t in tokens if word in t))
        if not any(v):
            v[DIM - 1] = 1.0  # evita vector nulo
        return v

    def embed_documents(self, texts):
        return EmbeddingResult(
            vectors=[self._vec(t) for t in texts],
            model=self.model,
            provider=self.name,
            dimension=self.dimension,
        )

    def embed_query(self, text):
        return self._vec(text)


@pytest.fixture
def fake_provider():
    return FakeEmbeddingProvider()


def _empresa(schema):
    with schema_context(schema):
        return Empresa.objects.only("id").first()


# --------------------------------------------------------------------------- #
# ChunkingService
# --------------------------------------------------------------------------- #
def test_chunk_texto_corto_un_chunk():
    assert ChunkingService.chunk("Cliente puntual en pagos.") == ["Cliente puntual en pagos."]


def test_chunk_vacio():
    assert ChunkingService.chunk("") == []
    assert ChunkingService.chunk("   \n  ") == []
    assert ChunkingService.chunk(None) == []


def test_chunk_multiparrafo():
    text = "Primer parrafo con contexto.\n\nSegundo parrafo distinto."
    assert ChunkingService.chunk(text) == [
        "Primer parrafo con contexto.",
        "Segundo parrafo distinto.",
    ]


def test_chunk_parrafo_largo_se_parte_con_overlap():
    sentence = "Esta es una oracion de relleno con suficiente longitud. "
    text = sentence * 40  # ~2200 chars, un solo parrafo
    chunks = ChunkingService.chunk(text, max_chars=300, overlap_chars=50)
    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)


def test_chunk_overlap_invalido():
    with pytest.raises(ValueError):
        ChunkingService.chunk("x", max_chars=100, overlap_chars=100)


# --------------------------------------------------------------------------- #
# sources allowlist
# --------------------------------------------------------------------------- #
def test_allowlist_solo_origenes_curados():
    assert is_indexable("cliente_observaciones") is True
    assert is_indexable("producto_descripcion") is True
    assert is_indexable("empleado_salario") is False
    assert is_indexable("cuenta_bancaria_notas") is False


# --------------------------------------------------------------------------- #
# EmbeddingService (idempotencia)
# --------------------------------------------------------------------------- #
def test_index_text_crea_doc_chunks_y_embeddings(tenant_a, fake_provider):
    svc = EmbeddingService(provider=fake_provider)
    with schema_context(tenant_a.schema_name):
        emp = _empresa(tenant_a.schema_name)
        res = svc.index_text(
            empresa=emp,
            source_type="producto_descripcion",
            source_id="10",
            text="Tornillo de acero. Perno galvanizado.",
            source_version="v1",
        )
        assert res.created_document is True
        assert res.n_chunks >= 1
        assert res.embedded == res.n_chunks
        assert res.skipped is False
        assert AIKnowledgeChunk.objects.filter(empresa=emp, embedding__isnull=False).count() == res.n_chunks


def test_index_text_idempotente_por_source_version(tenant_a, fake_provider):
    svc = EmbeddingService(provider=fake_provider)
    with schema_context(tenant_a.schema_name):
        emp = _empresa(tenant_a.schema_name)
        kw = dict(empresa=emp, source_type="producto_descripcion", source_id="11", text="Perno acero.")
        svc.index_text(**kw, source_version="v1")
        again = svc.index_text(**kw, source_version="v1")
        assert again.skipped is True
        assert again.embedded == 0

        changed = svc.index_text(**kw, source_version="v2")
        assert changed.skipped is False
        assert changed.embedded >= 1

        forced = svc.index_text(**kw, source_version="v2", force=True)
        assert forced.skipped is False


def test_deindex_borra_el_origen(tenant_a, fake_provider):
    svc = EmbeddingService(provider=fake_provider)
    with schema_context(tenant_a.schema_name):
        emp = _empresa(tenant_a.schema_name)
        svc.index_text(empresa=emp, source_type="producto_descripcion", source_id="12", text="Acero.")
        svc.deindex(empresa=emp, source_type="producto_descripcion", source_id="12")
        assert AIKnowledgeDocument.objects.filter(empresa=emp, source_id="12").count() == 0


# --------------------------------------------------------------------------- #
# RetrievalService
# --------------------------------------------------------------------------- #
def _seed(svc, emp, rows):
    for sid, text in rows:
        svc.index_text(empresa=emp, source_type="producto_descripcion", source_id=sid, text=text)


def test_search_rankea_por_similitud(tenant_a, fake_provider):
    emb = EmbeddingService(provider=fake_provider)
    ret = RetrievalService(provider=fake_provider)
    with schema_context(tenant_a.schema_name):
        emp = _empresa(tenant_a.schema_name)
        _seed(emb, emp, [
            ("A", "tornillo perno acero metalico sujetador"),
            ("B", "cliente mayorista credito descuento politica"),
        ])
        hits = ret.search(empresa=emp, query="sujetador metalico de acero", k=2)
        assert hits, "deberia haber resultados"
        assert hits[0].source_id == "A"
        assert hits[0].distance <= hits[-1].distance


def test_search_respeta_k(tenant_a, fake_provider):
    emb = EmbeddingService(provider=fake_provider)
    ret = RetrievalService(provider=fake_provider)
    with schema_context(tenant_a.schema_name):
        emp = _empresa(tenant_a.schema_name)
        _seed(emb, emp, [(str(i), f"acero tornillo numero {i}") for i in range(6)])
        assert len(ret.search(empresa=emp, query="acero", k=3)) == 3


def test_search_filtra_por_source_type(tenant_a, fake_provider):
    emb = EmbeddingService(provider=fake_provider)
    ret = RetrievalService(provider=fake_provider)
    with schema_context(tenant_a.schema_name):
        emp = _empresa(tenant_a.schema_name)
        emb.index_text(empresa=emp, source_type="producto_descripcion", source_id="P1", text="acero tornillo")
        emb.index_text(empresa=emp, source_type="cliente_observaciones", source_id="C1", text="acero cliente")
        hits = ret.search(empresa=emp, query="acero", k=10, source_types=["cliente_observaciones"])
        assert {h.source_type for h in hits} == {"cliente_observaciones"}


def test_search_query_vacia(tenant_a, fake_provider):
    ret = RetrievalService(provider=fake_provider)
    with schema_context(tenant_a.schema_name):
        emp = _empresa(tenant_a.schema_name)
        assert ret.search(empresa=emp, query="   ") == []


def test_search_es_solo_lectura(tenant_a, fake_provider):
    emb = EmbeddingService(provider=fake_provider)
    ret = RetrievalService(provider=fake_provider)
    with schema_context(tenant_a.schema_name):
        emp = _empresa(tenant_a.schema_name)
        _seed(emb, emp, [("X", "acero tornillo perno")])
        before_docs = AIKnowledgeDocument.objects.count()
        before_chunks = AIKnowledgeChunk.objects.count()
        ret.search(empresa=emp, query="acero", k=5)
        assert AIKnowledgeDocument.objects.count() == before_docs
        assert AIKnowledgeChunk.objects.count() == before_chunks


def test_search_no_cruza_tenants(tenant_a, tenant_b, fake_provider):
    emb = EmbeddingService(provider=fake_provider)
    ret = RetrievalService(provider=fake_provider)
    with schema_context(tenant_a.schema_name):
        emp_a = _empresa(tenant_a.schema_name)
        emb.index_text(
            empresa=emp_a, source_type="producto_descripcion", source_id="SECRET",
            text="tornillo acero confidencial de A",
        )
    with schema_context(tenant_b.schema_name):
        emp_b = _empresa(tenant_b.schema_name)
        assert ret.search(empresa=emp_b, query="tornillo acero confidencial", k=10) == []


# --------------------------------------------------------------------------- #
# Cache de query-embeddings (AI-VECTOR-11A)
# --------------------------------------------------------------------------- #
class _CountingProvider(FakeEmbeddingProvider):
    """Mismo provider fake, pero cuenta cuantas veces se invoca embed_query."""

    def __init__(self):
        self.embed_query_calls = 0

    def embed_query(self, text):
        self.embed_query_calls += 1
        return super().embed_query(text)


def test_search_cache_hit_no_reembede_texto_repetido(tenant_a):
    import uuid

    provider = _CountingProvider()
    emb = EmbeddingService(provider=provider)
    ret = RetrievalService(provider=provider)
    q = f"acero tornillo cache test {uuid.uuid4()}"
    with schema_context(tenant_a.schema_name):
        emp = _empresa(tenant_a.schema_name)
        _seed(emb, emp, [("X", "acero tornillo perno")])
        provider.embed_query_calls = 0  # descartar el embed del seed

        hits1 = ret.search(empresa=emp, query=q, k=5)
        assert provider.embed_query_calls == 1

        hits2 = ret.search(empresa=emp, query=q, k=5)
        # 2a llamada: cache hit -- no vuelve a invocar al provider.
        assert provider.embed_query_calls == 1
        assert [h.source_id for h in hits1] == [h.source_id for h in hits2]


def test_search_cache_miss_con_texto_distinto(tenant_a):
    import uuid

    provider = _CountingProvider()
    emb = EmbeddingService(provider=provider)
    ret = RetrievalService(provider=provider)
    suffix = uuid.uuid4()
    with schema_context(tenant_a.schema_name):
        emp = _empresa(tenant_a.schema_name)
        _seed(emb, emp, [("X", "acero tornillo perno")])
        provider.embed_query_calls = 0

        ret.search(empresa=emp, query=f"acero {suffix} uno", k=5)
        ret.search(empresa=emp, query=f"acero {suffix} dos", k=5)
        # textos distintos -- 2 embeds reales, ningun cache hit.
        assert provider.embed_query_calls == 2


def test_search_cache_no_cruza_tenants(tenant_a, tenant_b):
    import uuid

    provider = _CountingProvider()
    emb = EmbeddingService(provider=provider)
    ret = RetrievalService(provider=provider)
    q = f"acero tornillo cache cross-tenant {uuid.uuid4()}"

    with schema_context(tenant_a.schema_name):
        emp_a = _empresa(tenant_a.schema_name)
        _seed(emb, emp_a, [("X", "acero tornillo perno")])
        provider.embed_query_calls = 0
        ret.search(empresa=emp_a, query=q, k=5)
        assert provider.embed_query_calls == 1

    with schema_context(tenant_b.schema_name):
        emp_b = _empresa(tenant_b.schema_name)
        # mismo texto, tenant distinto -- NO debe reusar el cache de tenant_a
        # (la key incluye connection.schema_name).
        ret.search(empresa=emp_b, query=q, k=5)
        assert provider.embed_query_calls == 2


def test_search_cache_invalida_por_modelo(tenant_a):
    import uuid

    provider = _CountingProvider()
    emb = EmbeddingService(provider=provider)
    ret = RetrievalService(provider=provider)
    q = f"acero tornillo cache modelo {uuid.uuid4()}"
    with schema_context(tenant_a.schema_name):
        emp = _empresa(tenant_a.schema_name)
        _seed(emb, emp, [("X", "acero tornillo perno")])
        provider.embed_query_calls = 0

        ret.search(empresa=emp, query=q, k=5)
        assert provider.embed_query_calls == 1

        provider.model = "otro-modelo-v2"  # simula un cambio de proveedor/modelo
        ret.search(empresa=emp, query=q, k=5)
        # modelo distinto -> key distinta -> cache miss, no sirve un vector viejo.
        assert provider.embed_query_calls == 2


def test_search_cache_fail_open_si_redis_no_responde(tenant_a, monkeypatch):
    from apps.tenant.ai_knowledge.services import query_embedding_cache

    def _broken_redis():
        raise ConnectionError("redis no disponible (test)")

    monkeypatch.setattr(query_embedding_cache, "_redis", _broken_redis)

    provider = _CountingProvider()
    emb = EmbeddingService(provider=provider)
    ret = RetrievalService(provider=provider)
    with schema_context(tenant_a.schema_name):
        emp = _empresa(tenant_a.schema_name)
        _seed(emb, emp, [("X", "acero tornillo perno")])
        # sin cache disponible, search() sigue funcionando (fail-open).
        hits = ret.search(empresa=emp, query="acero", k=5)
        assert hits and hits[0].source_id == "X"
