"""AI-VECTOR-06: gate critico de seguridad y aislamiento multi-tenant.

Escenarios obligatorios del mandato:
  1. tenant_A / tenant_B  -> buscar desde A nunca devuelve documentos de B
  2. usuario con alcance empresa/sede/area -> solo documentos autorizados
  3. campos FORBIDDEN/MASKED -> nunca llegan al embedding
  4. ToolRisk.SENSITIVE_READ NO es proteccion automatica (ver
     apps/services/ai/tests/test_toolrisk_not_enforced.py)

  cross_tenant_leaks = 0 / forbidden_indexed = 0 / unauthorized_retrieval = 0
"""

import pytest
from django.db import connection
from django_tenants.utils import schema_context

from apps.services.ai.context import AIContext
from apps.tenant.ai_knowledge.models import AIKnowledgeChunk, AIKnowledgeDocument
from apps.tenant.ai_knowledge.services import (
    FORBIDDEN_MODEL_FIELDS,
    INDEXABLE_SOURCES,
    EmbeddingService,
    RetrievalService,
    is_indexable,
)
from apps.tenant.empresa.models import Empresa

pytestmark = pytest.mark.django_db


def _emp(schema):
    with schema_context(schema):
        return Empresa.objects.only("id").first()


def _ctx(empresa_id, *, alcance="EMPRESA", sede_ids=(), area_ids=()):
    return AIContext(
        user_id=1,
        empresa_id=empresa_id,
        schema_name="",
        rol="OPERADOR",
        alcance=alcance,
        sede_ids=tuple(sede_ids),
        area_ids=tuple(area_ids),
    )


# ========================================================================= #
# 1. AISLAMIENTO CROSS-TENANT
# ========================================================================= #
def test_cross_tenant_retrieval_no_leak(tenant_a, tenant_b, stub_provider):
    emb = EmbeddingService(provider=stub_provider)
    ret = RetrievalService(provider=stub_provider)

    with schema_context(tenant_a.schema_name):
        emb.index_text(
            empresa=_emp(tenant_a.schema_name), source_type="producto_descripcion",
            source_id="A1", text="documento confidencial del tenant A sobre precios",
        )
    with schema_context(tenant_b.schema_name):
        emb.index_text(
            empresa=_emp(tenant_b.schema_name), source_type="producto_descripcion",
            source_id="B1", text="documento confidencial del tenant B sobre precios",
        )

    # Buscar desde A: solo ve A. Desde B: solo ve B.
    with schema_context(tenant_a.schema_name):
        hits_a = ret.search(empresa=_emp(tenant_a.schema_name), query="documento confidencial precios", k=10)
        assert hits_a and all(h.source_id == "A1" for h in hits_a)
    with schema_context(tenant_b.schema_name):
        hits_b = ret.search(empresa=_emp(tenant_b.schema_name), query="documento confidencial precios", k=10)
        assert hits_b and all(h.source_id == "B1" for h in hits_b)


def test_cross_tenant_orm_es_estructuralmente_ciego(tenant_a, tenant_b, stub_provider):
    emb = EmbeddingService(provider=stub_provider)
    with schema_context(tenant_a.schema_name):
        emb.index_text(
            empresa=_emp(tenant_a.schema_name), source_type="producto_descripcion",
            source_id="ONLY_A", text="solo en A",
        )
    # Desde el schema de B, el ORM no ve NADA de la tabla de A.
    with schema_context(tenant_b.schema_name):
        assert AIKnowledgeDocument.objects.filter(source_id="ONLY_A").count() == 0
        assert AIKnowledgeChunk.objects.count() == 0


