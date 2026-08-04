"""
EKG validation - a pilot-scoped slice of the spec's Fase 17 checklist.

Runs against the dry-run JSON graph (the same data that would be loaded
into Neo4j), not against a live database - validating before load is what
actually prevents bad data from reaching the graph, and this pilot has no
live Neo4j to pull from anyway (see tools/ekg/PILOT_REPORT.md).

Implemented checks:
  - orphan nodes (zero edges, and not a documented "external stub")
  - dangling edges (endpoint id not present in the node set)
  - Endpoint nodes with no ViewSet EXPOSES-ing them (router/path kinds only;
    js-literal endpoints are expected to stand alone, see extract_js.py)
  - ViewSet/Model/Service nodes with no reachable Test

Deliberately NOT implemented (would require semantic/control-flow analysis
this pilot's static extractors don't do - see PILOT_REPORT.md rather than
have this script silently claim a check it cannot back up):
  - "service does not perform DSV" detection
  - Service-Layer-violation detection (logic leaking into ViewSets/Models)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.ekg import schema

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def find_orphan_nodes(graph: schema.Graph) -> list[str]:
    connected: set[str] = set()
    for e in graph.edges:
        connected.add(e.source_id)
        connected.add(e.target_id)
    orphans = []
    for node_id, node in graph.nodes.items():
        if node_id in connected:
            continue
        if node.properties.get("external"):
            continue
        orphans.append(node_id)
    return sorted(orphans)


def find_dangling_edges(graph: schema.Graph) -> list[str]:
    dangling = []
    for e in graph.edges:
        if e.source_id not in graph.nodes:
            dangling.append(f"{e.rel_type}: missing source {e.source_id!r} (-> {e.target_id})")
        if e.target_id not in graph.nodes:
            dangling.append(f"{e.rel_type}: missing target {e.target_id!r} ({e.source_id} ->)")
    return dangling


def find_unexposed_endpoints(graph: schema.Graph) -> list[str]:
    exposed_target_ids = {e.target_id for e in graph.edges if e.rel_type == schema.REL_EXPOSES}
    missing = []
    for node_id, node in graph.nodes.items():
        if node.label != schema.NODE_ENDPOINT:
            continue
        if node.properties.get("kind") == "js-literal":
            continue
        if node_id not in exposed_target_ids:
            missing.append(f"{node_id} (route={node.properties.get('route')!r})")
    return sorted(missing)


def find_untested_nodes(graph: schema.Graph, labels: tuple[str, ...]) -> list[str]:
    tested_source_ids = {e.source_id for e in graph.edges if e.rel_type == schema.REL_TESTED_BY}
    untested = []
    for node_id, node in graph.nodes.items():
        if node.label not in labels:
            continue
        if node.properties.get("external"):
            continue
        if node_id not in tested_source_ids:
            untested.append(f"{node_id} ({node.label})")
    return sorted(untested)


def run(graph: schema.Graph) -> int:
    checks = {
        "orphan_nodes": find_orphan_nodes(graph),
        "dangling_edges": find_dangling_edges(graph),
        "unexposed_endpoints": find_unexposed_endpoints(graph),
        "untested_viewsets_models_services": find_untested_nodes(
            graph, (schema.NODE_VIEWSET, schema.NODE_MODEL, schema.NODE_SERVICE)
        ),
    }

    print(f"EKG validation: {graph.node_count()} nodes, {graph.edge_count()} edges\n")
    hard_failures = 0
    for name, issues in checks.items():
        is_hard_failure = name in ("dangling_edges",)
        status = "FAIL" if issues and is_hard_failure else ("WARN" if issues else "OK")
        print(f"[{status}] {name}: {len(issues)}")
        for issue in issues:
            print(f"    - {issue}")
        if is_hard_failure:
            hard_failures += len(issues)

    return 1 if hard_failures else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an EKG dry-run graph.")
    parser.add_argument("--app", default="compras")
    parser.add_argument("--graph", default=None, help="Path to dry-run JSON (default tools/ekg/out/<app>.json)")
    args = parser.parse_args()

    graph_path = Path(args.graph) if args.graph else PROJECT_ROOT / "tools" / "ekg" / "out" / f"{args.app}.json"
    if not graph_path.exists():
        print(f"No dry-run graph at {graph_path}. Run: python -m tools.ekg.build_graph --app {args.app} --dry-run")
        sys.exit(2)

    data = json.loads(graph_path.read_text(encoding="utf-8"))
    graph = schema.graph_from_jsonable(data)
    sys.exit(run(graph))


if __name__ == "__main__":
    main()
