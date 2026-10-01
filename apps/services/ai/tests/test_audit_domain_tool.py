"""
LOOP 1 del MCP Control Plane (docs/mcp/ADR-MCP-001.md): tests de
`audit_domain`. Unit tests puros (sin DB) -- orquesta 3 tools
`platform` ya reales, todas sin dependencia de DB.
"""

from apps.services.ai.context import AIContext
from apps.services.ai.tools.platform_audit_tools import AuditDomainTool


def _fake_context() -> AIContext:
    return AIContext(
        user_id=1,
        empresa_id=1,
        schema_name="test",
        rol="ADMIN",
        alcance="EMPRESA",
    )


def test_app_label_vacio_es_validation_error():
    result = AuditDomainTool().run(_fake_context(), app_label="")
    assert result.status == "VALIDATION_ERROR"


def test_app_label_inexistente_es_not_found():
    result = AuditDomainTool().run(_fake_context(), app_label="app_que_nunca_existio")
    assert result.status == "NOT_FOUND"


def test_app_real_agrega_inventory_rules_y_dependencies():
    """clientes es una app real con snapshot EKG (tools/ekg/out/clientes.json)
    y dependencias reales conocidas (ver VENTAS_FACTURAS_AUDIT.md) -- confirma
    que las 3 sub-tools se ejecutaron de verdad, no solo una."""
    result = AuditDomainTool().run(_fake_context(), app_label="tenant_clientes")

    assert result.status == "OK"
    assert result.data["app_label"] == "tenant_clientes"
    # inventory: viene de ProjectInventoryTool, mismo dict que esa tool ya prueba.
    assert result.data["inventory"]["app_label"] == "tenant_clientes"
    assert result.data["inventory"]["model_count"] >= 1
    # rules: viene de ai_project_map(question="rules_for_app") con el nombre
    # de CARPETA real ("clientes"), no el app_label de Django.
    assert result.data["rules_status"] == "OK"
    assert result.data["rules"]["app_name"] == "clientes"
    # dependencies: viene de inspect_dependencies, tambien con el nombre de
    # carpeta correcto -- el bug real encontrado al construir esta tool era
    # pasar app_label crudo aqui, lo que filtraba silenciosamente a 0 edges.
    assert result.data["dependencies"]["edge_count"] > 0
    for edge in result.data["dependencies"]["edges"]:
        assert edge["source_app"] == "clientes" or edge["target_app"] == "clientes"
    # Nunca reclama cubrir ejes que no cubre.
    assert "permissions_detail" in result.data["not_covered"]


def test_app_sin_snapshot_ekg_no_falla_toda_la_auditoria():
    """tenant_ai_knowledge es una app real registrada SIN snapshot en
    tools/ekg/out/ (no hay 'ai_knowledge.json') -- rules_status debe
    reportar NOT_FOUND sin tumbar el resto de la auditoria (inventory
    sigue siendo util aunque falte el snapshot)."""
    result = AuditDomainTool().run(_fake_context(), app_label="tenant_ai_knowledge")

    assert result.status == "OK"
    assert result.data["rules_status"] == "NOT_FOUND"
    assert result.data["rules"] is None
    assert "ekg-build" in result.data["rules_message"]
    # inventory SI se resolvio -- la ausencia de snapshot EKG no lo bloquea.
    assert result.data["inventory"]["app_label"] == "tenant_ai_knowledge"
