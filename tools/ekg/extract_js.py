"""
EKG extractor: static/<app>/js/*.js via Tree-sitter (JavaScript grammar).

Scope (see tools/ekg/PILOT_REPORT.md for the full limitations list):
  - Endpoint linking is best-effort. A JS file's `fetch()`/string-literal
    URLs are recorded as their own lightweight Endpoint nodes
    (`kind=js-literal`) via a CONSUMES edge, since the literal a JS module
    builds at runtime (e.g. `${API_ROOT}${id}/cambiar-estado/`) rarely
    matches the DRF router prefix text extracted from urls.py verbatim.
    tools/ekg/build_graph.py runs a second pass that adds a direct CONSUMES
    edge to the real router-derived Endpoint node whenever the JS literal
    contains that route as a substring - a heuristic, not exact resolution.
  - DOM selectors referenced by the file (ids, `data-*` attribute selectors)
    are recorded as a property for extract_templates.py to cross-reference,
    not as first-class graph nodes (no "DOM element" label in the schema).
"""

from __future__ import annotations

from pathlib import Path

import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser, Query, QueryCursor
from tree_sitter import Node as TSNode

from tools.ekg import schema

JS_LANGUAGE = Language(tsjavascript.language())
_PARSER = Parser(JS_LANGUAGE)

ENDPOINT_MARKERS = ("/api/", "/ui/")
DOM_SELECTOR_PREFIXES = ("#", ".")


def _text(node: TSNode, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _strip_string_literal(raw: str) -> str:
    if len(raw) >= 2 and raw[0] in "'\"`" and raw[-1] == raw[0]:
        return raw[1:-1]
    return raw


def iter_string_literals(root: TSNode, src: bytes) -> list[str]:
    q = Query(JS_LANGUAGE, "[(string) (template_string)] @lit")
    qc = QueryCursor(q)
    values = []
    for _, captures in qc.matches(root):
        for node in captures["lit"]:
            values.append(_strip_string_literal(_text(node, src)))
    return values


def collect_const_string_bindings(root: TSNode, src: bytes) -> dict[str, str]:
    """Resolve `const NAME = "literal"` / `` const NAME = `${OTHER}suffix` ``
    bindings in source order, so template-string endpoint URLs built from a
    previously-defined constant (the common pattern in this codebase's
    *.api.js files, e.g. PLANTILLAS_ROOT = `${API_ROOT}plantillas/`) can be
    flattened into their effective literal value."""
    bindings: dict[str, str] = {}

    def walk(node: TSNode) -> None:
        if node.type == "variable_declarator":
            name_node = node.child_by_field_name("name")
            value_node = node.child_by_field_name("value")
            if name_node is not None and name_node.type == "identifier" and value_node is not None:
                name = _text(name_node, src)
                if value_node.type == "string":
                    bindings[name] = _strip_string_literal(_text(value_node, src))
                elif value_node.type == "template_string":
                    resolved = _resolve_template_string(value_node, src, bindings)
                    if resolved is not None:
                        bindings[name] = resolved
        for child in node.children:
            walk(child)

    walk(root)
    return bindings


def _resolve_template_string(node: TSNode, src: bytes, bindings: dict[str, str]) -> str | None:
    parts: list[str] = []
    for child in node.children:
        if child.type == "string_fragment":
            parts.append(_text(child, src))
        elif child.type == "template_substitution":
            identifier_node = next((c for c in child.children if c.type == "identifier"), None)
            if identifier_node is None:
                return None
            name = _text(identifier_node, src)
            if name not in bindings:
                return None
            parts.append(bindings[name])
        elif child.type == "`":
            continue
    return "".join(parts)


def iter_resolved_template_literals(root: TSNode, src: bytes, bindings: dict[str, str]) -> list[str]:
    """Every `template_string` in the file, resolved against `bindings`
    where possible (returns only the ones that fully resolved - a template
    with an unresolvable substitution contributes nothing, it does not leak
    a partial/misleading literal)."""
    q = Query(JS_LANGUAGE, "(template_string) @tpl")
    qc = QueryCursor(q)
    resolved = []
    for _, captures in qc.matches(root):
        for node in captures["tpl"]:
            value = _resolve_template_string(node, src, bindings)
            if value is not None:
                resolved.append(value)
    return resolved


def iter_top_level_namespaces(root: TSNode, src: bytes) -> set[str]:
    """Collect `window.Sintel.X...` assignment targets, e.g.
    `window.Sintel.Compras.API = ...` -> "window.Sintel.Compras.API"."""
    namespaces: set[str] = set()
    q = Query(
        JS_LANGUAGE,
        "(assignment_expression left: (member_expression) @target)",
    )
    qc = QueryCursor(q)
    for _, captures in qc.matches(root):
        for node in captures["target"]:
            text = _text(node, src)
            if text.startswith("window.Sintel."):
                namespaces.add(text)
    return namespaces


def classify_literals(literals: list[str]) -> tuple[list[str], list[str]]:
    """Split raw string literals into (endpoint_like, dom_selector_like)."""
    endpoints = []
    selectors = []
    for value in literals:
        if any(marker in value for marker in ENDPOINT_MARKERS):
            endpoints.append(value)
        elif value.startswith(DOM_SELECTOR_PREFIXES) and len(value) > 1:
            selectors.append(value)
    return endpoints, selectors


def extract_app_js(app_name: str, project_root: Path) -> schema.Graph:
    graph = schema.Graph()
    js_dir = project_root / "apps" / "tenant" / app_name / "static" / app_name / "js"
    if not js_dir.exists():
        return graph

    app_node_id = schema.application_id(app_name)
    graph.add_node(schema.Node(app_node_id, schema.NODE_APPLICATION, {"name": app_name}))

    js_files = sorted(js_dir.rglob("*.js"))
    for path in js_files:
        src = path.read_bytes()
        tree = _PARSER.parse(src)
        root = tree.root_node
        rel_path = path.relative_to(project_root).as_posix()

        namespaces = iter_top_level_namespaces(root, src)
        bindings = collect_const_string_bindings(root, src)
        literals = iter_string_literals(root, src) + iter_resolved_template_literals(root, src, bindings)
        endpoints, selectors = classify_literals(literals)

        js_node_id = schema.js_id(rel_path)
        graph.add_node(
            schema.Node(
                js_node_id,
                schema.NODE_JS,
                {
                    "path": rel_path,
                    "namespaces": sorted(namespaces),
                    "dom_selectors": sorted(set(selectors)),
                },
            )
        )
        graph.add_edge(schema.Edge(js_node_id, app_node_id, schema.REL_BELONGS_TO))

        for endpoint_literal in sorted(set(endpoints)):
            endpoint_node_id = schema.endpoint_id(app_name, endpoint_literal, "js-literal")
            graph.add_node(
                schema.Node(
                    endpoint_node_id,
                    schema.NODE_ENDPOINT,
                    {"route": endpoint_literal, "group": "js-literal", "kind": "js-literal"},
                )
            )
            graph.add_edge(schema.Edge(js_node_id, endpoint_node_id, schema.REL_CONSUMES))

    return graph
