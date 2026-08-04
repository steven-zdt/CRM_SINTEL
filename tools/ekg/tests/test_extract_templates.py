from pathlib import Path

from tools.ekg import schema
from tools.ekg.extract_templates import extract_app_templates

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _graph():
    return extract_app_templates("compras", PROJECT_ROOT)


def test_assets_template_loads_all_four_js_files():
    graph = _graph()
    assets_id = schema.template_id(
        "apps/tenant/compras/templates/tenant/compras/assets_compras.html"
    )
    js_targets = {
        graph.nodes[e.target_id].properties["path"]
        for e in graph.edges
        if e.source_id == assets_id and e.rel_type == schema.REL_USES
    }
    assert len(js_targets) == 4


def test_list_html_includes_compras_list_html():
    graph = _graph()
    list_id = schema.template_id("apps/tenant/compras/templates/tenant/compras/list.html")
    included = {
        graph.nodes[e.target_id].id
        for e in graph.edges
        if e.source_id == list_id and e.rel_type == schema.REL_USES
    }
    assert schema.template_id(
        "apps/tenant/compras/templates/tenant/compras/compras_list.html"
    ) in included
