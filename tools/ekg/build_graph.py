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


def build_app_graph(
    app_name: str,
    project_root: Path = PROJECT_ROOT,
    schema_root: str = "tenant",
    folder_name: str | None = None,
) -> schema.Graph:
    """`app_name` is the id-namespace for every node this builds (see
    extract_python.py's extract_app_python() docstring for why it can
    differ from the on-disk `folder_name` - apps/tenant/<x> and
    apps/public/<x> can share a bare folder name for two entirely
    unrelated apps, e.g. both have a "core"). Template extraction is
    skipped for schema_root != "tenant": apps/public/* templates don't
    follow a uniform templates/<app>/ convention the way apps/tenant/*
    does (see documentacion/arquitectura_general.md Sec 5.2 vs. what's
    actually on disk under apps/public/tenants/templates/, which is
    templates/emails/ and templates/public/, not templates/tenants/) -
    forcing the tenant-shaped extractor onto it would produce silently
    wrong data rather than an honest empty result."""
    graph = schema.Graph()
    folder = folder_name or app_name

    graph.merge(extract_app_python(app_name, project_root, schema_root, folder))
    graph.merge(extract_app_js(app_name, project_root, schema_root, folder))
    if schema_root == "tenant":
        graph.merge(extract_app_templates(app_name, project_root))
    graph.merge(extract_docker_compose(project_root))
    # NOTE: text-matched against the namespaced app_name, not the bare
    # folder - AGENTS.md/MEMORY.md/skills never literally say "public_core",
    # so for apps/public/* this heuristic honestly finds nothing rather than
    # colliding: searching for the bare folder ("core") would incorrectly
    # attach apps/tenant/core's matches to Application:core, corrupting
    # both apps' GOVERNED_BY/DOCUMENTED_BY data the moment they're merged
    # together (apps/tenant/core and apps/public/core are two different,
    # unrelated apps that happen to share a bare folder name - see
    # extract_app_python()'s docstring). A real gap for public apps, not
    # papered over - see PILOT_REPORT.md.
    graph.merge(extract_agents_md(project_root, [app_name]))
    graph.merge(extract_memory_md(project_root, [app_name]))
    graph.merge(extract_adr_docs(project_root, [app_name]))
    graph.merge(extract_skills(project_root, [app_name]))
    graph.merge(extract_app_audit_doc(app_name, project_root, schema_root, folder))

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
    parser.add_argument("--app", required=True, help="On-disk folder name, e.g. compras, or core (with --schema public)")
    parser.add_argument("--schema", default="tenant", choices=("tenant", "public"), help="apps/tenant/<app> vs apps/public/<app>")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Neo4j")
    parser.add_argument("--output", default=None, help="Dry-run output path (JSON)")
    args = parser.parse_args()

    # Public apps are extracted under a namespaced app_name (public_<app>)
    # to avoid id collisions with a tenant app that happens to share the
    # same bare folder name (e.g. both schemas have a "core") - see
    # build_app_graph()'s docstring.
    app_name = f"public_{args.app}" if args.schema == "public" else args.app
    graph = build_app_graph(app_name, PROJECT_ROOT, schema_root=args.schema, folder_name=args.app)
    print(f"Extracted {graph.node_count()} nodes and {graph.edge_count()} edges for app={app_name} (schema={args.schema})")
    args.app = app_name

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
