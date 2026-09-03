"""AI-VECTOR-03: modelos + CRUD service del Vector Store, y aislamiento tenant."""

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.utils import IntegrityError
from django_tenants.utils import schema_context

from apps.tenant.ai_knowledge.models import AIKnowledgeChunk, AIKnowledgeDocument
from apps.tenant.ai_knowledge.services import AIKnowledgeCRUDService
from apps.tenant.empresa.models import Empresa

pytestmark = pytest.mark.django_db


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

        vec = [0.1, 0.2, 0.3, 0.4]
        AIKnowledgeCRUDService.set_chunk_embedding(
            chunk=chunk, embedding=vec, embedding_model="test-model", embedding_version=1
        )
        chunk.refresh_from_db()
        assert chunk.embedding_dimension == 4
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
            chunk=chunks[0], embedding=[1.0, 0.0, 0.0], embedding_model="m", embedding_version=1
        )
        AIKnowledgeCRUDService.set_chunk_embedding(
            chunk=chunks[1], embedding=[0.0, 1.0, 0.0], embedding_model="m", embedding_version=1
        )
        nearest = (
            AIKnowledgeChunk.objects.filter(empresa=empresa, embedding__isnull=False)
            .order_by(CosineDistance("embedding", [0.9, 0.1, 0.0]))
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
