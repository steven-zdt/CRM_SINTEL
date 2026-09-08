"""AI-VECTOR-03: modelos + CRUD service del Vector Store, y aislamiento tenant."""

import pytest
from django.db.utils import IntegrityError
from django_tenants.utils import schema_context

from apps.tenant.ai_knowledge.models import AIKnowledgeChunk, AIKnowledgeDocument, AIKnowledgeSettings
from apps.tenant.ai_knowledge.services import AIKnowledgeCRUDService
from apps.tenant.empresa.models import Empresa

pytestmark = pytest.mark.django_db

# AI-VECTOR-04: la columna `embedding` es `vector(768)`.
DIM = 768


def _vec(*axis_values: float) -> list[float]:
    """Vector de 768 dims: los primeros valores son `axis_values`, el resto 0."""
    v = list(axis_values) + [0.0] * (DIM - len(axis_values))
    return v[:DIM]


def _empresa(schema: str) -> Empresa:
    with schema_context(schema):
        return Empresa.objects.only("id").first()


def test_upsert_document_crea_y_luego_actualiza(tenant_a):
    with schema_context(tenant_a.schema_name):
        empresa = _empresa(tenant_a.schema_name)
        doc, created = AIKnowledgeCRUDService.upsert_document(
            empresa=empresa,
            source_type="cliente_observaciones",
            source_id="42",
            source_version="v1",
            metadata={"sede": "principal"},
        )
        assert created is True
        assert doc.source_version == "v1"

        doc2, created2 = AIKnowledgeCRUDService.upsert_document(
            empresa=empresa,
            source_type="cliente_observaciones",
            source_id="42",
            source_version="v2",
        )
        assert created2 is False
        assert doc2.id == doc.id
        assert doc2.source_version == "v2"
        assert AIKnowledgeDocument.objects.filter(empresa=empresa).count() == 1


def test_replace_chunks_reemplaza_por_completo(tenant_a):
    with schema_context(tenant_a.schema_name):
        empresa = _empresa(tenant_a.schema_name)
        doc, _ = AIKnowledgeCRUDService.upsert_document(
            empresa=empresa, source_type="producto_descripcion", source_id="7"
        )
        AIKnowledgeCRUDService.replace_chunks(document=doc, contents=["a", "b", "c"])
        assert list(doc.chunks.values_list("chunk_index", flat=True)) == [0, 1, 2]

        AIKnowledgeCRUDService.replace_chunks(document=doc, contents=["x"])
        assert doc.chunks.count() == 1
        assert doc.chunks.first().content == "x"


def test_set_chunk_embedding_guarda_vector_y_dimension(tenant_a):
    with schema_context(tenant_a.schema_name):
        empresa = _empresa(tenant_a.schema_name)
        doc, _ = AIKnowledgeCRUDService.upsert_document(
            empresa=empresa, source_type="producto_descripcion", source_id="8"
        )
        (chunk,) = AIKnowledgeCRUDService.replace_chunks(document=doc, contents=["hola mundo"])
        assert chunk.embedding is None
        assert chunk.embedding_version == 0

        vec = _vec(0.1, 0.2, 0.3, 0.4)
        AIKnowledgeCRUDService.set_chunk_embedding(
            chunk=chunk, embedding=vec, embedding_model="test-model", embedding_version=1
        )
        chunk.refresh_from_db()
        assert chunk.embedding_dimension == DIM
        assert chunk.embedding_model == "test-model"
        assert chunk.embedding_version == 1
        assert chunk.embedded_at is not None
        assert list(chunk.embedding) == pytest.approx(vec, abs=1e-6)


