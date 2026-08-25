import json
import re
from pathlib import Path

from tools.ekg import schema
from tools.ekg.build_graph import build_app_graph
from tools.ekg.export_html import build_export_data, render_html

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_export_data_is_sorted_by_label_then_display_name():
    graph = build_app_graph("compras", PROJECT_ROOT)
    data = build_export_data(graph)
    keys = [(n["label"], n["display"].lower()) for n in data["nodes"]]
    assert keys == sorted(keys)


def test_export_data_label_counts_match_node_labels():
    graph = build_app_graph("compras", PROJECT_ROOT)
    data = build_export_data(graph)
    for label, count in data["label_counts"].items():
        assert count == sum(1 for n in graph.nodes.values() if n.label == label)


def test_rendered_html_has_exactly_one_script_close_tag():
    """AGENTS.md's own body text (extracted verbatim into Rule/Document node
    properties) contains literal code examples with "<script>" - embedding
    that text unescaped inside the page's own <script> block lets the FIRST
    such "</script" substring close the real tag early, dumping the rest of
    the JSON as visible page text (confirmed by hand: opening the
    unescaped version in a real browser rendered a wall of raw JSON/markdown
    instead of the UI - not a rendering-tool artifact). This is why
    render_html() escapes "</" to "<\\/" - regression guard for that fix."""
    graph = build_app_graph("core", PROJECT_ROOT)
    data = build_export_data(graph)
    assert any("</" in json.dumps(n["properties"]) for n in data["nodes"] if n["label"] == schema.NODE_RULE), (
        "fixture assumption broken: expected at least one Rule body containing a literal '</' "
        "sequence (e.g. a code example) to exercise the bug this test guards against"
    )

    html = render_html(data)
    assert html.count("</script>") == 1


def test_rendered_html_embeds_valid_json_that_round_trips_the_graph():
    graph = build_app_graph("compras", PROJECT_ROOT)
    data = build_export_data(graph)
    html = render_html(data)

    match = re.search(r"const DATA = ", html)
    assert match is not None
    decoded, _ = json.JSONDecoder().raw_decode(html, match.end())

    assert len(decoded["nodes"]) == len(data["nodes"])
    assert len(decoded["edges"]) == len(data["edges"])
