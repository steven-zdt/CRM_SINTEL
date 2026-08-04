"""
EKG pipeline orchestrator: runs every extractor for a given app, merges the
results into one Graph, links JS endpoint literals to the router/path
Endpoint nodes extracted from Python, and either loads the graph into Neo4j
or dumps it to disk for inspection.

Usage:
    python -m tools.ekg.build_graph --app compras
    python -m tools.ekg.build_graph --app compras --dry-run --output tools/ekg/out/compras.json

See tools/ekg/PILOT_REPORT.md for scope and current limitations.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.ekg import schema
from tools.ekg.extract_docs import (
    extract_adr_docs,
    extract_agents_md,
    extract_app_audit_doc,
    extract_memory_md,
    extract_skills,
)
from tools.ekg.extract_infra import extract_docker_compose
from tools.ekg.extract_js import extract_app_js
from tools.ekg.extract_python import extract_app_python
from tools.ekg.extract_templates import extract_app_templates

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def build_app_graph(app_name: str, project_root: Path = PROJECT_ROOT) -> schema.Graph:
    graph = schema.Graph()

    graph.merge(extract_app_python(app_name, project_root))
    graph.merge(extract_app_js(app_name, project_root))
    graph.merge(extract_app_templates(app_name, project_root))
    graph.merge(extract_docker_compose(project_root))
    graph.merge(extract_agents_md(project_root, [app_name]))
    graph.merge(extract_memory_md(project_root, [app_name]))
    graph.merge(extract_adr_docs(project_root, [app_name]))
    graph.merge(extract_skills(project_root, [app_name]))
    graph.merge(extract_app_audit_doc(app_name, project_root))

    _link_js_literals_to_router_endpoints(graph, app_name)

    return graph


def _link_js_literals_to_router_endpoints(graph: schema.Graph, app_name: str) -> None:
    """Best-effort second pass (documented in extract_js.py): if a JS
    endpoint literal's route text contains a router/path Endpoint's route as
    a substring, add a direct CONSUMES edge from the JS file to that real
    Endpoint node too, in addition to the js-literal stub it already has."""
    router_endpoints = [
        (node_id, node.properties.get("route", ""))
        for node_id, node in graph.nodes.items()
        if node.label == schema.NODE_ENDPOINT and node.properties.get("kind") in ("router", "path")
    ]
    js_literal_endpoints = [
        (node_id, node.properties.get("route", ""))
        for node_id, node in graph.nodes.items()
        if node.label == schema.NODE_ENDPOINT and node.properties.get("kind") == "js-literal"
    ]
    consumes_by_target: dict[str, list[str]] = {}
    for edge in graph.edges:
        if edge.rel_type == schema.REL_CONSUMES:
            consumes_by_target.setdefault(edge.target_id, []).append(edge.source_id)

    for literal_id, literal_route in js_literal_endpoints:
        js_source_ids = consumes_by_target.get(literal_id, [])
        for router_id, router_route in router_endpoints:
            if not router_route:
                continue
            if f"/{router_route}" in literal_route or literal_route.endswith(f"{router_route}/"):
                for js_source_id in js_source_ids:
                    graph.add_edge(schema.Edge(js_source_id, router_id, schema.REL_CONSUMES))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build (and optionally load) the EKG for one app.")
    parser.add_argument("--app", required=True, help="Tenant app name, e.g. compras")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Neo4j")
    parser.add_argument("--output", default=None, help="Dry-run output path (JSON)")
    args = parser.parse_args()

    graph = build_app_graph(args.app)
    print(f"Extracted {graph.node_count()} nodes and {graph.edge_count()} edges for app={args.app}")

    if args.dry_run:
        output_path = Path(args.output) if args.output else PROJECT_ROOT / "tools" / "ekg" / "out" / f"{args.app}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(schema.graph_to_jsonable(graph), indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Dry-run graph written to {output_path}")
        return

    from tools.ekg.load_neo4j import load

    load(args.app, graph)


if __name__ == "__main__":
    main()
