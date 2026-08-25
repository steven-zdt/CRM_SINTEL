from pathlib import Path

from tools.ekg import schema
from tools.ekg.build_graph import build_app_graph
from tools.ekg.impact import (
    find_nodes_by_name,
    find_nodes_by_path_fragment,
    impact_of_offline,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_impact_walks_model_to_endpoint_chain_on_real_extracted_graph():
    """OrdenCompra -[REFERENCES]- Field, -[USES]- 3 Serializers, -[USES]-
    ViewSet, -[EXPOSES]- Endpoints: exercises both REVERSE_DEP_RELS (the
    dependents) and FORWARD_PRODUCES_RELS (what the impacted ViewSet itself
    exposes) in one real, extracted-from-source graph - not a synthetic
    fixture, so this fails loudly if extract_python.py's edge directions
    ever change without this module being updated to match."""
    graph = build_app_graph("compras", PROJECT_ROOT)
    target = find_nodes_by_name(graph, "OrdenCompra", schema.NODE_MODEL)[0]

    report = impact_of_offline(graph, target, max_hops=4)

    names_by_label = {}
    for hit in report.hits:
        names_by_label.setdefault(hit.label, set()).add(hit.name)

    assert "OrdenCompraListSerializer" in names_by_label.get(schema.NODE_SERIALIZER, set())
    assert "OrdenCompraViewSet" in names_by_label.get(schema.NODE_VIEWSET, set())
    assert names_by_label.get(schema.NODE_ENDPOINT)  # at least one Endpoint reached via EXPOSES

    # Endpoint must be reached at a *later* hop than the ViewSet that exposes
    # it (EXPOSES is a forward walk starting only once the ViewSet itself is
    # already impacted) - if this were hop 1 it would mean the traversal
    # short-circuited the dependency chain.
    viewset_hop = next(h.hop for h in report.hits if h.name == "OrdenCompraViewSet")
    endpoint_hop = next(h.hop for h in report.hits if h.label == schema.NODE_ENDPOINT)
    assert endpoint_hop > viewset_hop


def test_impact_reports_app_level_rules_docs_and_tests():
    graph = build_app_graph("compras", PROJECT_ROOT)
    target = find_nodes_by_name(graph, "OrdenCompra", schema.NODE_MODEL)[0]

    report = impact_of_offline(graph, target, max_hops=4)

    assert report.apps_touched == ["compras"]
    assert any("AGENTS.md" in r for r in report.rules)
    assert any("AUDITORIA_FLUJO_COMPRAS.md" in d for d in report.docs)
    assert report.tests  # compras has real test coverage for this model's flow


def test_impact_max_hops_truncates_and_flags_it():
    graph = build_app_graph("compras", PROJECT_ROOT)
    target = find_nodes_by_name(graph, "OrdenCompra", schema.NODE_MODEL)[0]

    shallow = impact_of_offline(graph, target, max_hops=1)
    deep = impact_of_offline(graph, target, max_hops=4)

    assert len(shallow.hits) < len(deep.hits)
    assert shallow.truncated is True
    assert all(h.hop == 1 for h in shallow.hits)


def test_find_nodes_by_name_is_exact_and_label_filterable():
    graph = build_app_graph("compras", PROJECT_ROOT)

    all_matches = find_nodes_by_name(graph, "OrdenCompra")
    assert len(all_matches) == 1
    assert all_matches[0].label == schema.NODE_MODEL

    assert find_nodes_by_name(graph, "OrdenCompra", schema.NODE_SERIALIZER) == []
    assert find_nodes_by_name(graph, "DoesNotExistAnywhere") == []


def test_find_nodes_by_path_fragment_matches_js_and_test_paths():
    graph = build_app_graph("compras", PROJECT_ROOT)

    js_hits = find_nodes_by_path_fragment(graph, "compras.api.js")
    assert any(n.label == schema.NODE_JS for n in js_hits)

    no_hits = find_nodes_by_path_fragment(graph, "no-such-fragment-xyz")
    assert no_hits == []


def test_cross_app_services_mixin_inherited_by_a_viewset_splits_into_two_node_identities():
    """Known gap found verifying this engine for OCF (Fase 12, 2026-08-08),
    documented in this module's own docstring, not fixed: OrganizationalContextMixin
    is defined under apps/tenant/core/services/ (a real Service node once
    `core` is extracted) AND inherited by ViewSets in other apps (an
    external ViewSet stub minted by extract_viewsets()'s cross-app INHERITS
    resolver, which cannot tell a services-folder mixin from a ViewSet-family
    base). The two never merge - `find_nodes_by_name` must find both labels
    (proving the split is real, not a one-off flake) and the real INHERITS
    edges from compras' own ViewSets must land on the ViewSet-labeled stub,
    not the Service-labeled node - if this test ever starts failing because
    only one label exists, the resolver gap has been fixed and this test
    (and the docstring paragraph it pins) should be deleted, not patched."""
    graph = schema.Graph()
    graph.merge(build_app_graph("core", PROJECT_ROOT))
    graph.merge(build_app_graph("compras", PROJECT_ROOT))

    matches = find_nodes_by_name(graph, "OrganizationalContextMixin")
    labels = {n.label for n in matches}
    assert labels == {schema.NODE_SERVICE, schema.NODE_VIEWSET}, (
        "expected the known split-identity gap (Service + ViewSet stub); "
        "if only one label remains, the extractor gap was fixed - update the docstring"
    )

    viewset_stub = next(n for n in matches if n.label == schema.NODE_VIEWSET)
    orden_compra_vs = graph.nodes[schema.viewset_id("compras", "OrdenCompraViewSet")]
    real_inherits_targets = {
        e.target_id for e in graph.edges
        if e.source_id == orden_compra_vs.id and e.rel_type == schema.REL_INHERITS
    }
    assert viewset_stub.id in real_inherits_targets  # the real edge lands on the stub, not the Service node


def test_reverse_and_forward_relation_sets_do_not_overlap():
    """The whole traversal algorithm assumes these two sets are disjoint -
    a relation type walked in reverse (dependents) can never also be walked
    forward (produced) in the same pass, or a node could be double-counted
    at the wrong hop with the wrong via_rel."""
    from tools.ekg.impact import FORWARD_PRODUCES_RELS, REVERSE_DEP_RELS

    assert REVERSE_DEP_RELS & FORWARD_PRODUCES_RELS == set()
    # and both must only use relation types the schema actually knows about
    assert REVERSE_DEP_RELS <= schema.REL_TYPES
    assert FORWARD_PRODUCES_RELS <= schema.REL_TYPES
