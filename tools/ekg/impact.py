"""
EKG impact engine - "if I change this, what breaks?"

Given a starting node (by exact name, optionally disambiguated by label, or
by a substring of a file path/route), walks the graph to answer the
questions from the governance spec that are actually answerable with the
edges the pilot extractors populate today:

  - Que modulos/servicios/ViewSets/JS dependen de este componente
    (reverse walk over IMPORTS/INHERITS/USES/CALLS/CONSUMES/REFERENCES -
    "reverse" because e.g. `ViewSet -[USES]-> Serializer` means the ViewSet
    depends on the Serializer, so the dependent is the *source* of the edge).
  - Que Endpoints/Templates produce los nodos impactados (forward walk over
    EXPOSES/RENDERS starting from every node found impacted so far - if a
    ViewSet is impacted, the Endpoint it EXPOSES is impacted too).
  - Que pruebas ya cubren el nodo de partida o cualquier nodo impactado
    (TESTED_BY, forward from each impacted node).
  - Que Aplicaciones se tocan y, a traves de ellas, que Reglas (AGENTS.md /
    skills) y Documentos (ADRs / auditorias .agent/) revisar
    (BELONGS_TO -> Application -> GOVERNED_BY / DOCUMENTED_BY).

Known, deliberate limitation (see tools/ekg/PILOT_REPORT.md roadmap):
GOVERNED_BY/DOCUMENTED_BY are only populated at Application granularity
today, not per Model/Service/ViewSet/etc. - so "docs to review" is always
reported at the app level, never pinpointed to a single rule/ADR paragraph.
This engine reports that limitation explicitly rather than pretending to a
precision the graph does not have (see AGENTS.md: never invent, always
traceable to a real file).

Known gap, found while verifying this engine for the OCF project (Fase 12,
2026-08-08), NOT fixed here: a class that is BOTH (a) defined under
apps/tenant/<app>/services/ of an app this pilot extracts for real AND (b)
inherited as a base class by a ViewSet in a DIFFERENT app gets two
disconnected node identities that never merge -
`Service:<app>.<module>.<ClassName>` (from extract_services(), the real
extraction of where it's defined) and `ViewSet:<app>.<ClassName>` (an
external stub created by extract_viewsets()'s cross-app INHERITS resolver,
which only ever guesses "ViewSet family" for a cross-app base it can't
resolve from its own app's maps - see extract_python.py's
_resolve_cross_app_base_folder(), which discards the module-name segment
of the import path it would need to build the correct Service id instead).
Confirmed concretely: `python -m tools.ekg.impact --offline --name
OrganizationalContextMixin` returns "Multiple matches" ([ViewSet] and
[Service]) - querying the Service-labeled one shows only its own CALLS/USES
edges and misses every one of the 42 ViewSets that actually inherit it
(Fase 9 of OCF); only `--label ViewSet` reaches them, because that's the id
every real INHERITS edge actually points at. Root cause was BaseTenantViewSet/
SintelDSVMixin never triggering this (they live in apps/tenant/api/, an
"infrastructure" app never separately extracted, so no colliding real node
ever exists) - OrganizationalContextMixin is the first cross-app mixin
pattern in this codebase where the defining app IS also a pilot app,
exposing a resolver gap that was latent, not present, before. Not fixed:
correctly resolving this in general means extract_viewsets() would need to
check, before minting a ViewSet stub, whether a real Service node for that
exact (app, module, name) already exists in the merge scope - a real but
moderate-risk change to the most heavily-tested part of the pipeline
(extract_python.py's pass-2 INHERITS resolution, exercised by dozens of
tests in tools/ekg/tests/test_extract_python.py), for a UX/precision
inconvenience with a working manual workaround (pass --label, or check
both), not a data-integrity bug. Left for a future, dedicated pass rather
than folded into Fase 12's verification scope.

Two implementations, matching every other module in tools/ekg/:
  - `impact_of_offline` walks an in-memory schema.Graph (works with the
    dry-run JSON dumps under tools/ekg/out/, no Neo4j needed);
  - `impact_of_live` runs the Cypher equivalent against a real Neo4j
    instance (confirmed reachable and loaded - 2506 nodes / 3730 edges -
    2026-08-07, see documentacion/REMEDIACION_FASES2-8_AUDITORIA_ENTERPRISE.md).

Usage:
    python -m tools.ekg.impact --offline --name OrdenCompra
    python -m tools.ekg.impact --offline --name OrdenCompra --label Model
    python -m tools.ekg.impact --offline --path "cuenta_editor.js"
    python -m tools.ekg.impact --live --name CuentaContableViewSet --json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

from tools.ekg import schema

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "tools" / "ekg" / "out"

# The 17 real per-app dry-run dumps (tools/ekg/out/ also holds audit_*.json
# scratch files from the dead-code audit - those are query *results*, not
# extractor dumps, and must never be merged back in as if they were graph
# input, or nodes/edges would be double-counted against the wrong source).
PILOT_APPS = (
    "bancos", "clientes", "compras", "contabilidad", "core", "cotizaciones",
    "dashboard", "empleados", "empresa", "facturas", "gastos", "inventario",
    "landing", "perfil", "proveedores", "proyectos", "ventas",
)

# Extracted with the app_name/folder_name split (see build_graph.py's
# build_app_graph() docstring): apps/public/core and apps/tenant/core are
# two different, unrelated apps that happen to share a bare folder name, so
# the public ones are namespaced "public_<folder>" everywhere - the dump
# filenames match (tools/ekg/out/public_core.json, not core.json again).
PUBLIC_APPS = ("public_accounts", "public_tenants", "public_impuestos", "public_console", "public_core")

# "A -[REL]-> B" means A depends on B for these relation types, so the
# dependents of B are the *sources* of edges targeting B (a reverse walk).
REVERSE_DEP_RELS = frozenset(
    {
        schema.REL_IMPORTS,
        schema.REL_INHERITS,
        schema.REL_USES,
        schema.REL_CALLS,
        schema.REL_CONSUMES,
        schema.REL_REFERENCES,
    }
)

# "A -[REL]-> B" means A produces/owns B for these relation types, so if A is
# impacted, B is impacted too - forward walk starting from every newly
# impacted node.
FORWARD_PRODUCES_RELS = frozenset({schema.REL_EXPOSES, schema.REL_RENDERS})


def _display_name(node: schema.Node) -> str:
    """Node kinds identified by class name (Model/Service/ViewSet/...) carry
    a `name` property; kinds identified by file (Template/JS/Test/Document)
    carry `path`; Endpoint carries `route` (often "" for the API root, which
    is itself meaningful - not missing data). Falls back to the node's
    deterministic id, which is always readable (e.g. "Endpoint:compras:/:api"),
    rather than ever printing a bare None."""
    props = node.properties
    return props.get("name") or props.get("path") or props.get("route") or node.id


@dataclass
class ImpactHit:
    node_id: str
    label: str
    name: str
    hop: int
    via_rel: str
    from_node_id: str


@dataclass
class ImpactReport:
    target_id: str
    target_label: str
    target_name: str
    max_hops: int
    hits: list[ImpactHit] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    apps_touched: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    docs: list[str] = field(default_factory=list)
    truncated: bool = False

    def impacted_count(self) -> int:
        return len(self.hits)

    def to_jsonable(self) -> dict:
        return {
            "target": {"id": self.target_id, "label": self.target_label, "name": self.target_name},
            "max_hops": self.max_hops,
            "impacted": [
                {
                    "id": h.node_id, "label": h.label, "name": h.name,
                    "hop": h.hop, "via": h.via_rel, "from": h.from_node_id,
                }
                for h in self.hits
            ],
            "tests_covering_impacted_set": self.tests,
            "applications_touched": self.apps_touched,
            "rules_to_review": self.rules,
            "docs_to_review": self.docs,
            "truncated_at_max_hops": self.truncated,
        }


# ---------------------------------------------------------------------------
# Offline (in-memory graph) implementation
# ---------------------------------------------------------------------------


def load_full_offline_graph(
    out_dir: Path = OUT_DIR, apps: tuple[str, ...] = PILOT_APPS + PUBLIC_APPS
) -> schema.Graph:
    """Merge every real per-app dry-run dump into one graph, so cross-app
    edges (a Field's FK stub resolved by the app that owns the real Model,
    a JS file consuming another app's endpoint) are visible. Uses the same
    Graph.merge()/add_node() the extractors themselves use, so the
    "external is monotonic" invariant (see schema.py) applies here too.
    Defaults to all 17 tenant + 5 public apps (added 2026-08-07, closing
    PILOT_REPORT.md roadmap item 8 - apps/public/* coverage)."""
    graph = schema.Graph()
    missing = []
    for app_name in apps:
        path = out_dir / f"{app_name}.json"
        if not path.exists():
            missing.append(app_name)
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        graph.merge(schema.graph_from_jsonable(data))
    if missing:
        print(f"[impact] WARNING: no dry-run dump for {missing} - graph is incomplete for those apps")
    return graph


def find_nodes_by_name(graph: schema.Graph, name: str, label: str | None = None) -> list[schema.Node]:
    return [
        n for n in graph.nodes.values()
        if n.properties.get("name") == name and (label is None or n.label == label)
    ]


def find_nodes_by_path_fragment(graph: schema.Graph, fragment: str) -> list[schema.Node]:
    """Fallback lookup for node kinds identified by file path/route rather
    than a class name: Template, JS, Test, Document."""
    hits = []
    for n in graph.nodes.values():
        for key in ("path", "route", "source"):
            value = n.properties.get(key)
            if value and fragment in value:
                hits.append(n)
                break
    return hits


def impact_of_offline(graph: schema.Graph, target: schema.Node, max_hops: int = 4) -> ImpactReport:
    report = ImpactReport(
        target_id=target.id,
        target_label=target.label,
        target_name=_display_name(target),
        max_hops=max_hops,
    )

    visited = {target.id}
    frontier = [target.id]
    hop = 0
    while frontier and hop < max_hops:
        hop += 1
        next_frontier: list[str] = []
        for node_id in frontier:
            # Dependents: who points AT node_id via a dependency-style rel.
            for edge in graph.edges:
                if edge.target_id != node_id or edge.rel_type not in REVERSE_DEP_RELS:
                    continue
                if edge.source_id in visited:
                    continue
                visited.add(edge.source_id)
                src = graph.nodes.get(edge.source_id)
                if src is None:
                    continue
                report.hits.append(
                    ImpactHit(
                        node_id=src.id, label=src.label,
                        name=_display_name(src),
                        hop=hop, via_rel=edge.rel_type, from_node_id=node_id,
                    )
                )
                next_frontier.append(src.id)
            # Produced: what node_id itself owns/exposes going forward.
            for edge in graph.edges:
                if edge.source_id != node_id or edge.rel_type not in FORWARD_PRODUCES_RELS:
                    continue
                if edge.target_id in visited:
                    continue
                visited.add(edge.target_id)
                dst = graph.nodes.get(edge.target_id)
                if dst is None:
                    continue
                report.hits.append(
                    ImpactHit(
                        node_id=dst.id, label=dst.label,
                        name=_display_name(dst),
                        hop=hop, via_rel=edge.rel_type, from_node_id=node_id,
                    )
                )
                next_frontier.append(dst.id)
        frontier = next_frontier
    report.truncated = bool(frontier)  # still had unexplored nodes when max_hops ran out

    impacted_ids = visited  # includes the target itself
    tests = set()
    app_ids = set()
    for node_id in impacted_ids:
        for edge in graph.edges:
            if edge.source_id == node_id and edge.rel_type == schema.REL_TESTED_BY:
                test_node = graph.nodes.get(edge.target_id)
                if test_node:
                    tests.add(test_node.properties.get("path", test_node.id))
            if edge.source_id == node_id and edge.rel_type == schema.REL_BELONGS_TO:
                app_ids.add(edge.target_id)
    report.tests = sorted(tests)

    rules = set()
    docs = set()
    for app_id in app_ids:
        app_node = graph.nodes.get(app_id)
        if app_node:
            report.apps_touched.append(app_node.properties.get("name", app_id))
        for edge in graph.edges:
            if edge.source_id != app_id:
                continue
            if edge.rel_type == schema.REL_GOVERNED_BY:
                rule = graph.nodes.get(edge.target_id)
                if rule:
                    rules.add(f"{rule.properties.get('source', '')} :: {rule.properties.get('title', '')}")
            if edge.rel_type == schema.REL_DOCUMENTED_BY:
                doc = graph.nodes.get(edge.target_id)
                if doc:
                    docs.add(f"{doc.properties.get('source', '')} :: {doc.properties.get('title', doc.properties.get('adr', ''))}")
    report.apps_touched = sorted(set(report.apps_touched))
    report.rules = sorted(rules)
    report.docs = sorted(docs)
    return report


# ---------------------------------------------------------------------------
# Live (Neo4j) implementation
# ---------------------------------------------------------------------------

# Neo4j Cypher does not accept a relationship-type list or a variable-length
# hop bound as a query parameter, only as literal pattern syntax - both are
# controlled by this module (REVERSE_DEP_RELS/max_hops), never by user input,
# so inlining them into the query string is safe (no injection surface: the
# only externally-supplied value is $name, passed as a real parameter).
_REVERSE_RELS_PATTERN = "|".join(sorted(REVERSE_DEP_RELS))
_FORWARD_RELS_PATTERN = "|".join(sorted(FORWARD_PRODUCES_RELS))


def _display_expr(var: str) -> str:
    """Cypher equivalent of `_display_name()`: `coalesce()` only skips NULL,
    not empty strings, so two different Endpoint nodes that both have
    route="" (a real, meaningful value - the API root) would render an
    identical {{name: ""}} display map and silently collapse into one
    `collect(DISTINCT ...)` entry. Falls through empty strings too, all the
    way to the node's real id if needed."""
    return (
        f"CASE WHEN {var}.name IS NOT NULL AND {var}.name <> '' THEN {var}.name "
        f"WHEN {var}.path IS NOT NULL AND {var}.path <> '' THEN {var}.path "
        f"WHEN {var}.route IS NOT NULL AND {var}.route <> '' THEN {var}.route "
        f"ELSE {var}.id END"
    )


def build_live_cypher(max_hops: int = 4) -> str:
    """Mirrors impact_of_offline's two-pass walk exactly (see that function's
    docstring): FORWARD_PRODUCES_RELS (EXPOSES/RENDERS) must be walked from
    every node already found impacted by the reverse dependency walk, not
    only from the original target - a ViewSet only becomes impacted via the
    reverse walk, and the Endpoint it EXPOSES is only reachable by then
    walking forward *from that ViewSet*. An earlier version of this query
    only walked forward from `target` itself and silently returned zero
    Endpoints for any Model/Service more than one hop away from its
    ViewSet.

    Every returned map also carries `id` (the node's real, always-unique
    deterministic id - see schema.py) precisely so `collect(DISTINCT ...)`
    dedups by true identity, not by the display string: two different
    Endpoint nodes both have route="" (a real, meaningful value, the API
    root) and would otherwise render an identical display map and silently
    collapse into one entry. Both this and the previous bug were caught by
    comparing --live against --offline on the same real model (compras'
    OrdenCompra) rather than trusting either implementation in isolation -
    see documentacion/REMEDIACION_FASES2-8_AUDITORIA_ENTERPRISE.md."""
    dep_name = _display_expr("dependent")
    prod_name = _display_expr("produced")
    return f"""
MATCH (target {{name: $name}})
OPTIONAL MATCH depPath = (dependent)-[:{_REVERSE_RELS_PATTERN}*1..{max_hops}]->(target)
WITH target,
     [d IN collect(DISTINCT dependent) WHERE d IS NOT NULL] AS dependentNodes,
     [d IN collect(DISTINCT CASE WHEN dependent IS NOT NULL THEN
         {{id: dependent.id, name: {dep_name}, label: labels(dependent)[0], hops: length(depPath)}}
     END) WHERE d IS NOT NULL] AS dependents
WITH target, dependents, dependentNodes + [target] AS impactedSoFar
UNWIND impactedSoFar AS node
OPTIONAL MATCH prodPath = (node)-[:{_FORWARD_RELS_PATTERN}*1..{max_hops}]->(produced)
WITH target, dependents,
     [p IN collect(DISTINCT CASE WHEN produced IS NOT NULL THEN
         {{id: produced.id, name: {prod_name}, label: labels(produced)[0], hops: length(prodPath)}}
     END) WHERE p IS NOT NULL] AS produced,
     collect(DISTINCT node) AS impactedSoFar
UNWIND impactedSoFar AS node2
OPTIONAL MATCH (node2)-[:TESTED_BY]->(test:Test)
WITH target, dependents, produced, collect(DISTINCT test.path) AS testsRaw
WITH target, dependents, produced, [t IN testsRaw WHERE t IS NOT NULL] AS direct_tests
OPTIONAL MATCH (target)-[:BELONGS_TO]->(app:Application)-[:GOVERNED_BY]->(rule:Rule)
WITH target, dependents, produced, direct_tests, collect(DISTINCT rule.title) AS rules
OPTIONAL MATCH (target)-[:BELONGS_TO]->(app2:Application)-[:DOCUMENTED_BY]->(doc:Document)
WITH target, dependents, produced, direct_tests, rules, collect(DISTINCT doc.title) AS docsRaw
RETURN target.name AS target,
       dependents,
       produced,
       direct_tests,
       rules,
       [d IN docsRaw WHERE d IS NOT NULL] AS docs
"""


def impact_of_live(name: str, label: str | None = None, max_hops: int = 4) -> dict:
    from tools.ekg.load_neo4j import _env  # reuse the same env-var contract

    from neo4j import GraphDatabase

    uri = _env("NEO4J_URI", "bolt://localhost:7687")
    user = _env("NEO4J_USER", "neo4j")
    password = _env("NEO4J_PASSWORD")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            cypher = build_live_cypher(max_hops)
            result = session.run(cypher, name=name).single()
            if result is None:
                return {"error": f"No node named {name!r} found in the live graph"}
            return dict(result)
    finally:
        driver.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_report(report: ImpactReport) -> None:
    print(f"== Impact of changing {report.target_label}:{report.target_name} (max {report.max_hops} hops) ==\n")
    if not report.hits:
        print("No dependents/produced nodes found within the hop limit.")
    else:
        by_hop: dict[int, list[ImpactHit]] = {}
        for h in report.hits:
            by_hop.setdefault(h.hop, []).append(h)
        for hop in sorted(by_hop):
            print(f"-- hop {hop} --")
            for h in sorted(by_hop[hop], key=lambda x: (x.label, x.name)):
                print(f"  [{h.label}] {h.name}  (via {h.via_rel} <- hop {hop - 1})")
    print(f"\nTotal impacted (excluding target): {report.impacted_count()}")
    if report.truncated:
        print(f"WARNING: traversal hit max_hops={report.max_hops} with more nodes still unexplored - re-run with a higher --max-hops for full reach.")

    print("\n-- Tests covering target or any impacted node --")
    if report.tests:
        for t in report.tests:
            print(f"  {t}")
    else:
        print("  NONE FOUND - this change has no known automated regression coverage in the graph.")

    print("\n-- Applications touched --")
    for a in report.apps_touched:
        print(f"  {a}")

    print("\n-- Rules to review (AGENTS.md / skills, app-level only - see module docstring) --")
    for r in report.rules:
        print(f"  {r}")

    print("\n-- Docs to review (ADRs / audits, app-level only - see module docstring) --")
    for d in report.docs:
        print(f"  {d}")


def main() -> None:
    parser = argparse.ArgumentParser(description="EKG impact engine: what breaks if I change this node?")
    parser.add_argument("--name", default=None, help="Exact node name (Model/Service/ViewSet/Serializer class name)")
    parser.add_argument("--path", default=None, help="Substring of a file path/route (for Template/JS/Test/Document)")
    parser.add_argument("--label", default=None, help="Disambiguate when --name matches multiple labels")
    parser.add_argument("--max-hops", type=int, default=4)
    parser.add_argument("--offline", action="store_true", help="Merge JSON dumps under tools/ekg/out/ (default mode - this flag is accepted for symmetry with --live and with queries.py)")
    parser.add_argument("--live", action="store_true", help="Query the real Neo4j instance instead of merging JSON dumps")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON instead of a human-readable summary")
    args = parser.parse_args()

    if not args.name and not args.path:
        parser.error("provide --name or --path")

    if args.live:
        if not args.name:
            parser.error("--live currently requires --name (Cypher lookup is by exact name)")
        result = impact_of_live(args.name, label=args.label, max_hops=args.max_hops)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    graph = load_full_offline_graph()
    print(f"[impact] offline graph: {graph.node_count()} nodes, {graph.edge_count()} edges (merged {len(PILOT_APPS)} apps)\n")

    candidates = find_nodes_by_name(graph, args.name, args.label) if args.name else find_nodes_by_path_fragment(graph, args.path)
    if not candidates:
        print("No matching node found. Try --path for Template/JS/Test/Document lookups, or check spelling/--label.")
        return
    if len(candidates) > 1:
        print(f"Multiple matches ({len(candidates)}) - pass --label to disambiguate, or --path for a more specific fragment:")
        for n in candidates:
            print(f"  [{n.label}] {_display_name(n)}")
        return

    report = impact_of_offline(graph, candidates[0], max_hops=args.max_hops)
    if args.json:
        print(json.dumps(report.to_jsonable(), indent=2, ensure_ascii=False))
    else:
        _print_report(report)


if __name__ == "__main__":
    main()
