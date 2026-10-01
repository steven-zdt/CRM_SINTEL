"""
LOOP 1 del MCP Control Plane (docs/mcp/ADR-MCP-001.md): tests de
`inspect_dependencies`. Unit tests puros (sin DB) -- la tool corre AST
sobre el filesystem real del repo (tools/organizational_governance/
dependencies.py), sin tocar la base de datos.
"""

from apps.services.ai.context import AIContext
from apps.services.ai.tools.platform_audit_tools import InspectDependenciesTool


def _fake_context() -> AIContext:
    return AIContext(
        user_id=1,
        empresa_id=1,
        schema_name="test",
        rol="ADMIN",
        alcance="EMPRESA",
    )


def test_classification_invalida_es_validation_error():
    result = InspectDependenciesTool().run(_fake_context(), classification="URGENTISIMO")
    assert result.status == "VALIDATION_ERROR"


def test_sin_filtros_descubre_edges_reales_del_repo():
    result = InspectDependenciesTool().run(_fake_context())

    assert result.status == "OK"
    assert result.data["source"] == "tools.organizational_governance.dependencies"
    assert result.data["edge_count"] > 0
    # clientes<->facturas es una dependencia real conocida del proyecto
    # (ver documentacion/VENTAS_FACTURAS_AUDIT.md) -- confirma que la tool
    # ejecuto AST real, no una lista vacia/inventada.
    apps_involucradas = {e["source_app"] for e in result.data["edges"]} | {
        e["target_app"] for e in result.data["edges"]
    }
    assert "clientes" in apps_involucradas


def test_app_label_filtra_edges_donde_la_app_es_origen_o_destino():
    result_todos = InspectDependenciesTool().run(_fake_context())
    result_clientes = InspectDependenciesTool().run(_fake_context(), app_label="clientes")

    assert result_clientes.status == "OK"
    assert 0 < result_clientes.data["edge_count"] < result_todos.data["edge_count"]
    for edge in result_clientes.data["edges"]:
        assert edge["source_app"] == "clientes" or edge["target_app"] == "clientes"


def test_cycles_se_calculan_siempre_sobre_el_grafo_completo_no_el_filtrado():
    """Filtrar por app_label/classification no debe cambiar cycle_count --
    los ciclos son una propiedad del grafo completo, nunca del subconjunto
    visible (regla explicita del docstring de la tool)."""
    result_todos = InspectDependenciesTool().run(_fake_context())
    result_filtrado = InspectDependenciesTool().run(_fake_context(), app_label="clientes")

    assert result_filtrado.data["cycle_count"] == result_todos.data["cycle_count"]
    assert result_filtrado.data["cycles"] == result_todos.data["cycles"]


def test_classification_filtra_correctamente():
    result = InspectDependenciesTool().run(_fake_context(), classification="pull")

    assert result.status == "OK"
    assert all(e["classification"] == "PULL" for e in result.data["edges"])
    # forbidden_count_total nunca cambia con el filtro -- siempre reporta
    # la verdad del grafo completo.
    result_todos = InspectDependenciesTool().run(_fake_context())
    assert result.data["forbidden_count_total"] == result_todos.data["forbidden_count_total"]