def test_cross_tenant_empresa_id_falso_no_cruza_schema(tenant_a, tenant_b, stub_provider):
    """Aun pasando el empresa_id de A al buscar dentro del schema de B, no hay fuga:
    la tabla vive en el schema, y el empresa_id de A no existe en el schema de B."""
    emb = EmbeddingService(provider=stub_provider)
    ret = RetrievalService(provider=stub_provider)
    with schema_context(tenant_a.schema_name):
        emp_a = _emp(tenant_a.schema_name)
        emp_a_id = emp_a.id
        emb.index_text(
            empresa=emp_a, source_type="producto_descripcion",
            source_id="XA", text="dato de A",
        )
    with schema_context(tenant_b.schema_name):
        # search() acepta un id crudo -- aun asi la tabla vive en el schema de B.
        hits = ret.search(empresa=emp_a_id, query="dato de A", k=10)
        assert hits == []


# ========================================================================= #
# 2. ALCANCE ORGANIZACIONAL (empresa / sede / area)
# ========================================================================= #
@pytest.fixture
def seeded_scoped(tenant_a, stub_provider):
    emb = EmbeddingService(provider=stub_provider)
    with schema_context(tenant_a.schema_name):
        emp = _emp(tenant_a.schema_name)
        emb.index_text(empresa=emp, source_type="producto_descripcion", source_id="S1",
                       text="politica de la sede 1", metadata={"sede_id": 1})
        emb.index_text(empresa=emp, source_type="producto_descripcion", source_id="S2",
                       text="politica de la sede 2", metadata={"sede_id": 2})
        emb.index_text(empresa=emp, source_type="producto_descripcion", source_id="SN",
                       text="politica general sin sede")
        emb.index_text(empresa=emp, source_type="producto_descripcion", source_id="AR7",
                       text="nota del area 7", metadata={"area_id": 7})
    return tenant_a, emp.id


def test_alcance_empresa_ve_todo(seeded_scoped, stub_provider):
    tenant_a, emp_id = seeded_scoped
    ret = RetrievalService(provider=stub_provider)
    with schema_context(tenant_a.schema_name):
        ctx = _ctx(emp_id, alcance="EMPRESA")
        hits = ret.search_for_context(ctx, "politica nota", k=20)
        assert {h.source_id for h in hits} == {"S1", "S2", "SN", "AR7"}


def test_alcance_sede_solo_su_sede_mas_los_sin_sede(seeded_scoped, stub_provider):
    tenant_a, emp_id = seeded_scoped
    ret = RetrievalService(provider=stub_provider)
    with schema_context(tenant_a.schema_name):
        ctx = _ctx(emp_id, alcance="SEDE", sede_ids=(1,))
        got = {h.source_id for h in ret.search_for_context(ctx, "politica nota", k=20)}
        assert "S1" in got and "SN" in got and "AR7" in got  # AR7 no declara sede -> NULL-safe
        assert "S2" not in got  # <-- unauthorized_retrieval = 0


def test_alcance_sede_sin_asignaciones_no_ve_ninguna_con_sede(seeded_scoped, stub_provider):
    tenant_a, emp_id = seeded_scoped
    ret = RetrievalService(provider=stub_provider)
    with schema_context(tenant_a.schema_name):
        ctx = _ctx(emp_id, alcance="SEDE", sede_ids=())  # tupla vacia => "nada con sede"
        got = {h.source_id for h in ret.search_for_context(ctx, "politica nota", k=20)}
        assert "S1" not in got and "S2" not in got
        assert "SN" in got and "AR7" in got


def test_alcance_area_solo_su_area_mas_los_sin_area(seeded_scoped, stub_provider):
    tenant_a, emp_id = seeded_scoped
    ret = RetrievalService(provider=stub_provider)
    with schema_context(tenant_a.schema_name):
        ctx = _ctx(emp_id, alcance="AREA", area_ids=(7,))
        got = {h.source_id for h in ret.search_for_context(ctx, "politica nota", k=20)}
        assert "AR7" in got and "SN" in got and "S1" in got and "S2" in got  # sede no es el eje de AREA

        ctx_other = _ctx(emp_id, alcance="AREA", area_ids=(99,))
        got2 = {h.source_id for h in ret.search_for_context(ctx_other, "politica nota", k=20)}
        assert "AR7" not in got2


