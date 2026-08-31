"""Tests puros del registro de tools -- sin DB (Fase 50: 'tool tests' separados de 'integration tests')."""
import pytest

from apps.services.ai.tools.base import BaseTool, ToolKind, ToolResult, ToolRisk
from apps.services.ai.tools.registry import (
    _REGISTRY,
    _reset_registry_for_tests,
    get_tool,
    list_tools,
    register_tool,
    tool_metadata,
)


class _DummyTool(BaseTool):
    name = "dummy_tool_for_tests"
    description = "Tool de prueba, nunca tocar datos reales."
    domain = "test_domain"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ

    def run(self, context, **kwargs):
        return ToolResult(status="OK", data={"ok": True})


@pytest.fixture(autouse=True)
def _isolated_registry():
    """Aisla cada test del registro global real (que ya tiene buscar_cliente registrada por import)."""
    snapshot = dict(_REGISTRY)
    yield
    _reset_registry_for_tests()
    _REGISTRY.update(snapshot)


def test_registrar_y_obtener_tool():
    _reset_registry_for_tests()
    register_tool(_DummyTool())
    assert get_tool("dummy_tool_for_tests") is not None
    assert get_tool("no_existe") is None


def test_registrar_tool_duplicada_falla():
    _reset_registry_for_tests()
    register_tool(_DummyTool())
    with pytest.raises(ValueError):
        register_tool(_DummyTool())


def test_list_tools_filtra_por_domain_y_kind():
    _reset_registry_for_tests()
    register_tool(_DummyTool())
    assert len(list_tools(domain="test_domain")) == 1
    assert len(list_tools(domain="otro_domain")) == 0
    assert len(list_tools(kind=ToolKind.READ)) == 1
    assert len(list_tools(kind=ToolKind.WRITE)) == 0


def test_tool_metadata_no_expone_el_objeto_tool():
    """Regla Absoluta 4/12: metadata serializable, nunca el objeto Python real."""
    _reset_registry_for_tests()
    register_tool(_DummyTool())
    meta = tool_metadata()
    assert meta == [
        {
            "name": "dummy_tool_for_tests",
            "description": "Tool de prueba, nunca tocar datos reales.",
            "domain": "test_domain",
            "kind": "READ",
            "risk": "SAFE_READ",
            "confirmation_required": False,
            "idempotent": True,
        }
    ]
    assert all(isinstance(v, (str, bool)) for v in meta[0].values())
