"""
LOOP 1 del MCP Control Plane (docs/mcp/ADR-MCP-001.md): tests de
`production_readiness`. Requiere DB real (django_db) porque al menos un
check del registry (version del servidor Postgres) usa
django.db.connection.cursor() -- no tenant fixtures, solo acceso a la
conexion default.
"""

import pytest

from apps.services.ai.context import AIContext
from apps.services.ai.tools.platform_audit_tools import ProductionReadinessTool


def _fake_context() -> AIContext:
    return AIContext(
        user_id=1,
        empresa_id=1,
        schema_name="test",
        rol="ADMIN",
        alcance="EMPRESA",
    )


@pytest.mark.django_db
def test_corre_el_registry_real_y_reporta_status_agregado():
    result = ProductionReadinessTool().run(_fake_context())

    assert result.status == "OK"
    assert result.data["source"] == "apps.public.core.production_readiness"
    assert result.data["overall_status"] in {
        "READY",
        "NOT_READY",
        "READY_WITH_EXTERNAL_DEPENDENCIES",
    }
    assert isinstance(result.data["results"], list)
    assert len(result.data["results"]) > 0
    # Cada resultado serializado conserva el schema real (to_dict()), no
    # uno inventado aparte.
    for check in result.data["results"]:
        assert "id" in check
        assert "status" in check
        assert "severity" in check