def test_vector_distance_query_funciona(tenant_a):
    from pgvector.django import CosineDistance

    with schema_context(tenant_a.schema_name):
        empresa = _empresa(tenant_a.schema_name)
        doc, _ = AIKnowledgeCRUDService.upsert_document(
            empresa=empresa, source_type="doc", source_id="9"
        )
        chunks = AIKnowledgeCRUDService.replace_chunks(document=doc, contents=["c0", "c1"])
        AIKnowledgeCRUDService.set_chunk_embedding(
            chunk=chunks[0], embedding=_vec(1.0, 0.0, 0.0), embedding_model="m", embedding_version=1
        )
        AIKnowledgeCRUDService.set_chunk_embedding(
            chunk=chunks[1], embedding=_vec(0.0, 1.0, 0.0), embedding_model="m", embedding_version=1
        )
        nearest = (
            AIKnowledgeChunk.objects.filter(empresa=empresa, embedding__isnull=False)
            .order_by(CosineDistance("embedding", _vec(0.9, 0.1, 0.0)))
            .first()
        )
        assert nearest.content == "c0"


def test_unique_constraint_documento_por_origen(tenant_a):
    with schema_context(tenant_a.schema_name):
        empresa = _empresa(tenant_a.schema_name)
        AIKnowledgeDocument.objects.create(
            empresa=empresa, source_type="x", source_id="1"
        )
        with pytest.raises(IntegrityError):
            AIKnowledgeDocument.objects.create(
                empresa=empresa, source_type="x", source_id="1"
            )


def test_empresa_obligatoria(tenant_a):
    with schema_context(tenant_a.schema_name):
        doc = AIKnowledgeDocument(source_type="x", source_id="2")
        with pytest.raises(ValueError):
            doc.save()


# --------------- AI-VECTOR-11: AIKnowledgeSettings (flag por tenant) ------- #

def test_get_or_create_settings_crea_apagado_por_defecto(tenant_a):
    with schema_context(tenant_a.schema_name):
        empresa = _empresa(tenant_a.schema_name)
        settings_row = AIKnowledgeCRUDService.get_or_create_settings(empresa=empresa)
        assert settings_row.retrieval_enabled is False
        assert AIKnowledgeSettings.objects.filter(empresa=empresa).count() == 1


def test_set_retrieval_enabled_prende_y_apaga(tenant_a):
    with schema_context(tenant_a.schema_name):
        empresa = _empresa(tenant_a.schema_name)
        AIKnowledgeCRUDService.set_retrieval_enabled(empresa=empresa, enabled=True)
        assert AIKnowledgeSettings.objects.get(empresa=empresa).retrieval_enabled is True

        AIKnowledgeCRUDService.set_retrieval_enabled(empresa=empresa, enabled=False)
        assert AIKnowledgeSettings.objects.get(empresa=empresa).retrieval_enabled is False
        # sigue siendo 1 sola fila (get_or_create, no duplica)
        assert AIKnowledgeSettings.objects.filter(empresa=empresa).count() == 1


def test_settings_unique_constraint_por_empresa(tenant_a):
    with schema_context(tenant_a.schema_name):
        empresa = _empresa(tenant_a.schema_name)
        AIKnowledgeSettings.objects.create(empresa=empresa)
        with pytest.raises(IntegrityError):
            AIKnowledgeSettings.objects.create(empresa=empresa)


def test_settings_aislamiento_cross_tenant(tenant_a, tenant_b):
    with schema_context(tenant_a.schema_name):
        empresa_a = _empresa(tenant_a.schema_name)
        AIKnowledgeCRUDService.set_retrieval_enabled(empresa=empresa_a, enabled=True)

    with schema_context(tenant_b.schema_name):
        # El schema de B no ve el flag de A -- apagar A no lo apaga, encender A no lo prende.
        assert AIKnowledgeSettings.objects.count() == 0


def test_aislamiento_cross_tenant(tenant_a, tenant_b):
    with schema_context(tenant_a.schema_name):
        empresa_a = _empresa(tenant_a.schema_name)
        AIKnowledgeCRUDService.upsert_document(
            empresa=empresa_a, source_type="secreto", source_id="A", metadata={"tenant": "A"}
        )

    with schema_context(tenant_b.schema_name):
        # El schema de B no ve NADA del Vector Store de A (aislamiento real de PostgreSQL).
        assert AIKnowledgeDocument.objects.count() == 0
        assert (
            AIKnowledgeCRUDService.get_document(
                empresa=_empresa(tenant_b.schema_name), source_type="secreto", source_id="A"
            )
            is None
        )
