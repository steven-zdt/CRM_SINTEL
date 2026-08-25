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
# Base classes that mean "this top-level class in models.py is NOT a Django
# Model" - e.g. `class RolTenant(models.TextChoices):`, a plain enum of
# string constants (a common, legitimate pattern for choice fields), not a
# model requiring SintelTenantBaseModel or a database table of its own.
_NON_MODEL_BASE_NAMES = frozenset({"TextChoices", "IntegerChoices", "Choices"})


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


def _build_import_map(root: TSNode, src: bytes) -> dict[str, str]:
    """Map a name visible in this file to the dotted module it was imported
    from, e.g. {"SintelTenantBaseModel": "apps.tenant.core.models"} for
    `from apps.tenant.core.models import SintelTenantBaseModel`. Used by
    _resolve_cross_app_base() below to find the real app a base class/mixin
    lives in when it isn't defined in the current file - see that
    function's docstring for the bug this closes."""
    import_map: dict[str, str] = {}
    for module_text, imported_name, _line in iter_imports(root, src):
        if imported_name and imported_name != "*":
            import_map[imported_name] = module_text
    return import_map


def _resolve_cross_app_base_folder(base_name: str, import_map: dict[str, str]) -> str | None:
    """Given a bare base-class name (e.g. "SintelTenantBaseModel",
    "BaseTenantViewSet") and this file's import map, return the
    apps/tenant/<folder> name it's actually imported from, or None if it
    isn't imported from apps.tenant.* at all (a Django/DRF builtin like
    models.Model, a third-party class, or a name this pass genuinely can't
    place). Callers that need a Model id must convert this folder name to
    a real app_label via resolve_app_label() first (Model ids are keyed by
    app_label); callers that need a ViewSet id use the folder name as-is
    (ViewSet ids are keyed by the apps/tenant/<folder> name, see schema.py).

    Bug this closes: extract_models()/extract_viewsets() used to resolve
    EVERY base class as schema.model_id/viewset_id(<same app as subclass>,
    base_name) - i.e. assumed the base always lives in the *same* app as
    the subclass. That is correct for a same-app sibling (e.g. one model
    inheriting another in the same models.py) but silently produces zero
    INHERITS edge for the single most common case in the whole project:
    every tenant model inheriting apps.tenant.core.models.
    SintelTenantBaseModel, and every tenant ViewSet inheriting
    apps.tenant.api.base.BaseTenantViewSet - both always live in a
    *different* app. Confirmed missing for
    `compras.OrdenCompra(SintelTenantBaseModel)` even on a fresh extraction
    (not a stale dump) while building the EKG impact/governance tooling -
    see documentacion/REMEDIACION_FASES2-8_AUDITORIA_ENTERPRISE.md."""
    module_text = import_map.get(base_name)
    if not module_text or not module_text.startswith("apps.tenant."):
        return None
    remainder = module_text[len("apps.tenant.") :]
    folder = remainder.split(".", 1)[0]
    return folder or None


