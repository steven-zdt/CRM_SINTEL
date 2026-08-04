"""
EKG extractor: Python source (models.py, services/*.py, api/*.py, urls.py,
tests/*.py) via Tree-sitter. No regex is used to derive code structure or
relationships - every fact comes from walking the parsed syntax tree.

Design notes / known limitations (see tools/ekg/PILOT_REPORT.md for the full
list):
  - Cross-app FK/model targets that this pass has not itself parsed are
    recorded as "external stub" nodes (properties["external"] = True) rather
    than left dangling or silently dropped - tools/ekg/validate.py treats
    stubs differently from true orphans.
  - ViewSet -> Serializer wiring is a static reference scan (every
    "...Serializer" identifier assigned or returned inside the class body),
    not a control-flow-accurate resolution of get_serializer_class().
  - FK target resolution only handles literal string/identifier arguments
    (e.g. ForeignKey("app.Model", ...) or ForeignKey(SomeModel, ...)); a
    computed/dynamic target is left unresolved (no REFERENCES edge, target
    text kept as a Field property for a human to check).
"""

from __future__ import annotations

from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Query, QueryCursor
from tree_sitter import Node as TSNode

from tools.ekg import schema

PY_LANGUAGE = Language(tspython.language())
_PARSER = Parser(PY_LANGUAGE)

FK_FIELD_SUFFIXES = ("ForeignKey", "OneToOneField", "ManyToManyField")
META_LIST_PROPS = ("indexes", "constraints", "unique_together", "ordering")


# ---------------------------------------------------------------------------
# Low level tree-sitter helpers
# ---------------------------------------------------------------------------