def test_search_for_context_usa_empresa_id_del_contexto(seeded_scoped, stub_provider):
    """No hay parametro empresa que pasar -- sale del contexto, siempre."""
    tenant_a, emp_id = seeded_scoped
    ret = RetrievalService(provider=stub_provider)
    with schema_context(tenant_a.schema_name):
        ctx = _ctx(emp_id + 999, alcance="EMPRESA")  # empresa_id inexistente
        assert ret.search_for_context(ctx, "politica", k=20) == []


# ========================================================================= #
# 3. FORBIDDEN / MASKED NUNCA LLEGAN AL EMBEDDING
# ========================================================================= #
def test_allowlist_no_referencia_ningun_campo_prohibido():
    """Candado: ningun IndexableSource apunta a un campo FORBIDDEN/MASKED."""
    for src in INDEXABLE_SOURCES:
        assert (src.model_label, src.text_field) not in FORBIDDEN_MODEL_FIELDS
        for mf in src.metadata_fields:
            assert (src.model_label, mf) not in FORBIDDEN_MODEL_FIELDS


@pytest.mark.parametrize(
    "forbidden_source_type",
    [
        "empleado_salario", "empleado_eps", "empleado_afp", "contrato_salario_mensual",
        "devengo_salario_base", "cuenta_bancaria_numero", "transaccion_notas_conciliacion",
        "extracto_saldo_final",
    ],
)
def test_indexar_source_no_allowlisted_es_rechazado(tenant_a, stub_provider, forbidden_source_type):
    assert is_indexable(forbidden_source_type) is False
    emb = EmbeddingService(provider=stub_provider)
    with schema_context(tenant_a.schema_name):
        with pytest.raises(ValueError):
            emb.index_text(
                empresa=_emp(tenant_a.schema_name),
                source_type=forbidden_source_type,
                source_id="X",
                text="salario 5000000 eps sanitas afp porvenir",
            )
        # Nada quedo persistido ni embebido.
        assert AIKnowledgeDocument.objects.filter(source_type=forbidden_source_type).count() == 0


def test_forbidden_field_no_se_indexa_ni_con_texto_realista(tenant_a, stub_provider):
    emb = EmbeddingService(provider=stub_provider)
    with schema_context(tenant_a.schema_name):
        emp = _emp(tenant_a.schema_name)
        before = AIKnowledgeChunk.objects.count()
        with pytest.raises(ValueError):
            emb.index_text(
                empresa=emp, source_type="cuenta_bancaria_numero", source_id="42",
                text="Numero de cuenta 001-234567-89 saldo 12.400.000",
            )
        assert AIKnowledgeChunk.objects.count() == before  # forbidden_indexed = 0


def test_allowlist_escape_hatch_es_explicito(tenant_a, stub_provider):
    """allow_unlisted=True existe para uso interno controlado y deja rastro (warning)."""
    emb = EmbeddingService(provider=stub_provider)
    with schema_context(tenant_a.schema_name):
        r = emb.index_text(
            empresa=_emp(tenant_a.schema_name), source_type="tipo_interno_test",
            source_id="1", text="texto de prueba", allow_unlisted=True,
        )
        assert r.skipped is False and r.n_chunks >= 1


def test_sources_self_check_bloquea_allowlist_insegura():
    """El candado de import (`_assert_allowlist_safe`) falla si se agrega un origen prohibido."""
    from apps.tenant.ai_knowledge.services import sources as s

    bad = s.IndexableSource(
        source_type="x", model_label="bancos.CuentaBancaria", text_field="numero",
        description="prohibido",
    )
    original = s.INDEXABLE_SOURCES
    s.INDEXABLE_SOURCES = original + (bad,)
    try:
        with pytest.raises(RuntimeError):
            s._assert_allowlist_safe()
    finally:
        s.INDEXABLE_SOURCES = original
