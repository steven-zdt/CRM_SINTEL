from pathlib import Path

from tools.ekg import schema
from tools.ekg.extract_js import extract_app_js

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _graph():
    return extract_app_js("compras", PROJECT_ROOT)


def test_finds_all_four_js_files():
    graph = _graph()
    js_paths = {n.properties["path"] for n in graph.nodes.values() if n.label == schema.NODE_JS}
    assert js_paths == {
        "apps/tenant/compras/static/compras/js/compras.api.js",
        "apps/tenant/compras/static/compras/js/compras.utils.js",
        "apps/tenant/compras/static/compras/js/features/compras_list.js",
        "apps/tenant/compras/static/compras/js/features/compras_editor.js",
    }


def test_api_root_literal_captured_as_endpoint():
    graph = _graph()
    endpoint_id = schema.endpoint_id("compras", "/api/v1/compras/", "js-literal")
    assert endpoint_id in graph.nodes


def test_template_string_built_from_const_resolves():
    """PLANTILLAS_ROOT = `${API_ROOT}plantillas/` should flatten to a
    resolvable literal, not be dropped just because it is a template
    expression (see collect_const_string_bindings in extract_js.py)."""
    graph = _graph()
    endpoint_id = schema.endpoint_id("compras", "/api/v1/compras/plantillas/", "js-literal")
    assert endpoint_id in graph.nodes
