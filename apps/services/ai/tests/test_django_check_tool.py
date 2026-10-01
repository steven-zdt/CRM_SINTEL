"""
LOOP 1 del MCP Control Plane (docs/mcp/ADR-MCP-001.md): tests de
`django_check`. Unit test puro (sin DB) -- django.core.checks.run_checks()
no toca la base de datos por defecto.
"""

from apps.services.ai.context import AIContext
from apps.services.ai.tools.platform_audit_tools import DjangoCheckTool


def _fake_context() -> AIContext:
    return AIContext(
        user_id=1,
        empresa_id=1,
        schema_name="test",
        rol="ADMIN",
        alcance="EMPRESA",
    )


def test_corre_el_check_framework_real():
    result = DjangoCheckTool().run(_fake_context())

    assert result.status == "OK"
    assert result.data["source"] == "django.core.checks.run_checks()"
    assert result.data["overall_status"] in {"PASS", "WARN", "FAIL"}
    assert result.data["error_count"] == sum(1 for i in result.data["issues"] if i["is_error"])
    assert result.data["warning_count"] == sum(
        1 for i in result.data["issues"] if not i["is_error"]
    )


def test_deployment_checks_es_opcional_y_no_falla():
    result = DjangoCheckTool().run(_fake_context(), include_deployment_checks=True)
    assert result.status == "OK"
