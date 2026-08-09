"""
Grafo organizacional en memoria (F13.10, F13.13, F13.14) - resolucion de
identidad estable, export JSON, y las queries reproducibles que pide F13.14
y F14.22.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from tools.organizational_governance.schema import NODE_LABELS, REL_TYPES


@dataclass(frozen=True)
class Node:
    """Identidad estable = (label, qualified_id). qualified_id nunca es solo
    el nombre corto (F13.10) - para App/Model/ViewSet es "app_label.NombreClase"
    o "app_label" segun el tipo, nunca ambiguo entre apps distintas."""

    label: str
    qualified_id: str
    props: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.label not in NODE_LABELS:
            raise ValueError(f"Node label desconocido: {self.label!r} (ver schema.NODE_LABELS)")

    @property
    def key(self) -> tuple[str, str]:
        return (self.label, self.qualified_id)


@dataclass(frozen=True)
class Edge:
    rel_type: str
    source: tuple[str, str]
    target: tuple[str, str]
    props: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.rel_type not in REL_TYPES:
            raise ValueError(f"Relationship type desconocido: {self.rel_type!r} (ver schema.REL_TYPES)")


class Graph:
    """Grafo dirigido con resolucion de identidad por (label, qualified_id) -
    agregar el mismo nodo dos veces (ej. citado desde un ADR y desde un
    extractor de codigo) fusiona sus props en vez de duplicar (F13.10)."""

    def __init__(self) -> None:
        self._nodes: dict[tuple[str, str], Node] = {}
        self._edges: list[Edge] = []

    def add_node(self, node: Node) -> Node:
        existing = self._nodes.get(node.key)
        if existing is None:
            self._nodes[node.key] = node
            return node
        merged_props = {**existing.props, **node.props}
        merged = Node(label=node.label, qualified_id=node.qualified_id, props=merged_props)
        self._nodes[node.key] = merged
        return merged

    def add_edge(self, edge: Edge) -> None:
        if edge.source not in self._nodes:
            raise KeyError(f"Edge source no registrado como nodo: {edge.source}")
        if edge.target not in self._nodes:
            raise KeyError(f"Edge target no registrado como nodo: {edge.target}")
        self._edges.append(edge)

    @property
    def nodes(self) -> list[Node]:
        return list(self._nodes.values())

    @property
    def edges(self) -> list[Edge]:
        return list(self._edges)

    def nodes_by_label(self, label: str) -> list[Node]:
        return [n for n in self._nodes.values() if n.label == label]

    def get_node(self, label: str, qualified_id: str) -> Node | None:
        return self._nodes.get((label, qualified_id))

    def edges_from(self, source: tuple[str, str], rel_type: str | None = None) -> list[Edge]:
        return [e for e in self._edges if e.source == source and (rel_type is None or e.rel_type == rel_type)]

    def edges_to(self, target: tuple[str, str], rel_type: str | None = None) -> list[Edge]:
        return [e for e in self._edges if e.target == target and (rel_type is None or e.rel_type == rel_type)]

    # -- Export ----------------------------------------------------------

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "nodes": [
                {"label": n.label, "id": n.qualified_id, "props": n.props}
                for n in sorted(self._nodes.values(), key=lambda n: (n.label, n.qualified_id))
            ],
            "edges": [
                {
                    "rel_type": e.rel_type,
                    "source": {"label": e.source[0], "id": e.source[1]},
                    "target": {"label": e.target[0], "id": e.target[1]},
                    "props": e.props,
                }
                for e in self._edges
            ],
        }

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_jsonable(), indent=2, ensure_ascii=False), encoding="utf-8")

    # -- Queries reproducibles (F13.14 / F14.22) --------------------------

    def apps_without_scope(self) -> list[str]:
        """Apps sin USES_SCOPE ni USES_CONTEXT hacia ningun nodo."""
        from tools.organizational_governance.schema import REL_USES_CONTEXT, REL_USES_SCOPE

        out = []
        for app in self.nodes_by_label("App"):
            has_ctx = bool(self.edges_from(app.key, REL_USES_CONTEXT))
            has_scope = bool(self.edges_from(app.key, REL_USES_SCOPE))
            if not has_ctx and not has_scope:
                out.append(app.qualified_id)
        return sorted(out)

    def models_without_empresa(self) -> list[str]:
        from tools.organizational_governance.schema import SCOPE_NONE

        return sorted(
            m.qualified_id for m in self.nodes_by_label("Model") if m.props.get("scope") == SCOPE_NONE
        )

    def models_with_sede(self) -> list[str]:
        from tools.organizational_governance.schema import SCOPE_SEDE, SCOPE_SEDE_LEGACY_NULLSAFE

        return sorted(
            m.qualified_id
            for m in self.nodes_by_label("Model")
            if m.props.get("scope") in (SCOPE_SEDE, SCOPE_SEDE_LEGACY_NULLSAFE)
        )

    def models_with_area(self) -> list[str]:
        return sorted(m.qualified_id for m in self.nodes_by_label("Model") if m.props.get("has_area"))

    def viewsets_with_has_organizational_scope(self) -> list[str]:
        from tools.organizational_governance.schema import REL_USES_PERMISSION

        out = []
        for vs in self.nodes_by_label("ViewSet"):
            for e in self.edges_from(vs.key, REL_USES_PERMISSION):
                if e.target[1] == "HasOrganizationalScope":
                    out.append(vs.qualified_id)
        return sorted(out)

    def adrs_for_component(self, qualified_id: str) -> list[str]:
        from tools.organizational_governance.schema import REL_GOVERNS

        out = []
        for adr in self.nodes_by_label("ADR"):
            for e in self.edges_from(adr.key, REL_GOVERNS):
                if e.target[1] == qualified_id:
                    out.append(adr.qualified_id)
        return sorted(out)


def load_ekg_dumps_readonly(out_dir: Path) -> list[dict[str, Any]]:
    """[F13.0] Lee (solo lectura, nunca escribe ni importa codigo) los dumps
    JSON ya generados por el pipeline EKG existente en tools/ekg/out/*.json,
    si estan presentes, como dato complementario. No falla si no existen."""
    dumps: list[dict[str, Any]] = []
    if not out_dir.exists():
        return dumps
    for p in sorted(out_dir.glob("*.json")):
        try:
            dumps.append(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return dumps
