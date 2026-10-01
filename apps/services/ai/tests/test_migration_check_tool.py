"""
LOOP 1 del MCP Control Plane (docs/mcp/ADR-MCP-001.md): tests de
`migration_check`. Requiere DB real (django_db) -- 'makemigrations
--check' consulta `django_migrations` real via
loader.check_consistent_history() para saber que migraciones ya estan
aplicadas (hallazgo real al construir este test: la primera version
asumia que era 100% sin DB, la corrida real lo desmintio -- nunca
escribe migraciones nuevas, pero SI lee la tabla de migraciones).
"""

import pytest

from apps.services.ai.context import AIContext
from apps.services.ai.tools.platform_audit_tools import MigrationCheckTool


def _fake_context() -> AIContext:
    return AIContext(
        user_id=1,
        empresa_id=1,
        schema_name="test",
        rol="ADMIN",
        alcance="EMPRESA",
    )


@pytest.mark.django_db
def test_corre_makemigrations_check_real_sin_escribir_nada():
    result = MigrationCheckTool().run(_fake_context())

    assert result.status == "OK"
    assert result.data["source"].startswith("manage.py makemigrations --check")
    assert result.data["overall_status"] in {"PASS", "FAIL"}
    assert isinstance(result.data["has_missing_migrations"], bool)
    # PASS <-> has_missing_migrations=False son consistentes entre si.
    if result.data["overall_status"] == "PASS":
        assert result.data["has_missing_migrations"] is False
    else:
        assert result.data["has_missing_migrations"] is True
