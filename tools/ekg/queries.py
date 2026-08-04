"""
EKG canned questions - the first slice of the "objetivos secundarios" list
from the EKG spec, scoped to what the apps/tenant/compras pilot graph can
actually answer today.

Every question has two implementations that must agree:
  - an `offline_*` function that walks an in-memory tools.ekg.schema.Graph
    (works with no Neo4j connection - used by --offline and by
    tools/ekg/tests/);
  - a CANNED_CYPHER entry with the equivalent Cypher, for --live once a
    real Neo4j is loaded (see tools/ekg/PILOT_REPORT.md for why that could
    not be exercised in this environment).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.ekg import schema

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _node_by_name(graph: schema.Graph, label: str, name: str) -> schema.Node | None:
    for node in graph.nodes.values():
        if node.label == label and node.properties.get("name") == name:
            return node
    return None


def _edges_from(graph: schema.Graph, source_id: str, rel_type: str) -> list[schema.Edge]:
    return [e for e in graph.edges if e.source_id == source_id and e.rel_type == rel_type]


def _edges_to(graph: schema.Graph, target_id: str, rel_type: str) -> list[schema.Edge]:
    return [e for e in graph.edges if e.target_id == target_id and e.rel_type == rel_type]


# ---------------------------------------------------------------------------
# 1. What ViewSet uses this Serializer?
# ---------------------------------------------------------------------------


def offline_viewsets_using_serializer(graph: schema.Graph, serializer_name: str) -> list[str]:
    node = _node_by_name(graph, schema.NODE_SERIALIZER, serializer_name)
    if node is None:
        return []
    return [
        graph.nodes[e.source_id].properties.get("name", e.source_id)
        for e in _edges_to(graph, node.id, schema.REL_USES)
        if graph.nodes[e.source_id].label == schema.NODE_VIEWSET
    ]


CANNED_CYPHER_VIEWSETS_USING_SERIALIZER = """
MATCH (v:ViewSet)-[:USES]->(s:Serializer {name: $serializer_name})
RETURN v.name AS viewset
"""


# ---------------------------------------------------------------------------
# 2. What JS consumes this endpoint?
# ---------------------------------------------------------------------------


def offline_js_consuming_endpoint_route(graph: schema.Graph, route_substring: str) -> list[str]:
    results = []
    for node in graph.nodes.values():
        if node.label != schema.NODE_ENDPOINT:
            continue
        if route_substring not in node.properties.get("route", ""):
            continue
        for e in _edges_to(graph, node.id, schema.REL_CONSUMES):
            js_node = graph.nodes[e.source_id]
            if js_node.label == schema.NODE_JS:
                results.append(f"{js_node.properties.get('path')} -> {node.properties.get('route')}")
    return sorted(set(results))


CANNED_CYPHER_JS_CONSUMING_ENDPOINT = """
MATCH (j:JS)-[:CONSUMES]->(e:Endpoint)
WHERE e.route CONTAINS $route_substring
RETURN j.path AS js_file, e.route AS route
"""


# ---------------------------------------------------------------------------
# 3. What endpoints expose this model (via its ViewSet -> Serializer -> Meta.model)?
# ---------------------------------------------------------------------------


def offline_endpoints_for_model(graph: schema.Graph, model_name: str) -> list[str]:
    model_node = _node_by_name(graph, schema.NODE_MODEL, model_name)
    if model_node is None:
        return []
    serializer_ids = {e.source_id for e in _edges_to(graph, model_node.id, schema.REL_USES)}
    viewset_ids = set()
    for serializer_id in serializer_ids:
        viewset_ids.update(
            e.source_id for e in _edges_to(graph, serializer_id, schema.REL_USES)
        )
    results = []
    for viewset_id in viewset_ids:
        for e in _edges_from(graph, viewset_id, schema.REL_EXPOSES):
            endpoint = graph.nodes[e.target_id]
            results.append(f"{graph.nodes[viewset_id].properties.get('name')} -> {endpoint.properties.get('route')!r} ({endpoint.properties.get('group')})")
    return sorted(set(results))


CANNED_CYPHER_ENDPOINTS_FOR_MODEL = """
MATCH (m:Model {name: $model_name})<-[:USES]-(s:Serializer)<-[:USES]-(v:ViewSet)-[:EXPOSES]->(e:Endpoint)
RETURN DISTINCT v.name AS viewset, e.route AS route, e.group AS group
"""


# ---------------------------------------------------------------------------
# 4. What AGENTS.md / skill Rules govern this Application?
# ---------------------------------------------------------------------------


def offline_rules_governing_app(graph: schema.Graph, app_name: str) -> list[str]:
    app_id = schema.application_id(app_name)
    if app_id not in graph.nodes:
        return []
    results = []
    for e in _edges_from(graph, app_id, schema.REL_GOVERNED_BY):
        rule = graph.nodes[e.target_id]
        title = rule.properties.get("title", "")
        source = rule.properties.get("source", "")
        results.append(f"{source} :: {title}")
    return sorted(results)


CANNED_CYPHER_RULES_GOVERNING_APP = """
MATCH (a:Application {name: $app_name})-[:GOVERNED_BY]->(r:Rule)
RETURN r.source AS source, r.title AS title
"""


# ---------------------------------------------------------------------------
# 5. What ADR/Document documents this Application?
# ---------------------------------------------------------------------------


def offline_docs_for_app(graph: schema.Graph, app_name: str) -> list[str]:
    app_id = schema.application_id(app_name)
    if app_id not in graph.nodes:
        return []
    results = []
    for e in _edges_from(graph, app_id, schema.REL_DOCUMENTED_BY):
        doc = graph.nodes[e.target_id]
        results.append(f"{doc.properties.get('source')} :: {doc.properties.get('title', doc.properties.get('adr', ''))}")
    return sorted(results)


CANNED_CYPHER_DOCS_FOR_APP = """
MATCH (a:Application {name: $app_name})-[:DOCUMENTED_BY]->(d:Document)
RETURN d.source AS source, d.title AS title
"""


# ---------------------------------------------------------------------------
# 6. What FK relationships does this Model have?
# ---------------------------------------------------------------------------


def offline_fk_relationships(graph: schema.Graph, model_name: str) -> list[str]:
    model_node = _node_by_name(graph, schema.NODE_MODEL, model_name)
    if model_node is None:
        return []
    results = []
    for e in _edges_from(graph, model_node.id, schema.REL_HAS_FIELD):
        field = graph.nodes[e.target_id]
        for ref_edge in _edges_from(graph, field.id, schema.REL_REFERENCES):
            target = graph.nodes[ref_edge.target_id]
            external = " (external stub)" if target.properties.get("external") else ""
            results.append(f"{field.properties.get('name')} -> {target.properties.get('app_label')}.{target.properties.get('name')}{external}")
    return sorted(results)


CANNED_CYPHER_FK_RELATIONSHIPS = """
MATCH (m:Model {name: $model_name})-[:HAS_FIELD]->(f:Field)-[:REFERENCES]->(target:Model)
RETURN f.name AS field, target.app_label AS target_app, target.name AS target_model, target.external AS is_external_stub
"""


# ---------------------------------------------------------------------------
# 7. What tests cover this node?
# ---------------------------------------------------------------------------


def offline_tests_for(graph: schema.Graph, label: str, name: str) -> list[str]:
    node = _node_by_name(graph, label, name)
    if node is None:
        return []
    return sorted(
        graph.nodes[e.target_id].properties.get("path", e.target_id)
        for e in _edges_from(graph, node.id, schema.REL_TESTED_BY)
    )


CANNED_CYPHER_TESTS_FOR = """
MATCH (n {name: $name})-[:TESTED_BY]->(t:Test)
RETURN t.path AS test_path
"""


CANNED_CYPHER = {
    "viewsets_using_serializer": CANNED_CYPHER_VIEWSETS_USING_SERIALIZER,
    "js_consuming_endpoint": CANNED_CYPHER_JS_CONSUMING_ENDPOINT,
    "endpoints_for_model": CANNED_CYPHER_ENDPOINTS_FOR_MODEL,
    "rules_governing_app": CANNED_CYPHER_RULES_GOVERNING_APP,
    "docs_for_app": CANNED_CYPHER_DOCS_FOR_APP,
    "fk_relationships": CANNED_CYPHER_FK_RELATIONSHIPS,
    "tests_for": CANNED_CYPHER_TESTS_FOR,
}


def run_demo(graph: schema.Graph, app_name: str) -> None:
    print(f"== EKG demo queries for app={app_name} ==\n")

    print("Q: What ViewSet uses OrdenCompraListSerializer?")
    for r in offline_viewsets_using_serializer(graph, "OrdenCompraListSerializer"):
        print(" -", r)

    print("\nQ: What JS consumes an endpoint containing 'plantillas'?")
    for r in offline_js_consuming_endpoint_route(graph, "plantillas"):
        print(" -", r)

    print("\nQ: What endpoints expose the OrdenCompra model?")
    for r in offline_endpoints_for_model(graph, "OrdenCompra"):
        print(" -", r)

    print(f"\nQ: What AGENTS.md/skill rules govern {app_name}?")
    for r in offline_rules_governing_app(graph, app_name):
        print(" -", r)

    print(f"\nQ: What ADRs/docs document {app_name}?")
    for r in offline_docs_for_app(graph, app_name):
        print(" -", r)

    print("\nQ: What FK relationships does OrdenCompra have?")
    for r in offline_fk_relationships(graph, "OrdenCompra"):
        print(" -", r)

    print("\nQ: What tests cover OrdenCompraBusinessService?")
    for r in offline_tests_for(graph, schema.NODE_SERVICE, "OrdenCompraBusinessService"):
        print(" -", r)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run canned EKG questions.")
    parser.add_argument("--offline", default=None, help="Path to a dry-run JSON graph (default tools/ekg/out/<app>.json)")
    parser.add_argument("--app", default="compras")
    parser.add_argument("--live", action="store_true", help="List canned Cypher instead (requires Neo4j, not run here)")
    args = parser.parse_args()

    if args.live:
        for key, cypher in CANNED_CYPHER.items():
            print(f"-- {key} --{cypher}")
        return

    graph_path = Path(args.offline) if args.offline else PROJECT_ROOT / "tools" / "ekg" / "out" / f"{args.app}.json"
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    graph = schema.graph_from_jsonable(data)
    run_demo(graph, args.app)


if __name__ == "__main__":
    main()
