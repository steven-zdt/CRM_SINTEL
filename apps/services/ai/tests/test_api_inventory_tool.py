"""
LOOP 1 del MCP Control Plane (docs/mcp/ADR-MCP-001.md): tests de
`api_inventory`. Unit tests puros (sin DB) -- recorre el resolver de
URLs ya cargado en memoria, sin consultar la base de datos.
"""

from apps.services.ai.context import AIContext
from apps.services.ai.tools.platform_audit_tools import ApiInventoryTool


def _fake_context() -> AIContext:
    return AIContext(
        user_id=1,
        empresa_id=1,
        schema_name="test",
        rol="ADMIN",
        alcance="EMPRESA",
    )


def test_urlconf_invalido_es_validation_error():
    result = ApiInventoryTool().run(_fake_context(), urlconf="modulo.que.no.existe")
    assert result.status == "VALIDATION_ERROR"


def test_path_prefix_filtra_endpoints_reales():
    result = ApiInventoryTool().run(_fake_context(), path_prefix="clientes")

    assert result.status == "OK"
    assert result.data["endpoint_count"] > 0
    assert not result.data["truncated"]
    view_classes = {e["view_class"] for e in result.data["endpoints"]}
    # ClienteViewSet es el ViewSet real de este dominio -- confirma que se
    # recorrio el resolver real, no una lista inventada.
    assert "ClienteViewSet" in view_classes
    for e in result.data["endpoints"]:
        assert "clientes" in e["path"]


def test_sin_prefix_deduplica_por_name_y_limita_a_200():
    result = ApiInventoryTool().run(_fake_context())

    assert result.status == "OK"
    names = [e["name"] for e in result.data["endpoints"]]
    assert len(names) == len(set(names))  # sin duplicados por variante .json
    assert len(result.data["endpoints"]) <= 200
    if len(result.data["endpoints"]) == 200:
        assert result.data["truncated"] is True


def test_nunca_reclama_cubrir_permission_classes():
    result = ApiInventoryTool().run(_fake_context(), path_prefix="clientes")
    assert "permission_classes" in result.data["not_covered"]
