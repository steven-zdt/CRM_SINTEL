"""AI-VECTOR-08: pipeline de indexacion real (IndexingService + tarea Celery)."""

import pytest
from django_tenants.utils import schema_context

from apps.tenant.ai_knowledge.models import AIKnowledgeChunk, AIKnowledgeDocument
from apps.tenant.ai_knowledge.services import EmbeddingService, IndexingService
from apps.tenant.ai_knowledge.tasks import _clasificar_excepcion, reindex_tenant_knowledge
from apps.services.ai.providers.embedding_base import EmbeddingProviderError
from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import Producto

pytestmark = pytest.mark.django_db


def _emp(schema):
    with schema_context(schema):
        return Empresa.objects.only("id").first()


def _mk_cliente(empresa, num, obs):
    return Cliente.objects.create(
        empresa=empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
        numero_documento=num, razon_social=f"Cliente {num}",
        regimen_tributario="ORDINARIO", observaciones=obs,
    )


def _svc(stub):
    return IndexingService(embedding_service=EmbeddingService(provider=stub))


# ------------------------------------------------------------------------- #
def test_reindex_crea_documentos_desde_clientes_reales(tenant_a, stub_provider):
    with schema_context(tenant_a.schema_name):
        emp = _emp(tenant_a.schema_name)
        _mk_cliente(emp, "800000001", "Paga a 30 dias, compra material electrico al por mayor.")
        _mk_cliente(emp, "800000002", "Contratista de obra blanca, pedidos pequenos de contado.")

        stats = _svc(stub_provider).reindex_source_type(empresa=emp, source_type="cliente_observaciones")
        assert stats.scanned == 2 and stats.indexed == 2 and stats.skipped == 0
        assert AIKnowledgeDocument.objects.filter(source_type="cliente_observaciones").count() == 2
        assert AIKnowledgeChunk.objects.filter(embedding__isnull=False).count() >= 2


def test_reindex_es_idempotente(tenant_a, stub_provider):
    with schema_context(tenant_a.schema_name):
        emp = _emp(tenant_a.schema_name)
        _mk_cliente(emp, "800000010", "Observacion estable que no cambia.")
        svc = _svc(stub_provider)
        svc.reindex_source_type(empresa=emp, source_type="cliente_observaciones")
        again = svc.reindex_source_type(empresa=emp, source_type="cliente_observaciones")
        assert again.scanned == 1 and again.skipped == 1 and again.indexed == 0


def test_reindex_reembebe_si_cambia_el_texto(tenant_a, stub_provider):
    with schema_context(tenant_a.schema_name):
        emp = _emp(tenant_a.schema_name)
        c = _mk_cliente(emp, "800000011", "texto original")
        svc = _svc(stub_provider)
        svc.reindex_source_type(empresa=emp, source_type="cliente_observaciones")
        c.observaciones = "texto modificado por el usuario"
        c.save(update_fields=["observaciones", "updated_at"])
        stats = svc.reindex_source_type(empresa=emp, source_type="cliente_observaciones")
        assert stats.indexed == 1 and stats.skipped == 0


def test_texto_en_blanco_no_se_indexa(tenant_a, stub_provider):
    with schema_context(tenant_a.schema_name):
        emp = _emp(tenant_a.schema_name)
        _mk_cliente(emp, "800000012", "   ")
        _mk_cliente(emp, "800000013", "observacion con contenido")
        stats = _svc(stub_provider).reindex_source_type(empresa=emp, source_type="cliente_observaciones")
        assert stats.scanned == 2 and stats.indexed == 1 and stats.emptied == 1
        assert AIKnowledgeDocument.objects.count() == 1


def test_prune_borra_documentos_de_registros_eliminados(tenant_a, stub_provider):
    # Nota: probar `Cliente.delete()` real aqui exigiria migrar media docena de
    # apps de dominio al schema de test (el collector de Django recorre TODAS
    # las relaciones inversas: ventas, facturas, cartera...). El flujo completo
    # delete -> prune esta verificado end-to-end en `aipoc` real
    # (AI_VECTOR_POC_EXECUTION.md). Aqui se prueba la LOGICA de prune con un
    # documento huerfano (source_id que no corresponde a ningun Cliente actual).
    with schema_context(tenant_a.schema_name):
        emp = _emp(tenant_a.schema_name)
        _mk_cliente(emp, "800000021", "cliente que permanece")
        AIKnowledgeDocument.objects.create(
            empresa=emp, source_type="cliente_observaciones",
            source_id="00000000-0000-0000-0000-000000000000",  # huerfano
        )
        svc = _svc(stub_provider)
        stats = svc.reindex_source_type(
            empresa=emp, source_type="cliente_observaciones", prune=True
        )
        assert stats.pruned == 1
        assert not AIKnowledgeDocument.objects.filter(
            source_id="00000000-0000-0000-0000-000000000000"
        ).exists()
        assert AIKnowledgeDocument.objects.count() == 1


def test_reindex_all_cubre_productos(tenant_a, stub_provider):
    with schema_context(tenant_a.schema_name):
        emp = _emp(tenant_a.schema_name)
        _mk_cliente(emp, "800000030", "nota de cliente")
        Producto.objects.create(empresa=emp, codigo="P-1", nombre="Tornillo",
                                descripcion="tornillo de acero inoxidable para exteriores")
        Producto.objects.create(empresa=emp, codigo="P-2", nombre="Perno", descripcion=None)  # sin descripcion

        result = _svc(stub_provider).reindex_all(empresa=emp)
        by = {s.source_type: s for s in result.stats}
        assert by["producto_descripcion"].scanned == 2
        assert by["producto_descripcion"].indexed == 1  # el de descripcion=None no
        assert by["cliente_observaciones"].indexed == 1


def test_reindex_source_no_allowlisted():
    with pytest.raises(ValueError):
        IndexingService().reindex_source_type(empresa=None, source_type="empleado_salario")


# ------------------------------------------------------------------------- #
# Tarea Celery
# ------------------------------------------------------------------------- #
def test_task_reindex_tenant_knowledge_sync(tenant_a, stub_provider, monkeypatch):
    # La tarea instancia IndexingService() sin stub -> parchear el provider.
    monkeypatch.setattr(
        "apps.tenant.ai_knowledge.services.embedding_service.get_embedding_provider",
        lambda name=None: stub_provider,
    )
    with schema_context(tenant_a.schema_name):
        emp = _emp(tenant_a.schema_name)
        _mk_cliente(emp, "800000040", "condiciones comerciales especiales para este cliente")

    out = reindex_tenant_knowledge.apply(args=[tenant_a.schema_name]).get()
    assert out["status"] == "OK"
    assert out["totals"]["indexed"] >= 1
    assert {s["source_type"] for s in out["by_source"]} == {"cliente_observaciones", "producto_descripcion"}


def test_clasificacion_de_excepciones():
    assert _clasificar_excepcion(ConnectionError()) == "transient"
    assert _clasificar_excepcion(TimeoutError()) == "transient"
    assert _clasificar_excepcion(EmbeddingProviderError("x", transient=True)) == "transient"
    assert _clasificar_excepcion(EmbeddingProviderError("x", transient=False)) == "unknown"
    assert _clasificar_excepcion(AttributeError()) == "programming"
    # PermissionError es subclase de OSError -- debe clasificar como security igual.
    assert _clasificar_excepcion(PermissionError()) == "security"
    assert _clasificar_excepcion(ValueError()) == "validation"
