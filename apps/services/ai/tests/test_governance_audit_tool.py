"""
LOOP 1 del MCP Control Plane (docs/mcp/ADR-MCP-001.md): tests de
`governance_audit`. Unit test puro (sin DB) -- la tool invoca
tools.organizational_governance tal cual, contra el filesystem real del
repo, sin tocar la base de datos.
"""

from apps.services.ai.context import AIContext
from apps.services.ai.tools.platform_audit_tools import GovernanceAuditTool


def _fake_context() -> AIContext:
    return AIContext(
        user_id=1,
        empresa_id=1,
        schema_name="test",
        rol="ADMIN",
        alcance="EMPRESA",
    )


def test_severity_filter_invalido_es_validation_error():
    result = GovernanceAuditTool().run(_fake_context(), severity_filter="URGENTISIMO")
    assert result.status == "VALIDATION_ERROR"


def test_corre_el_motor_real_y_reporta_status_agregado():
    result = GovernanceAuditTool().run(_fake_context())

    assert result.status == "OK"
    assert result.data["source"] == "tools.organizational_governance"
    assert result.data["overall_status"] in {"PASS", "WARN", "FAIL"}
    assert isinstance(result.data["findings"], list)
    assert result.data["finding_count"] == len(result.data["findings"])
    # Cada finding serializado conserva el schema real de Finding (no un
    # esquema inventado aparte) mas el status derivado.
    for finding in result.data["findings"]:
        assert "rule_id" in finding
        assert "severity" in finding
        assert "status" in finding


def test_severity_filter_real_filtra_correctamente():
    result_todos = GovernanceAuditTool().run(_fake_context())
    severidades_reales = {f["severity"] for f in result_todos.data["findings"]}
    if not severidades_reales:
        return  # nada que filtrar en este snapshot del repo -- no falla el test
    alguna = next(iter(severidades_reales))

    result_filtrado = GovernanceAuditTool().run(_fake_context(), severity_filter=alguna.lower())

    assert result_filtrado.status == "OK"
    assert all(f["severity"] == alguna for f in result_filtrado.data["findings"])