def _base_class_name(base: str) -> str:
    """Normalize a base-class reference for sibling-node lookup: a module-
    qualified base like `inv_services.ProductoServiceMixin`
    (apps/tenant/inventario/api/viewsets.py) must resolve the same as a bare
    `ProductoServiceMixin` would - dict lookups on the raw qualified text
    never matched, making every mixin used this way look unreferenced (a
    dead-code false positive caught auditing the graph). The raw text is
    still kept in the node's own `bases` property for provenance; this is
    only applied at edge-resolution time."""
    return base.rsplit(".", 1)[-1]


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
    ref_node: TSNode,
    src: bytes,
    app_name: str,
    app_label: str,
    graph: schema.Graph,
    import_map: dict[str, str] | None = None,
    project_root: Path | None = None,
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
    PILOT_REPORT.md "cross-app id consistency" note.

    `import_map`/`project_root` (optional, both call sites always pass
    them) close a second instance of the same bug _resolve_cross_app_base_
    folder() fixes for base classes: Django allows `ForeignKey(SomeModel,
    ...)` with a real imported class reference, not only the dotted
    "app_label.Model" string form. A bare identifier used to be assumed
    same-app unconditionally - wrong for e.g. `empresa = ForeignKey(Empresa,
    ...)` after `from apps.tenant.empresa.models import Empresa` in
    empleados/inventario/proveedores/proyectos, each producing its own
    wrongly-namespaced, never-merging placeholder
    (`Model:tenant_empleados.Empresa` etc.) instead of the one real
    `Model:empresa.Empresa`. Found via the EKG governance sweep - see
    documentacion/REMEDIACION_FASES2-8_AUDITORIA_ENTERPRISE.md."""
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
        if import_map is not None and project_root is not None:
            cross_app_folder = _resolve_cross_app_base_folder(text, import_map)
            if cross_app_folder is not None:
                label_part = resolve_app_label(cross_app_folder, project_root)
                model_part = text

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
    import_map = _build_import_map(root, src)

    for name_node, bases, body_node, class_node in iter_top_level_classes(root, src):
        class_name = _text(name_node, src)
        if any(_base_class_name(b) in _NON_MODEL_BASE_NAMES for b in bases):
            # e.g. `class RolTenant(models.TextChoices):` in
            # apps/tenant/perfil/models.py - a plain enum of string
            # constants, not a Django Model, despite living in models.py
            # (a common, legitimate Django pattern for choice fields).
            # Found via the EKG governance sweep flagging RolTenant as "does
            # not inherit SintelTenantBaseModel" - a real extractor false
            # positive, not an architecture violation - see
            # documentacion/REMEDIACION_FASES2-8_AUDITORIA_ENTERPRISE.md.
            continue
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
            base_name = _base_class_name(base)
            base_id = schema.model_id(app_label, base_name)
            if base_id in graph.nodes:
                graph.add_edge(schema.Edge(model_node_id, base_id, schema.REL_INHERITS))
                continue
            cross_app_folder = _resolve_cross_app_base_folder(base_name, import_map)
            if cross_app_folder is not None:
                cross_app_label = resolve_app_label(cross_app_folder, project_root)
                cross_base_id = schema.model_id(cross_app_label, base_name)
                if cross_base_id not in graph.nodes:
                    graph.add_node(
                        schema.Node(
                            cross_base_id,
                            schema.NODE_MODEL,
                            {"name": base_name, "app_label": cross_app_label, "external": True},
                        )
                    )
                graph.add_edge(schema.Edge(model_node_id, cross_base_id, schema.REL_INHERITS))

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
                        target_ref, src, app_name, app_label, graph,
                        import_map=import_map, project_root=project_root,
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

            if kind in (schema.SERVICE_KIND_BUSINESS, schema.SERVICE_KIND_OTHER) and body_node is not None:
                # Non-canonically-named files (kind=other, e.g.
                # proyectos/services/presupuesto_service.py,
                # cotizaciones/services/producto_service.py) hold the exact
                # same intra-file Business->CRUD delegation pattern as
                # business_service.py, just without the FSD filename - e.g.
                # `PresupuestoCRUDService.save_item(item)` called from
                # `PresupuestoBusinessService` in the same file. Restricting
                # this scan to kind=business only made every such CRUD class
                # look unreferenced (4 confirmed cases caught auditing the
                # graph for dead code). Graph.add_edge de-dupes on (source,
                # target, rel_type), so aggregate every distinct method into
                # one CALLS edge per (caller, target_service) pair instead of
                # losing all but the first call site.
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

            if kind == schema.SERVICE_KIND_MIXIN and body_node is not None:
                # ServiceMixins wire in their Selector/CRUD/BusinessService not
                # via method calls but via class-attribute injection, e.g.
                # `business_service_class = OrdenCompraBusinessService`
                # (apps/tenant/compras/services/api_mixins.py) - a plain call
                # scan never sees this. Without this, every CRUD/Business
                # service in the app looks "never called" from the mixin that
                # actually wires it into the ViewSet, a false-positive
                # dead-code signal severe enough that it was caught auditing
                # apparently-orphaned services that are demonstrably live
                # (OrdenCompraBusinessService). Not hardcoded to the three
                # conventional attribute names (selector_class/
                # crud_service_class/business_service_class) - any class-level
                # `name = OtherServiceClass` assignment inside a mixin counts.
                for _attr_name, right_node in iter_class_level_assignments(body_node, src):
                    if right_node.type != "identifier":
                        continue
                    referenced_class = _text(right_node, src)
                    target_id = receivers.get(referenced_class)
                    if target_id is not None and target_id != node_id:
                        graph.add_edge(schema.Edge(node_id, target_id, schema.REL_USES))

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
    import_map = _build_import_map(root, src)

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
                        meta_right, src, app_name, app_label, graph,
                        import_map=import_map, project_root=project_root,
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
                        # Explicit False (not just "key absent"), mirroring
                        # extract_models()'s real-Model nodes: Graph.add_node's
                        # "external is monotonic" merge only forces false when
                        # the EXISTING node already has external is False -
                        # omitting the key here would let a same-app-processed-
                        # later stub (from a cross-app ViewSet INHERITS
                        # resolved by another app before this one merges)
                        # silently downgrade this real node back to external.
                        # Found while building the EKG governance sweep - a
                        # CoreViewSet inheriting a real tenant ViewSet showed
                        # up as still "external" after both apps were merged.
                        "external": False,
                    },
                )
            )
            graph.add_edge(schema.Edge(node_id, app_node_id, schema.REL_BELONGS_TO))
            class_to_node[class_name] = node_id

    # Pass 2: resolve bases (INHERITS to sibling ViewSet-family classes,
    # USES to service-layer mixins) and Serializer references.
    for _path, root, src in parsed_files:
        import_map = _build_import_map(root, src)
        for name_node, bases, body_node, _class_node in iter_top_level_classes(root, src):
            class_name = _text(name_node, src)
            node_id = class_to_node.get(class_name)
            if node_id is None:
                continue

            for base in bases:
                base_name = _base_class_name(base)
                sibling_id = class_to_node.get(base_name)
                if sibling_id is not None and sibling_id != node_id:
                    graph.add_edge(schema.Edge(node_id, sibling_id, schema.REL_INHERITS))
                    continue
                mixin_id = service_nodes.get(base_name)
                if mixin_id is not None:
                    graph.add_edge(schema.Edge(node_id, mixin_id, schema.REL_USES))
                    continue
                # Cross-app ViewSet-family base not resolvable from this
                # app's own class_to_node/service_nodes maps - e.g.
                # BaseTenantViewSet/SintelDSVMixin, both defined in
                # apps/tenant/api/, a separate "infrastructure" app this
                # pilot does not extract as one of its 17 business apps
                # (see documentacion/arquitectura_general.md §2.3). Recorded
                # as an external stub rather than left with zero edge at
                # all, same convention as an unresolved cross-app FK - see
                # _resolve_cross_app_base_folder()'s docstring for the bug
                # this closes.
                cross_app_folder = _resolve_cross_app_base_folder(base_name, import_map)
                if cross_app_folder is not None:
                    cross_base_id = schema.viewset_id(cross_app_folder, base_name)
                    if cross_base_id not in graph.nodes:
                        graph.add_node(
                            schema.Node(
                                cross_base_id,
                                schema.NODE_VIEWSET,
                                {
                                    "name": base_name,
                                    "kind": schema.VIEWSET_KIND_MIXIN,
                                    "external": True,
                                },
                            )
                        )
                    graph.add_edge(schema.Edge(node_id, cross_base_id, schema.REL_INHERITS))

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

                # Some ViewSets call a Selector/Service directly
                # (`CuentaContableSelector.get_qs_list(...)` in
                # contabilidad/api/viewsets.py) instead of going through a
                # ServiceMixin's class-attribute injection. Without this,
                # every Service only ever reachable this way looks
                # unreferenced - caught auditing the graph for dead code.
                for receiver, _method, _line_no in iter_attribute_calls(body_node, src):
                    target_id = service_nodes.get(receiver)
                    if target_id is not None:
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


def resolve_app_label(
    app_name: str, project_root: Path, schema_root: str = "tenant", folder_name: str | None = None
) -> str:
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
    external stub instead of resolving same-app references correctly.

    `schema_root`/`folder_name` (added when extending coverage to
    apps/public/* - see extract_app_python()'s docstring for why `app_name`
    and the on-disk folder name are no longer always the same string)."""
    path = project_root / "apps" / schema_root / (folder_name or app_name) / "apps.py"
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


