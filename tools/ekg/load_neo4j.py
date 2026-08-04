"""
EKG loader: writes an in-memory tools.ekg.schema.Graph into Neo4j
idempotently (MERGE, never CREATE), so re-running the pipeline after a code
change updates the graph in place instead of duplicating nodes/edges.

Every Node.id already embeds its label (see schema.py id helpers, e.g.
"Model:compras.OrdenCompra"), so it is safe to MATCH/MERGE purely on the
`id` property without also constraining by label - ids cannot collide
across labels by construction.

This module requires a reachable Neo4j instance (NEO4J_URI/NEO4J_USER/
NEO4J_PASSWORD env vars) - see tools/ekg/PILOT_REPORT.md for why that could
not be exercised end-to-end in the environment this pilot was built in, and
run `python -m tools.ekg.build_graph --app <name> --dry-run` first if you
want to inspect the graph before touching a live database.
"""

from __future__ import annotations

import os

from neo4j import GraphDatabase

from tools.ekg import schema

BATCH_SIZE = 500


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"{name} must be set (see .env.example)")
    return value


class Neo4jLoader:
    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None):
        self._uri = uri or _env("NEO4J_URI", "bolt://localhost:7687")
        self._user = user or _env("NEO4J_USER", "neo4j")
        self._password = password or _env("NEO4J_PASSWORD")
        self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> Neo4jLoader:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def ensure_constraints(self) -> None:
        with self._driver.session() as session:
            for label in sorted(schema.NODE_LABELS):
                session.run(
                    f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE"
                )

    def load_graph(self, graph: schema.Graph) -> None:
        self.ensure_constraints()
        nodes = list(graph.nodes.values())
        with self._driver.session() as session:
            for i in range(0, len(nodes), BATCH_SIZE):
                session.execute_write(_write_nodes_batch, nodes[i : i + BATCH_SIZE])
            for i in range(0, len(graph.edges), BATCH_SIZE):
                session.execute_write(_write_edges_batch, graph.edges[i : i + BATCH_SIZE])


def _write_nodes_batch(tx, nodes: list[schema.Node]) -> None:
    by_label: dict[str, list[dict]] = {}
    for node in nodes:
        by_label.setdefault(node.label, []).append({"id": node.id, "props": node.properties})
    for label, rows in by_label.items():
        tx.run(
            f"""
            UNWIND $rows AS row
            MERGE (n:{label} {{id: row.id}})
            WITH n, row, n.external AS old_external
            SET n += row.props
            SET n.external = CASE
                WHEN old_external = false THEN false
                ELSE row.props.external
            END
            """,
            # `external` is monotonic across separately-loaded apps (see
            # schema.Graph.add_node's docstring for the concrete bug this
            # closes): capture the node's external value BEFORE the blind
            # `SET n += row.props`, then never let a later app's stub view
            # (external=true) downgrade a node another app already
            # resolved for real (external=false). Not exercised against a
            # live Neo4j in this environment - see PILOT_REPORT.md.
            rows=rows,
        )


def _write_edges_batch(tx, edges: list[schema.Edge]) -> None:
    by_type: dict[str, list[dict]] = {}
    for edge in edges:
        by_type.setdefault(edge.rel_type, []).append(
            {"source_id": edge.source_id, "target_id": edge.target_id, "props": edge.properties}
        )
    for rel_type, rows in by_type.items():
        tx.run(
            f"""
            UNWIND $rows AS row
            MATCH (a {{id: row.source_id}})
            MATCH (b {{id: row.target_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r += row.props
            """,
            rows=rows,
        )


def load(app_name: str, graph: schema.Graph) -> None:
    with Neo4jLoader() as loader:
        loader.load_graph(graph)
    print(f"Loaded {graph.node_count()} nodes and {graph.edge_count()} edges for app={app_name}")
