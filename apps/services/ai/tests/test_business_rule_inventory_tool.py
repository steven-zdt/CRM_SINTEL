"""
LOOP 1 del MCP Control Plane (docs/mcp/ADR-MCP-001.md): tests de
`business_rule_inventory`. Unit tests puros (sin DB) -- la tool carga
snapshots ya generados de tools/ekg/out/*.json, sin tocar la base de
datos ni Neo4j.
"""

from apps.services.ai.context import AIContext
from apps.services.ai.tools.platform_audit_tools import BusinessRuleInventoryTool


def _fake_context() -> AIContext:
    return AIContext(
        user_id=1,
        empresa_id=1,
        schema_name="test",
        rol="ADMIN",
        alcance="EMPRESA",
    )


def test_rule_invalida_es_validation_error():
    result = BusinessRuleInventoryTool().run(_fake_context(), rule="regla_que_no_existe")
    assert result.status == "VALIDATION_ERROR"


def test_sin_rule_corre_las_6_reglas_y_nunca_oculta_que_es_snapshot():
    result = BusinessRuleInventoryTool().run(_fake_context())

    assert result.status == "OK"
    assert result.data["source"] == "tools.ekg.governance"
    assert len(result.data["checks"]) == 6
    assert result.data["total_violations"] == sum(
        c["violation_count"] for c in result.data["checks"].values()
    )
    assert result.data["overall_status"] in {"PASS", "FAIL"}
    # Nunca debe fingir ser el estado vivo -- siempre reporta cuando se
    # genero el snapshot mergeado.
    assert result.data["snapshot_oldest"]
    assert result.data["snapshot_newest"]
    assert result.data["node_count"] > 0
    assert result.data["edge_count"] > 0


def test_con_rule_corre_solo_esa_regla():
    result = BusinessRuleInventoryTool().run(
        _fake_context(), rule="models_not_inheriting_tenant_base"
    )

    assert result.status == "OK"
    assert list(result.data["checks"].keys()) == ["models_not_inheriting_tenant_base"]