def extract_app_python(
    app_name: str, project_root: Path, schema_root: str = "tenant", folder_name: str | None = None
) -> schema.Graph:
    """`app_name` is the id-namespace used for every node this pass creates
    (Application/Model/Service/ViewSet/... ids all key off it - see
    schema.py's id helpers); `folder_name` (defaults to `app_name`) is the
    on-disk directory name, only ever used to build a Path. They differ
    only for apps/public/* apps: `apps/tenant/core` and `apps/public/core`
    are two entirely different, unrelated apps that happen to share the
    bare folder name "core" - extracting the public one with app_name=
    "core" would collide its Application/ViewSet/JS/... ids with the
    tenant one's (Model ids are safe either way, they key off the real
    Django app_label, and apps/tenant/core deliberately overrides its
    label to "tenant_core" for exactly this reason - see
    resolve_app_label()'s docstring). Callers extracting a public app must
    pass a namespaced `app_name` (e.g. "public_core") and the real
    `folder_name` ("core") separately."""
    graph = schema.Graph()
    app_dir = project_root / "apps" / schema_root / (folder_name or app_name)
    app_label = resolve_app_label(app_name, project_root, schema_root, folder_name)

    graph.add_node(
        schema.Node(
            schema.application_id(app_name),
            schema.NODE_APPLICATION,
            # Explicit False, not just "key absent" - same fix, same reason,
            # as the real ViewSet node fix above: another app's Service
            # extraction can create an `external: True` Application stub
            # for THIS app (see the "other_app_node_id" stub a few hundred
            # lines up) when it references a cross-app Service by receiver
            # name; without this, merge order could silently downgrade a
            # real Application back to looking external.
            {
                "name": app_name,
                "app_label": app_label,
                "external": False,
                "schema": schema_root,
                "folder": folder_name or app_name,
            },
        )
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