def _text(node: TSNode, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _line(node: TSNode) -> int:
    return node.start_point[0] + 1


def _defined_in(path: Path, project_root: Path, node: TSNode) -> str:
    """Relative-to-project_root "defined_in" provenance string. Must never
    use an absolute path.as_posix() directly - PROJECT_ROOT in
    build_graph.py is always absolute, so every "defined_in" property
    silently baked in the machine-specific absolute path (Windows host path
    here, `/app` inside the Docker container elsewhere) until this was
    fixed. Not portable/reproducible across machines - a real bug, not just
    a cosmetic one, since a shared Neo4j graph is meant to be the same
    regardless of who ran the extraction."""
    return f"{path.relative_to(project_root).as_posix()}:{_line(node)}"


def parse_source(path: Path) -> tuple[TSNode, bytes]:
    src = path.read_bytes()
    tree = _PARSER.parse(src)
    return tree.root_node, src


def iter_top_level_classes(root: TSNode, src: bytes):
    """Yield (name_node, bases: list[str], body_node, class_node) for every
    class defined directly at module level (decorators are unwrapped)."""
    for child in root.children:
        node = child
        if node.type == "decorated_definition":
            for inner in node.children:
                if inner.type == "class_definition":
                    node = inner
                    break
        if node.type != "class_definition":
            continue
        name_node = node.child_by_field_name("name")
        if name_node is None:
            continue
        bases_node = node.child_by_field_name("superclasses")
        body_node = node.child_by_field_name("body")
        bases = _extract_base_names(bases_node, src) if bases_node else []
        yield name_node, bases, body_node, node


def _extract_base_names(bases_node: TSNode, src: bytes) -> list[str]:
    names = []
    for c in bases_node.children:
        if c.type in ("identifier", "attribute"):
            names.append(_text(c, src))
    return names


def iter_class_level_assignments(body_node: TSNode, src: bytes):
    """Yield (name, right_node) for direct `name = <expr>` statements at the
    top of a class body (i.e. fields), skipping methods and nested classes."""
    if body_node is None:
        return
    for child in body_node.children:
        if child.type != "expression_statement" or not child.children:
            continue
        assign = child.children[0]
        if assign.type != "assignment":
            continue
        left = assign.child_by_field_name("left")
        right = assign.child_by_field_name("right")
        if left is None or right is None or left.type != "identifier":
            continue
        yield _text(left, src), right


def find_nested_class(body_node: TSNode, src: bytes, class_name: str) -> TSNode | None:
    if body_node is None:
        return None
    for child in body_node.children:
        if child.type != "class_definition":
            continue
        name_node = child.child_by_field_name("name")
        if name_node is not None and _text(name_node, src) == class_name:
            return child
    return None


def call_target_and_args(node: TSNode, src: bytes) -> tuple[str, TSNode] | None:
    """If `node` is a call expression, return (callee_text, argument_list)."""
    if node.type != "call":
        return None
    fn = node.child_by_field_name("function")
    args = node.child_by_field_name("arguments")
    if fn is None or args is None:
        return None
    return _text(fn, src), args


def first_positional_or_kwarg(args_node: TSNode, src: bytes, kwarg_name: str) -> TSNode | None:
    positional = []
    kwarg_value = None
    for c in args_node.children:
        if c.type == "keyword_argument":
            name_node = c.child_by_field_name("name")
            value_node = c.child_by_field_name("value")
            if name_node is not None and _text(name_node, src) == kwarg_name:
                kwarg_value = value_node
        elif c.type in ("string", "identifier", "attribute"):
            positional.append(c)
    if kwarg_value is not None:
        return kwarg_value
    return positional[0] if positional else None


def string_literal_value(node: TSNode, src: bytes) -> str | None:
    """Resolve a `string` node to its literal value, honoring the
    string_start/string_content/string_end split tree-sitter uses (so
    prefixed literals like r"..." or f"..." don't leak their prefix)."""
    if node.type != "string":
        return None
    parts = [c for c in node.children if c.type == "string_content"]
    if not parts:
        return ""
    return "".join(_text(c, src) for c in parts)


def identifiers_by_suffix(node: TSNode, src: bytes, suffix: str) -> set[str]:
    """Best-effort static scan: every `identifier` token anywhere in the
    subtree whose text ends with `suffix`. Used to link ViewSets to the
    Serializer classes they reference without needing control-flow
    resolution of get_serializer_class()."""
    found: set[str] = set()

    def walk(n: TSNode) -> None:
        if n.type == "identifier":
            text = _text(n, src)
            if text.endswith(suffix):
                found.add(text)
        for c in n.children:
            walk(c)

    walk(node)
    return found


def iter_attribute_calls(node: TSNode, src: bytes):
    """Yield (receiver_text, method_name, line) for every `Receiver.method(...)`
    call anywhere in the subtree - used to link business_service -> crud_service."""
    q = Query(PY_LANGUAGE, "(call function: (attribute) @fn) @call")
    qc = QueryCursor(q)
    for _, captures in qc.matches(node):
        for fn_node in captures.get("fn", []):
            fn_text = _text(fn_node, src)
            if "." not in fn_text:
                continue
            receiver, _, method = fn_text.rpartition(".")
            yield receiver, method, _line(fn_node)


def iter_imports(root: TSNode, src: bytes):
    """Yield (module_text, imported_name_or_None, line) for every import in
    the file (module-level `import x` / `from x import y, z as w`)."""
    results = []
    for child in root.children:
        if child.type == "import_statement":
            for c in child.children:
                if c.type == "dotted_name":
                    results.append((_text(c, src), None, _line(child)))
                elif c.type == "aliased_import":
                    name_node = c.child_by_field_name("name")
                    if name_node is not None:
                        results.append((_text(name_node, src), None, _line(child)))
        elif child.type == "import_from_statement":
            module_node = child.child_by_field_name("module_name")
            module_text = _text(module_node, src) if module_node is not None else ""
            imported = []
            for c in child.children:
                if module_node is not None and c.id == module_node.id:
                    continue
                if c.type == "dotted_name":
                    imported.append(_text(c, src))
                elif c.type == "aliased_import":
                    name_node = c.child_by_field_name("name")
                    if name_node is not None:
                        imported.append(_text(name_node, src))
                elif c.type == "wildcard_import":
                    imported.append("*")
            if not imported:
                imported = [None]
            for name in imported:
                results.append((module_text, name, _line(child)))
    return results


# ---------------------------------------------------------------------------
# Model target resolution (FK / Meta.model)
# ---------------------------------------------------------------------------


def resolve_model_target(
    ref_node: TSNode, src: bytes, app_name: str, app_label: str, graph: schema.Graph
) -> str | None:
    """Given a FK-target or Meta.model reference node, return the Model
    node id it points to, creating an external stub node if the target
    belongs to an app this pass has not parsed.

    Model ids are keyed by the real Django app_label (e.g.
    "Model:tenant_proveedores.Proveedor"), not the apps/tenant/<folder>
    name used for every other node type - FK strings and Meta.model always
    resolve through Django's app_label namespace, so an external stub
    created here must use the exact same id a direct extraction of that
    other app would produce, or the two never merge into one node once
    both apps' graphs are loaded together. See resolve_app_label() and the
    PILOT_REPORT.md "cross-app id consistency" note."""
    text: str | None
    if ref_node.type == "string":
        text = string_literal_value(ref_node, src)
    else:
        text = _text(ref_node, src)
    if not text or text == "self":
        return None

    if "." in text:
        label_part, _, model_part = text.rpartition(".")
    else:
        label_part, model_part = app_label, text

    if label_part == app_label:
        node_id = schema.model_id(app_label, model_part)
        if node_id not in graph.nodes:
            # Referenced before its own Model node was created in this pass
            # (e.g. self-referential FK) - create the placeholder now, the
            # real extractor call will merge full properties onto it later.
            graph.add_node(schema.Node(node_id, schema.NODE_MODEL, {"name": model_part}))
        return node_id

    node_id = schema.model_id(label_part, model_part)
    graph.add_node(
        schema.Node(
            node_id,
            schema.NODE_MODEL,
            {"name": model_part, "app_label": label_part, "external": True},
        )
    )
    return node_id


# ---------------------------------------------------------------------------
# models.py
# ---------------------------------------------------------------------------


def extract_models(
    app_name: str, app_label: str, path: Path, graph: schema.Graph, project_root: Path
) -> None:
    if not path.exists():
        return
    root, src = parse_source(path)
    app_node_id = schema.application_id(app_name)

    for name_node, bases, body_node, class_node in iter_top_level_classes(root, src):
        class_name = _text(name_node, src)
        model_node_id = schema.model_id(app_label, class_name)
        graph.add_node(
            schema.Node(
                model_node_id,
                schema.NODE_MODEL,
                {
                    "name": class_name,
                    "app_label": app_label,
                    "defined_in": _defined_in(path, project_root, class_node),
                    "bases": bases,
                    # overwrites any stale True left by an external-stub
                    # reference to this exact model from another app's FK,
                    # extracted before this (real) definition was reached -
                    # see resolve_model_target()'s docstring.
                    "external": False,
                },
            )
        )
        graph.add_edge(schema.Edge(model_node_id, app_node_id, schema.REL_BELONGS_TO))
        for base in bases:
            base_id = schema.model_id(app_label, base)
            if base_id in graph.nodes:
                graph.add_edge(schema.Edge(model_node_id, base_id, schema.REL_INHERITS))

        meta_node = find_nested_class(body_node, src, "Meta")
        meta_props: dict[str, str] = {}
        if meta_node is not None:
            meta_body = meta_node.child_by_field_name("body")
            for meta_field_name, meta_right in iter_class_level_assignments(meta_body, src):
                if meta_field_name in META_LIST_PROPS:
                    meta_props[meta_field_name] = _text(meta_right, src)
        if meta_props:
            graph.add_node(schema.Node(model_node_id, schema.NODE_MODEL, meta_props))

        for field_name, right_node in iter_class_level_assignments(body_node, src):
            call = call_target_and_args(right_node, src)
            field_node_id = schema.field_id(app_name, class_name, field_name)
            if call is None:
                continue
            callee_text, args_node = call
            field_type = callee_text.rpartition(".")[2] if "." in callee_text else callee_text
            graph.add_node(
                schema.Node(
                    field_node_id,
                    schema.NODE_FIELD,
                    {"name": field_name, "type": field_type, "model": class_name},
                )
            )
            graph.add_edge(schema.Edge(model_node_id, field_node_id, schema.REL_HAS_FIELD))

            if field_type in FK_FIELD_SUFFIXES:
                target_ref = first_positional_or_kwarg(args_node, src, "to")
                if target_ref is not None:
                    target_model_id = resolve_model_target(
                        target_ref, src, app_name, app_label, graph
                    )
                    if target_model_id is not None:
                        graph.add_edge(
                            schema.Edge(field_node_id, target_model_id, schema.REL_REFERENCES)
                        )


# ---------------------------------------------------------------------------
# services/*.py
# ---------------------------------------------------------------------------

def _cross_tenant_app_from_module(module_text: str, current_app: str) -> str | None:
    """Return the other app name if `module_text` is an
    apps.tenant.<other_app>... import, else None (stdlib/DRF/Django/same-app
    imports are not modeled as cross-app dependency edges)."""
    prefix = "apps.tenant."
    if not module_text.startswith(prefix):
        return None
    remainder = module_text[len(prefix) :]
    other_app = remainder.split(".", 1)[0]
    if not other_app or other_app == current_app:
        return None
    return other_app


_SERVICE_FILE_KIND = {
    "selectors.py": schema.SERVICE_KIND_SELECTOR,
    "crud_service.py": schema.SERVICE_KIND_CRUD,
    "business_service.py": schema.SERVICE_KIND_BUSINESS,
    "api_mixins.py": schema.SERVICE_KIND_MIXIN,
}


def _service_kind_for(filename: str) -> str:
    return _SERVICE_FILE_KIND.get(filename, schema.SERVICE_KIND_OTHER)


def extract_services(
    app_name: str, services_dir: Path, graph: schema.Graph, project_root: Path
) -> dict[str, str]:
    """Returns a map of {class_name: node_id} for every Service class found.

    Walks services_dir recursively (not just its direct children) because
    some apps outgrew the flat FSD layout - e.g. facturas/services/dian/
    (cufe.py, ubl21_builder.py, xades_signer.py) and
    facturas/services/services_mail_ingestion.py. A file is classified as
    selector/crud/business/mixin only by the four canonical FSD filenames;
    anything else (nested or top-level) is SERVICE_KIND_OTHER rather than
    guessed at - see schema.py's SERVICE_KIND_OTHER docstring."""
    class_to_node: dict[str, str] = {}
    if not services_dir.exists():
        return class_to_node

    app_node_id = schema.application_id(app_name)
    receivers: dict[str, str] = {}  # class_name -> node_id, filled as we go

    # Process the four canonical FSD files first (in FSD dependency order,
    # so business_service's CALLS-to-crud_service resolves), then every
    # other/nested module.
    paths = [services_dir / name for name in _SERVICE_FILE_KIND if (services_dir / name).exists()]
    other_paths = sorted(
        p for p in services_dir.rglob("*.py")
        if p.name not in _SERVICE_FILE_KIND and p.name != "__init__.py"
    )
    paths.extend(other_paths)

    for path in paths:
        module_name = path.relative_to(services_dir).with_suffix("").as_posix().replace("/", ".")
        kind = _service_kind_for(path.name)
        root, src = parse_source(path)

        for module_text, imported_name, line in iter_imports(root, src):
            other_app = _cross_tenant_app_from_module(module_text, app_name)
            if other_app is not None:
                other_app_node_id = schema.application_id(other_app)
                graph.add_node(
                    schema.Node(other_app_node_id, schema.NODE_APPLICATION, {"name": other_app, "external": True})
                )
                graph.add_edge(
                    schema.Edge(
                        app_node_id,
                        other_app_node_id,
                        schema.REL_IMPORTS,
                        {"module": module_text, "name": imported_name, "line": line, "in_file": module_name},
                    )
                )

        for name_node, bases, body_node, class_node in iter_top_level_classes(root, src):
            class_name = _text(name_node, src)
            node_id = schema.service_id(app_name, module_name, class_name)
            graph.add_node(
                schema.Node(
                    node_id,
                    schema.NODE_SERVICE,
                    {
                        "name": class_name,
                        "kind": kind,
                        "defined_in": _defined_in(path, project_root, class_node),
                        "bases": bases,
                    },
                )
            )
            graph.add_edge(schema.Edge(node_id, app_node_id, schema.REL_BELONGS_TO))
            class_to_node[class_name] = node_id
            receivers[class_name] = node_id

            if kind == schema.SERVICE_KIND_BUSINESS and body_node is not None:
                # Graph.add_edge de-dupes on (source, target, rel_type), so
                # aggregate every distinct method into one CALLS edge per
                # (business_service, target_service) pair instead of losing
                # all but the first call site.
                calls_by_target: dict[str, set[str]] = {}
                for receiver, method, _call_line in iter_attribute_calls(body_node, src):
                    target_id = receivers.get(receiver)
                    if target_id is not None and target_id != node_id:
                        calls_by_target.setdefault(target_id, set()).add(method)
                for target_id, methods in calls_by_target.items():
                    graph.add_edge(
                        schema.Edge(
                            node_id, target_id, schema.REL_CALLS, {"methods": sorted(methods)}
                        )
                    )

    return class_to_node


# ---------------------------------------------------------------------------
# api/serializers.py
# ---------------------------------------------------------------------------


def extract_serializers(
    app_name: str, app_label: str, path: Path, graph: schema.Graph, project_root: Path
) -> dict[str, str]:
    class_to_node: dict[str, str] = {}
    if not path.exists():
        return class_to_node
    root, src = parse_source(path)
    app_node_id = schema.application_id(app_name)

    for name_node, bases, body_node, class_node in iter_top_level_classes(root, src):
        class_name = _text(name_node, src)
        if not any("Serializer" in b or "Field" in b for b in bases):
            continue
        node_id = schema.serializer_id(app_name, class_name)
        graph.add_node(
            schema.Node(
                node_id,
                schema.NODE_SERIALIZER,
                {
                    "name": class_name,
                    "defined_in": _defined_in(path, project_root, class_node),
                    "bases": bases,
                },
            )
        )
        graph.add_edge(schema.Edge(node_id, app_node_id, schema.REL_BELONGS_TO))
        class_to_node[class_name] = node_id

        meta_node = find_nested_class(body_node, src, "Meta")
        if meta_node is not None:
            meta_body = meta_node.child_by_field_name("body")
            for meta_field_name, meta_right in iter_class_level_assignments(meta_body, src):
                if meta_field_name == "model":
                    target_model_id = resolve_model_target(
                        meta_right, src, app_name, app_label, graph
                    )
                    if target_model_id is not None:
                        graph.add_edge(
                            schema.Edge(node_id, target_model_id, schema.REL_USES)
                        )

    return class_to_node


# ---------------------------------------------------------------------------
# api/viewsets.py
# ---------------------------------------------------------------------------


# Files under api/ that have their own dedicated extractor, or are DRF
# infra (routing/permissions/filtering/pagination config) rather than
# ViewSet-family classes - skipped so extract_viewsets doesn't misclassify
# their contents.
_API_NON_VIEWSET_FILENAMES = frozenset(
    {"serializers.py", "urls.py", "filters.py", "permissions.py", "pagination.py", "__init__.py"}
)

_VIEWSET_BASE_MARKERS = ("ViewSet", "APIView", "GenericAPIView", "ListAPIView", "CreateAPIView")


def _is_viewset_family(class_name: str, bases: list[str]) -> bool:
    if "ViewSet" in class_name or "Mixin" in class_name or "View" in class_name:
        return True
    return any(any(marker in b for marker in _VIEWSET_BASE_MARKERS) or "Mixin" in b for b in bases)


def _viewset_kind_for(class_name: str, bases: list[str]) -> str:
    if "ViewSet" in class_name or any("ViewSet" in b for b in bases):
        return schema.VIEWSET_KIND_VIEWSET
    if "Mixin" in class_name:
        return schema.VIEWSET_KIND_MIXIN
    return schema.VIEWSET_KIND_VIEW


def extract_viewsets(
    app_name: str,
    api_dir: Path,
    graph: schema.Graph,
    serializer_nodes: dict[str, str],
    service_nodes: dict[str, str],
    project_root: Path,
) -> dict[str, str]:
    """Returns a map of {class_name: node_id} for every ViewSet/APIView/
    ViewSet-mixin class found under api/ (recursively - e.g. facturas/
    api/mixins/*.py, facturas/api/views_mail_ingestion.py), not just
    api/viewsets.py. See schema.py's VIEWSET_KIND_* docstring for how the
    three kinds are distinguished."""
    class_to_node: dict[str, str] = {}
    if not api_dir.exists():
        return class_to_node
    app_node_id = schema.application_id(app_name)

    paths = sorted(
        p for p in api_dir.rglob("*.py") if p.name not in _API_NON_VIEWSET_FILENAMES
    )

    # Pass 1: create every ViewSet-family node before resolving any base
    # class, so a mixin defined in a file processed after its user (e.g.
    # api/viewsets.py before api/mixins/*.py in some app) still resolves.
    parsed_files = []
    for path in paths:
        root, src = parse_source(path)
        parsed_files.append((path, root, src))
        for name_node, bases, _body_node, class_node in iter_top_level_classes(root, src):
            class_name = _text(name_node, src)
            if not _is_viewset_family(class_name, bases):
                continue
            node_id = schema.viewset_id(app_name, class_name)
            graph.add_node(
                schema.Node(
                    node_id,
                    schema.NODE_VIEWSET,
                    {
                        "name": class_name,
                        "kind": _viewset_kind_for(class_name, bases),
                        "defined_in": _defined_in(path, project_root, class_node),
                        "bases": bases,
                    },
                )
            )
            graph.add_edge(schema.Edge(node_id, app_node_id, schema.REL_BELONGS_TO))
            class_to_node[class_name] = node_id

    # Pass 2: resolve bases (INHERITS to sibling ViewSet-family classes,
    # USES to service-layer mixins) and Serializer references.
    for _path, root, src in parsed_files:
        for name_node, bases, body_node, _class_node in iter_top_level_classes(root, src):
            class_name = _text(name_node, src)
            node_id = class_to_node.get(class_name)
            if node_id is None:
                continue

            for base in bases:
                sibling_id = class_to_node.get(base)
                if sibling_id is not None and sibling_id != node_id:
                    graph.add_edge(schema.Edge(node_id, sibling_id, schema.REL_INHERITS))
                    continue
                mixin_id = service_nodes.get(base)
                if mixin_id is not None:
                    graph.add_edge(schema.Edge(node_id, mixin_id, schema.REL_USES))

            if body_node is not None:
                for serializer_name in identifiers_by_suffix(body_node, src, "Serializer"):
                    target_id = serializer_nodes.get(serializer_name)
                    if target_id is None:
                        target_id = schema.serializer_id(app_name, serializer_name)
                        graph.add_node(
                            schema.Node(
                                target_id,
                                schema.NODE_SERIALIZER,
                                {"name": serializer_name, "external": True},
                            )
                        )
                    graph.add_edge(schema.Edge(node_id, target_id, schema.REL_USES))

    return class_to_node


# ---------------------------------------------------------------------------
# urls.py / api/urls.py
# ---------------------------------------------------------------------------


def _is_include_call(node: TSNode, src: bytes) -> bool:
    call = call_target_and_args(node, src)
    return call is not None and call[0] == "include"


def _extract_view_class_name(view_text: str) -> str:
    """Pull the class name out of a `path()` view argument's raw text.

    `view_text.split(".", 1)[0]` (the old logic) silently took the wrong
    segment whenever the view was referenced through a module-qualified
    import instead of a bare one - e.g. `views.DashboardDataAPIView
    .as_view()` (dashboard/api/urls.py does `from . import views` rather
    than `from .views import DashboardDataAPIView`) resolved to "views",
    which is never a real ViewSet name, so the endpoint could never link.
    Strip the call parens, then take the segment before a trailing
    ".as_view" if present (the DRF convention), else the last dotted
    segment (handles a bare function-based view reference too)."""
    dotted = view_text.split("(", 1)[0]
    parts = dotted.split(".")
    if len(parts) >= 2 and parts[-1] == "as_view":
        return parts[-2]
    return parts[-1]


def extract_urls(
    app_name: str, path: Path, graph: schema.Graph, viewset_nodes: dict[str, str], group: str
) -> None:
    if not path.exists():
        return
    root, src = parse_source(path)

    # router.register(prefix, ViewSetClass, basename=...)
    q = Query(PY_LANGUAGE, "(call function: (attribute) @fn arguments: (argument_list) @args)")
    qc = QueryCursor(q)
    for _, captures in qc.matches(root):
        fn_node = captures["fn"][0]
        args_node = captures["args"][0]
        fn_text = _text(fn_node, src)
        if not fn_text.endswith(".register"):
            continue
        positional = [
            c for c in args_node.children if c.type in ("string", "identifier", "attribute")
        ]
        if len(positional) < 2:
            continue
        prefix = string_literal_value(positional[0], src)
        if prefix is None:
            prefix = _text(positional[0], src)
        # router.register(r'', viewsets.DashboardViewSet, ...) - same
        # module-qualified-reference issue _extract_view_class_name()
        # exists for, just without a trailing ".as_view()" call to strip.
        viewset_name = _text(positional[1], src).split(".")[-1]
        endpoint_node_id = schema.endpoint_id(app_name, prefix or "/", group)
        graph.add_node(
            schema.Node(
                endpoint_node_id,
                schema.NODE_ENDPOINT,
                {"route": prefix, "group": group, "kind": "router"},
            )
        )
        target_viewset_id = viewset_nodes.get(viewset_name)
        if target_viewset_id is not None:
            graph.add_edge(schema.Edge(target_viewset_id, endpoint_node_id, schema.REL_EXPOSES))

    q_path = Query(PY_LANGUAGE, "(call function: (identifier) @fn arguments: (argument_list) @args)")
    qc_path = QueryCursor(q_path)
    for _, captures in qc_path.matches(root):
        fn_node = captures["fn"][0]
        if _text(fn_node, src) != "path":
            continue
        args_node = captures["args"][0]
        positional = [
            c for c in args_node.children if c.type in ("string", "identifier", "attribute", "call")
        ]
        if not positional:
            continue
        route = string_literal_value(positional[0], src)
        if route is None:
            continue
        if len(positional) > 1 and _is_include_call(positional[1], src):
            # path("", include(router.urls)) / path("app/", include("app.urls"))
            # mounts a sub-urlconf, it is not itself a concrete endpoint -
            # inventario/api/urls.py's `path('', include(router.urls))` was
            # showing up as a permanently-"unexposed" endpoint before this
            # check (compras/proveedores/etc mount via `urlpatterns =
            # router.urls` directly and never hit this path() branch at all).
            continue
        view_text = _text(positional[1], src) if len(positional) > 1 else ""
        endpoint_node_id = schema.endpoint_id(app_name, route, group)
        graph.add_node(
            schema.Node(
                endpoint_node_id,
                schema.NODE_ENDPOINT,
                {"route": route, "group": group, "kind": "path", "view": view_text},
            )
        )
        view_class = _extract_view_class_name(view_text)
        target_viewset_id = viewset_nodes.get(view_class)
        if target_viewset_id is not None:
            graph.add_edge(schema.Edge(target_viewset_id, endpoint_node_id, schema.REL_EXPOSES))


# ---------------------------------------------------------------------------
# tests/*.py
# ---------------------------------------------------------------------------


def extract_tests(app_name: str, project_root: Path, app_dir: Path, graph: schema.Graph) -> None:
    known_names: dict[str, str] = {
        node.properties.get("name"): node_id
        for node_id, node in graph.nodes.items()
        if node.label in (schema.NODE_MODEL, schema.NODE_SERVICE, schema.NODE_VIEWSET, schema.NODE_SERIALIZER)
        and node.properties.get("name")
    }

    candidate_dirs = [app_dir / "tests", project_root / "tests" / "tenant" / app_name]
    for tests_dir in candidate_dirs:
        if not tests_dir.exists():
            continue
        for test_file in sorted(tests_dir.glob("*.py")):
            if test_file.name == "__init__.py":
                continue
            root, src = parse_source(test_file)
            rel_path = test_file.relative_to(project_root).as_posix()
            test_node_id = schema.test_id(rel_path)
            graph.add_node(schema.Node(test_node_id, schema.NODE_TEST, {"path": rel_path}))

            referenced = identifiers_by_suffix(root, src, "")
            for name in referenced:
                target_id = known_names.get(name)
                if target_id is not None:
                    graph.add_edge(schema.Edge(target_id, test_node_id, schema.REL_TESTED_BY))


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def resolve_app_label(app_name: str, project_root: Path) -> str:
    """Read the real Django app_label from apps.py's AppConfig.label,
    falling back to Django's own default (the last path segment, i.e.
    app_name itself) when an app does not override it.

    This matters: roughly half of apps/tenant/* explicitly set
    `label = "tenant_<name>"` (compras, ventas, gastos, clientes,
    proveedores, proyectos, inventario) and roughly half do not - those
    keep Django's bare default (facturas, contabilidad, bancos, core,
    cotizaciones, dashboard, empleados, empresa, landing, perfil). A FK
    string like "facturas.Factura" is correct for the un-overridden apps;
    hardcoding "tenant_<app_name>" here would misclassify it as an
    external stub instead of resolving same-app references correctly."""
    path = project_root / "apps" / "tenant" / app_name / "apps.py"
    if not path.exists():
        return app_name
    root, src = parse_source(path)
    for _name_node, _bases, body_node, _class_node in iter_top_level_classes(root, src):
        for field_name, right_node in iter_class_level_assignments(body_node, src):
            if field_name == "label":
                value = string_literal_value(right_node, src)
                if value:
                    return value
    return app_name


def extract_app_python(app_name: str, project_root: Path) -> schema.Graph:
    graph = schema.Graph()
    app_dir = project_root / "apps" / "tenant" / app_name
    app_label = resolve_app_label(app_name, project_root)

    graph.add_node(
        schema.Node(schema.application_id(app_name), schema.NODE_APPLICATION, {"name": app_name, "app_label": app_label})
    )

    extract_models(app_name, app_label, app_dir / "models.py", graph, project_root)
    service_nodes = extract_services(app_name, app_dir / "services", graph, project_root)
    serializer_nodes = extract_serializers(
        app_name, app_label, app_dir / "api" / "serializers.py", graph, project_root
    )
    viewset_nodes = extract_viewsets(
        app_name, app_dir / "api", graph, serializer_nodes, service_nodes, project_root
    )
    extract_urls(app_name, app_dir / "api" / "urls.py", graph, viewset_nodes, group="api")
    extract_urls(app_name, app_dir / "urls.py", graph, viewset_nodes, group="ui")
    extract_tests(app_name, project_root, app_dir, graph)

    return graph
