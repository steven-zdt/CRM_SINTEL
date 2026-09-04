"""Fixtures para los tests del Vector Store (AI-VECTOR-03).

Provisiona 2 tenants de prueba con las tablas minimas (`empresa`,
`tenant_ai_knowledge`) para poder verificar CRUD y aislamiento cross-tenant.
La extension `vector` la instala la migracion compartida
`db_extensions.0001` al construir la BD de test.
"""

import pytest
from django.core.management import call_command
from django.db import connection
from django_tenants.utils import schema_context

from apps.public.tenants.models import Client, Domain
from apps.tenant.empresa.models import Empresa


def _ensure_tenant(schema: str, nombre: str):
    client = Client.objects.filter(schema_name=schema).first()
    if not client:
        with schema_context("public"):
            client = Client(schema_name=schema, nombre=nombre)
            client.auto_create_schema = False
            client.save(force_insert=True)
    Domain.objects.get_or_create(
        tenant=client,
        domain=f"{schema}.sintel.net.co",
        defaults={"is_primary": True},
    )
    with connection.cursor() as cur:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    with schema_context(schema):
        tables = set(connection.introspection.table_names())
    if "empresa_empresa" not in tables:
        call_command("migrate_schemas", "--tenant", "-s", schema, "empresa", "--noinput", verbosity=0)
    if "tenant_ai_knowledge_aiknowledgedocument" not in tables:
        call_command(
            "migrate_schemas", "--tenant", "-s", schema, "tenant_ai_knowledge", "--noinput", verbosity=0
        )
    # AI-VECTOR-08: dominios de origen para los tests del pipeline de indexacion.
    if "tenant_clientes_cliente" not in tables:
        call_command("migrate_schemas", "--tenant", "-s", schema, "tenant_clientes", "--noinput", verbosity=0)
    if "tenant_inventario_producto" not in tables:
        call_command("migrate_schemas", "--tenant", "-s", schema, "tenant_inventario", "--noinput", verbosity=0)

    with schema_context(schema):
        empresa = Empresa.objects.only("id").first()
        if not empresa:
            empresa = Empresa.objects.create(
                razon_social="EMPRESA TEST S.A.S.",
                nit="901234567",
                direccion="Direccion de prueba",
                telefono="3000000000",
            )
    return client


@pytest.fixture
def tenant_a(db):
    return _ensure_tenant("aik_test_a", "AI Knowledge Test A")


@pytest.fixture
def tenant_b(db):
    return _ensure_tenant("aik_test_b", "AI Knowledge Test B")


class StubEmbeddingProvider:
    """Proveedor de embeddings determinista sin descargar modelos.

    Vector 768d derivado de un hash del texto -> textos identicos dan el
    mismo vector, textos distintos vectores distintos. Suficiente para
    tests de aislamiento/alcance (no de calidad de ranking).
    """

    name = "stub"
    model = "stub-model"
    dimension = 768

    def _vec(self, text: str):
        import hashlib

        h = hashlib.sha256(text.encode("utf-8")).digest()
        base = [b / 255.0 for b in h]  # 32 valores en [0,1]
        v = (base * 24)[: self.dimension]
        return v

    def embed_documents(self, texts):
        from apps.services.ai.providers.embedding_base import EmbeddingResult

        return EmbeddingResult(
            vectors=[self._vec(t) for t in texts],
            model=self.model,
            provider=self.name,
            dimension=self.dimension,
        )

    def embed_query(self, text):
        return self._vec(text)


@pytest.fixture
def stub_provider():
    return StubEmbeddingProvider()
