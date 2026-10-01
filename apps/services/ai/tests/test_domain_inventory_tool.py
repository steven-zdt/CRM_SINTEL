"""
LOOP 1 del MCP Control Plane (docs/mcp/ADR-MCP-001.md): tests de
`domain_inventory`. Unit tests puros (sin DB) -- filtra
tool_metadata() ya calculado, no consulta nada nuevo.
"""

from apps.services.ai.context import AIContext
from apps.services.ai.tools.platform_audit_tools import DomainInventoryTool


def _fake_context() -> AIContext:
    return AIContext(
        user_id=1,
        empresa_id=1,
        schema_name="test",
        rol="ADMIN",
        alcance="EMPRESA",
    )


def test_domain_vacio_es_validation_error():
    result = DomainInventoryTool().run(_fake_context(), domain="")
    assert result.status == "VALIDATION_ERROR"


def test_domain_sin_tools_registradas_es_not_found():
    result = DomainInventoryTool().run(_fake_context(), domain="impuestos")
    assert result.status == "NOT_FOUND"


def test_domain_real_lista_sus_tools_reales():
    result = DomainInventoryTool().run(_fake_context(), domain="clientes")

    assert result.status == "OK"
    assert result.data["source"] == "AIToolRegistry.tool_metadata()"
    tool_names = {t["name"] for t in result.data["tools"]}
    # buscar_cliente y validar_cliente son las 2 tools reales de este
    # dominio (AI_TOOL_REGISTRY.md) -- confirma filtrado real, no vacio.
    assert "buscar_cliente" in tool_names
    assert "validar_cliente" in tool_names
    assert result.data["tool_count"] == len(result.data["tools"])
    assert all(t["domain"] == "clientes" for t in result.data["tools"])
