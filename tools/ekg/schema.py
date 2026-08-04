"""
Enterprise Knowledge Graph (EKG) - graph vocabulary (SSoT).

This is the single source of truth for every node label and relationship
type the EKG pipeline can emit. Extractors must only use labels/relationship
types defined here - do not invent new ones inline in an extractor module.

Scope note: this is a deliberately narrow subset of the full 20-phase EKG
spec, scoped to what the apps/tenant/compras pilot can actually extract
today. See tools/ekg/PILOT_REPORT.md for what is NOT covered yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Node labels
# ---------------------------------------------------------------------------

NODE_PROJECT = "Project"
NODE_APPLICATION = "Application"
NODE_MODEL = "Model"
NODE_FIELD = "Field"
NODE_SERVICE = "Service"
NODE_VIEWSET = "ViewSet"
NODE_SERIALIZER = "Serializer"
NODE_ENDPOINT = "Endpoint"
NODE_TEMPLATE = "Template"
NODE_JS = "JS"
NODE_RULE = "Rule"
NODE_DOCUMENT = "Document"
NODE_TEST = "Test"
NODE_SETTING = "Setting"
NODE_DOCKER = "Docker"

NODE_LABELS = frozenset(
    {
        NODE_PROJECT,
        NODE_APPLICATION,
        NODE_MODEL,
        NODE_FIELD,
        NODE_SERVICE,
        NODE_VIEWSET,
        NODE_SERIALIZER,
        NODE_ENDPOINT,
        NODE_TEMPLATE,
        NODE_JS,
        NODE_RULE,
        NODE_DOCUMENT,
        NODE_TEST,
        NODE_SETTING,
        NODE_DOCKER,
    }
)

# Service.kind values (Service is a single label with a "kind" property,
# not four separate labels, so a "what services exist" query stays simple)
SERVICE_KIND_SELECTOR = "selector"
SERVICE_KIND_CRUD = "crud"
SERVICE_KIND_BUSINESS = "business"
SERVICE_KIND_MIXIN = "mixin"
# Apps that outgrew the flat FSD services/ layout (e.g. facturas/services/dian/)
# park their non-FSD helper modules here rather than mis-tagging them as one
# of the four real layers above.
SERVICE_KIND_OTHER = "other"

SERVICE_KINDS = frozenset(
    {
        SERVICE_KIND_SELECTOR,
        SERVICE_KIND_CRUD,
        SERVICE_KIND_BUSINESS,
        SERVICE_KIND_MIXIN,
        SERVICE_KIND_OTHER,
    }
)

# ViewSet.kind values - api/ can also hold plain DRF APIViews and
# composition mixins alongside real ViewSets (e.g. facturas/api/mixins/,
# facturas/api/views_mail_ingestion.py); all three still live on the
# ViewSet label so "what's in this app's API layer" stays a single query.
VIEWSET_KIND_VIEWSET = "viewset"
VIEWSET_KIND_MIXIN = "mixin"
VIEWSET_KIND_VIEW = "view"

VIEWSET_KINDS = frozenset({VIEWSET_KIND_VIEWSET, VIEWSET_KIND_MIXIN, VIEWSET_KIND_VIEW})


# ---------------------------------------------------------------------------
# Relationship types
# ---------------------------------------------------------------------------

REL_IMPORTS = "IMPORTS"
REL_INHERITS = "INHERITS"
REL_HAS_FIELD = "HAS_FIELD"
REL_REFERENCES = "REFERENCES"
REL_EXPOSES = "EXPOSES"
REL_USES = "USES"
REL_CALLS = "CALLS"
REL_CONSUMES = "CONSUMES"
REL_RENDERS = "RENDERS"
REL_BELONGS_TO = "BELONGS_TO"
REL_DOCUMENTED_BY = "DOCUMENTED_BY"
REL_GOVERNED_BY = "GOVERNED_BY"
REL_TESTED_BY = "TESTED_BY"
REL_SSOT_OF = "SSOT_OF"
REL_DEPENDS_ON = "DEPENDS_ON"

REL_TYPES = frozenset(
    {
        REL_IMPORTS,
        REL_INHERITS,
        REL_HAS_FIELD,
        REL_REFERENCES,
        REL_EXPOSES,
        REL_USES,
        REL_CALLS,
        REL_CONSUMES,
        REL_RENDERS,
        REL_BELONGS_TO,
        REL_DOCUMENTED_BY,
        REL_GOVERNED_BY,
        REL_TESTED_BY,
        REL_SSOT_OF,
        REL_DEPENDS_ON,
    }
)


# ---------------------------------------------------------------------------
# In-memory graph primitives
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Node:
    """A single EKG node. `id` must be globally unique and deterministic
    (same input always yields the same id) so the Neo4j loader can MERGE
    idempotently instead of duplicating nodes on re-runs."""

    id: str
    label: str
    properties: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.label not in NODE_LABELS:
            raise ValueError(f"Unknown node label: {self.label!r}")


@dataclass(frozen=True)
class Edge:
    source_id: str
    target_id: str
    rel_type: str
    properties: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.rel_type not in REL_TYPES:
            raise ValueError(f"Unknown relationship type: {self.rel_type!r}")


@dataclass
class Graph:
    """In-memory accumulator used by every extractor. Nodes/edges are kept
    in dicts keyed by id so re-adding the same node (e.g. a Model referenced
    from two different files) is a no-op merge, not a duplicate."""

    nodes: dict = field(default_factory=dict)
    edges: list = field(default_factory=list)

    def add_node(self, node: Node) -> Node:
        existing = self.nodes.get(node.id)
        if existing is None:
            self.nodes[node.id] = node
            return node
        merged_props = {**existing.properties, **node.properties}
        if existing.properties.get("external") is False:
            # "external" is monotonic: once a node has been resolved for
            # real (some app's own extraction produced it, external=False),
            # a later merge of a *different* app's independently-built
            # stub view of the same target (external=True, because that
            # app doesn't know the target has since been extracted for
            # real) must not downgrade it back to a stub. Found via the
            # rollout: gastos' own `proveedor` FK creates its own
            # tenant_proveedores.Proveedor stub, and merging gastos after
            # proveedores was silently flipping the already-resolved real
            # node back to external=True. See PILOT_REPORT.md spot-check #8.
            merged_props["external"] = False
        merged = Node(id=node.id, label=node.label, properties=merged_props)
        self.nodes[node.id] = merged
        return merged

    def add_edge(self, edge: Edge) -> Edge:
        # de-dupe identical edges (same source/target/type) across extractors
        for existing in self.edges:
            if (
                existing.source_id == edge.source_id
                and existing.target_id == edge.target_id
                and existing.rel_type == edge.rel_type
            ):
                return existing
        self.edges.append(edge)
        return edge

    def merge(self, other: Graph) -> None:
        for node in other.nodes.values():
            self.add_node(node)
        for edge in other.edges:
            self.add_edge(edge)

    def node_count(self) -> int:
        return len(self.nodes)

    def edge_count(self) -> int:
        return len(self.edges)


# ---------------------------------------------------------------------------
# Deterministic id helpers (used by every extractor, kept here so the id
# convention is defined in exactly one place)
# ---------------------------------------------------------------------------


def application_id(app_name: str) -> str:
    return f"Application:{app_name}"


def model_id(app_name: str, class_name: str) -> str:
    return f"Model:{app_name}.{class_name}"


def field_id(app_name: str, class_name: str, field_name: str) -> str:
    return f"Field:{app_name}.{class_name}.{field_name}"


def service_id(app_name: str, module_name: str, class_name: str) -> str:
    return f"Service:{app_name}.{module_name}.{class_name}"


def viewset_id(app_name: str, class_name: str) -> str:
    return f"ViewSet:{app_name}.{class_name}"


def serializer_id(app_name: str, class_name: str) -> str:
    return f"Serializer:{app_name}.{class_name}"


def endpoint_id(app_name: str, route: str, method_group: str = "") -> str:
    suffix = f":{method_group}" if method_group else ""
    return f"Endpoint:{app_name}:{route}{suffix}"


def template_id(relative_path: str) -> str:
    return f"Template:{relative_path}"


def js_id(relative_path: str) -> str:
    return f"JS:{relative_path}"


def rule_id(source: str, anchor: str) -> str:
    return f"Rule:{source}#{anchor}"


def document_id(relative_path: str, anchor: str = "") -> str:
    suffix = f"#{anchor}" if anchor else ""
    return f"Document:{relative_path}{suffix}"


def test_id(relative_path: str, test_name: str = "") -> str:
    suffix = f"::{test_name}" if test_name else ""
    return f"Test:{relative_path}{suffix}"


def setting_id(name: str) -> str:
    return f"Setting:{name}"


def docker_service_id(name: str) -> str:
    return f"Docker:{name}"


# ---------------------------------------------------------------------------
# JSON (de)serialization - used by the dry-run path in build_graph.py and by
# queries.py's --offline mode, so a Graph can round-trip without a live
# Neo4j connection.
# ---------------------------------------------------------------------------


def graph_to_jsonable(graph: Graph) -> dict:
    return {
        "nodes": [
            {"id": n.id, "label": n.label, "properties": n.properties} for n in graph.nodes.values()
        ],
        "edges": [
            {
                "source_id": e.source_id,
                "target_id": e.target_id,
                "rel_type": e.rel_type,
                "properties": e.properties,
            }
            for e in graph.edges
        ],
    }


def graph_from_jsonable(data: dict) -> Graph:
    graph = Graph()
    for n in data.get("nodes", []):
        graph.add_node(Node(id=n["id"], label=n["label"], properties=n.get("properties", {})))
    for e in data.get("edges", []):
        graph.add_edge(
            Edge(
                source_id=e["source_id"],
                target_id=e["target_id"],
                rel_type=e["rel_type"],
                properties=e.get("properties", {}),
            )
        )
    return graph
