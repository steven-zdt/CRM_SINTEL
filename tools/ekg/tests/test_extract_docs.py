from pathlib import Path

from tools.ekg import schema
from tools.ekg.extract_docs import extract_agents_md, extract_memory_md, extract_skills

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_universal_rule_tags_link_to_every_app():
    graph = extract_agents_md(PROJECT_ROOT, ["compras"])
    linked_tags = {
        graph.nodes[e.target_id].properties["tag"]
        for e in graph.edges
        if e.rel_type == schema.REL_GOVERNED_BY
    }
    assert {"CRUD-E2E", "ARCHITECTURE", "SECURITY", "BRIDGE", "HTMX-OFFCANVAS"} <= linked_tags


def test_memory_md_adr006_links_to_compras_by_body_mention():
    graph = extract_memory_md(PROJECT_ROOT, ["compras"])
    linked_adrs = {
        graph.nodes[e.target_id].properties["adr"]
        for e in graph.edges
        if e.rel_type == schema.REL_DOCUMENTED_BY
    }
    assert "ADR-006" in linked_adrs


def test_tabulator_skill_extracted_but_only_linked_via_real_mention():
    """compras migrated off Tabulator (ADR-006) - this asserts the
    extractor does not invent a "compras uses Tabulator" relationship, and
    that when it DOES link tabulator.md it is because the skill doc's own
    text literally names compras (the #grid-compras collision example),
    not because of any assumption about which grid library compras uses."""
    graph = extract_skills(PROJECT_ROOT, ["compras"])
    tabulator_id = schema.rule_id(".agents/skills/frontend/tabulator.md", "skill")
    assert tabulator_id in graph.nodes
    text = (PROJECT_ROOT / ".agents/skills/frontend/tabulator.md").read_text(encoding="utf-8")
    is_linked = any(e.target_id == tabulator_id for e in graph.edges)
    assert is_linked == ("compras" in text)
