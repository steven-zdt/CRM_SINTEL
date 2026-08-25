"""
EKG governance rules (Fase 7 of the spec): "no permitir X", scoped strictly
to what's honestly checkable from data the extractors *already* populate -
BELONGS_TO/INHERITS/USES + node path/name properties - without any new
control-flow/semantic extractor. Every rule here cites the exact
documentacion/arquitectura_general.md / AGENTS.md section it enforces and
is traceable to a real Cypher-equivalent graph query; none is invented.

Deliberately NOT implemented here - would require new static analysis this
pilot's extractors don't do (see tools/ekg/validate.py's own docstring for
the same boundary drawn from the "graph integrity" side):
  - "ViewSet/queryset has no empresa_id filter" / "no .only()" - the
    extractors don't parse queryset method-chain bodies at all.
  - "Service performs DSV" - DSV is a runtime validation pattern inside a
    method body, not a structural relationship between two classes.
  - "Endpoint has no permission_classes" - permission classes are never
    extracted as graph data today (ViewSet.properties has no such field).
  - "no Signals for business logic" - signal registration/connection isn't
    parsed by extract_python.py at all.
  - "consultas N+1" - requires runtime query-plan analysis, not statics.
A governance report that silently guessed at these would violate the one
rule that matters most here: never claim a check the graph cannot back up.

Implemented rules:
  - viewsets_without_service_layer    (arquitectura_general.md Sec 4.2: "El
                                        ViewSet es un enrutador HTTP puro...
                                        Toda logica de negocio vive en el
                                        Service Layer" - a ViewSet with zero
                                        USES edge to any Service node never
                                        delegates to one)
  - models_not_inheriting_tenant_base (Sec 3.2 / AGENTS.md "Herencia
                                        Obligatoria de Modelos SSoT": every
                                        tenant model must inherit
                                        SintelTenantBaseModel, directly or
                                        transitively - walks INHERITS, not
                                        just a direct-base string compare,
                                        so an abstract app-local intermediate
                                        base still counts)
  - js_outside_own_app_static_path    (Sec 5.2: JS estatico tenant vive en
                                        apps/tenant/<app>/static/<app>/js/)
  - templates_outside_own_app_path    (Sec 5.2: mismo principio para
                                        templates)
  - sede_or_area_field_without_sede_aware_model (OCF Fase 11 / ADR-003 §
                                        "SedeAwareModel": un modelo tenant con
                                        un campo `sede`/`area` (FK real hacia
                                        empresa.Sede/Area, no cualquier campo
                                        con ese nombre) deberia heredar
                                        SedeAwareModel en vez de redeclarar el
                                        FK a mano - walks INHERITS igual que
                                        la regla de SintelTenantBaseModel.
                                        NO es un rollout forzado: los hits de
                                        esta regla son, a la fecha de este
                                        commit, el checklist en vivo del
                                        rollout de ADR-003 pendiente (Fase 9
                                        del proyecto OCF documento 6 apps con
                                        `sede` FK preexistente al mixin,
                                        migradas antes de que SedeAwareModel
                                        existiera) - no bugs nuevos.

Fase 11 tambien evaluo, y descarto explicitamente, una segunda regla pedida
por el propio proyecto OCF: "todo ViewSet con minimum_organizational_level
debe usar OrganizationalPermission". Verificado que HOY minimum_organizational_level
no esta seteado en ningun ViewSet real (solo aparece en
apps/tenant/api/permissions.py, que lo define, y en su propio test) -
implementar esa regla exigiria primero extender extract_python.py para
capturar permission_classes/atributos de clase arbitrarios (hoy
deliberadamente fuera de alcance, ver arriba "Endpoint has no
permission_classes"), solo para gobernar cero usos reales - exactamente el
tipo de infraestructura especulativa que este proyecto evito en cada fase
anterior. Queda documentado, no implementado, hasta que exista al menos un
ViewSet real que la necesite.

  - import_cycles_between_tenant_apps (OSF Fase F16, "gobernanza automatica
                                        ampliada", ultima fase del proyecto
                                        Organizational Scope Framework;
                                        mapea el item "Import circular" del
                                        roadmap original de F16 -
                                        documentacion/Nueva recomendación
                                        arquitectónica.md - al unico check
                                        de ese item honestamente respaldable
                                        por el grafo hoy: ciclos en las
                                        aristas IMPORTS App->App que
                                        extract_services() ya popula para
                                        imports `apps.tenant.<otra_app>`
                                        dentro de services/. AGENTS.md §17
                                        BRIDGE exige que las apps tenant se
                                        comuniquen via Bridges/Soft
                                        References (UUID + lookup), nunca
                                        import mutuo directo de sus modulos
                                        de servicio - un ciclo A<->B es
                                        precisamente lo que ese patron existe
                                        para evitar. Cero extractor nuevo:
                                        reusa aristas IMPORTS ya existentes,
                                        DFS de 3 colores estandar.

El resto del wishlist original de F16 (documentacion/Nueva recomendación
arquitectónica.md, "FASE 16 - GOBERNANZA AUTOMATICA") - "Query sin scope",
"Service ignorando sede", "Usuario accediendo a sede no autorizada", "Área
fuera de la sede permitida", "DTO inter-app sin contexto", "Bridge sin
aislamiento" (a nivel semantico, no de import) - son exactamente la
categoria de check "queryset/service ejecuta X en tiempo de ejecucion" que
este modulo ya declina arriba por principio ("never claim a check the graph
cannot back up"): no son relaciones estructurales entre nodos, son
comportamiento dentro de un cuerpo de metodo. Esos invariantes SI estan
gobernados hoy - no por este modulo, sino por la suite de tests dedicada
construida en OSF F14 (apps/tenant/*/tests/test_scope_isolation_f14.py +
test_scope_object_level_f13.py + test_scope_facturas_f11.py, etc.), que los
verifica en tiempo de ejecucion contra las 6 apps candidatas fuertes. F16
cierra el proyecto documentando esa division de responsabilidad
explicitamente en vez de fingir una cobertura estatica que no existe.

CLI: python -m tools.ekg.governance [--offline | --live]
Both merge/query the full 17-app graph (not one app at a time) since a
governance sweep is only meaningful project-wide.
"""

from __future__ import annotations

import argparse
import sys

from tools.ekg import schema
from tools.ekg.impact import load_full_offline_graph

TENANT_BASE_MODEL_NAME = "SintelTenantBaseModel"
# Models that are legitimately exempt from Sec 3.2 - the base itself, and
# any external stub (this pilot didn't extract that app, so it cannot know
# whether the stub inherits the base or not; flagging it would be a guess,
# not a finding - see module docstring's "never claim a check the graph
# cannot back up").
_EXEMPT_MODEL_NAME_PREFIXES = (TENANT_BASE_MODEL_NAME,)


def _tenant_app_ids(graph: schema.Graph) -> set[str]:
    """Application ids whose `schema` property is "tenant" (or absent, for
    a dump extracted before apps/public/* coverage added that property -
    defaults to the only convention that existed then). Used to scope
    tenant-only architectural rules (SintelTenantBaseModel inheritance,
    Service Layer usage) away from apps/public/* models/ViewSets, which
    the architecture doc (Sec 3.2/4.2) never states are held to either
    requirement - `impuestos`/`accounts`/`tenants`/`console` are a
    different, shared-schema part of the system with its own (undocumented
    here, not assumed) conventions. Found necessary immediately: the very
    first run against the merged 22-app graph flagged 19 public models and
    24 public ViewSets that were never a real finding, just the wrong rule
    applied to the wrong schema."""
    return {
        app_id for app_id, node in graph.nodes.items()
        if node.label == schema.NODE_APPLICATION and node.properties.get("schema", "tenant") == "tenant"
    }


def _belongs_to_tenant_app(graph: schema.Graph, node_id: str, tenant_app_ids: set[str]) -> bool:
    return any(
        e.target_id in tenant_app_ids
        for e in graph.edges
        if e.source_id == node_id and e.rel_type == schema.REL_BELONGS_TO
    )


def find_viewsets_without_service_layer(graph: schema.Graph) -> list[str]:
    tenant_app_ids = _tenant_app_ids(graph)
    uses_service_sources = {
        e.source_id
        for e in graph.edges
        if e.rel_type == schema.REL_USES
        and graph.nodes.get(e.target_id, schema.Node("", schema.NODE_APPLICATION)).label
        == schema.NODE_SERVICE
    }
    inherits_by_source: dict[str, list[str]] = {}
    for e in graph.edges:
        if e.rel_type == schema.REL_INHERITS:
            inherits_by_source.setdefault(e.source_id, []).append(e.target_id)

    def _uses_service_transitively(node_id: str, seen: set[str]) -> bool:
        # The ADR-002 public/tenant dual-registration pattern (e.g.
        # apps/tenant/core/api/v1/contabilidad/viewsets.py's
        # CuentaContableCoreViewSet(CuentaContableViewSet)) inherits the
        # real tenant ViewSet wholesale instead of re-declaring its own
        # USES edge to a Service - a direct-USES-only check flagged every
        # one of these Core facades as a false positive (36 of them,
        # confirmed by reading several in full before trusting this rule).
        if node_id in uses_service_sources:
            return True
        if node_id in seen:
            return False
        seen.add(node_id)
        return any(_uses_service_transitively(t, seen) for t in inherits_by_source.get(node_id, []))

    violations = []
    for node_id, node in graph.nodes.items():
        if node.label != schema.NODE_VIEWSET:
            continue
        if node.properties.get("external"):
            continue
        if node.properties.get("kind") != schema.VIEWSET_KIND_VIEWSET:
            continue  # plain APIViews/mixins are not the "CRUD ViewSet" this rule targets
        if not _belongs_to_tenant_app(graph, node_id, tenant_app_ids):
            continue  # Sec 4.2's Service Layer mandate is stated for tenant apps only
        if _uses_service_transitively(node_id, set()):
            continue
        violations.append(f"{node.properties.get('name')} ({node.properties.get('defined_in', node_id)})")
    return sorted(violations)


def find_models_not_inheriting_tenant_base(graph: schema.Graph) -> list[str]:
    tenant_app_ids = _tenant_app_ids(graph)
    base_ids = {
        n.id for n in graph.nodes.values()
        if n.label == schema.NODE_MODEL and n.properties.get("name") == TENANT_BASE_MODEL_NAME
    }
    if not base_ids:
        return ["ERROR: SintelTenantBaseModel node not found in graph - is `core` app merged in?"]

    inherits_by_source: dict[str, list[str]] = {}
    for e in graph.edges:
        if e.rel_type == schema.REL_INHERITS:
            inherits_by_source.setdefault(e.source_id, []).append(e.target_id)

    def _reaches_base(node_id: str, seen: set[str]) -> bool:
        if node_id in base_ids:
            return True
        if node_id in seen:
            return False  # inheritance cycle guard, should never happen for real Django models
        seen.add(node_id)
        return any(_reaches_base(target, seen) for target in inherits_by_source.get(node_id, []))

    violations = []
    for node_id, node in graph.nodes.items():
        if node.label != schema.NODE_MODEL:
            continue
        if node.properties.get("external"):
            continue
        if not node.properties.get("defined_in"):
            # Unresolved placeholder, not a real extracted model: created by
            # resolve_model_target() for a same-app FK/Meta.model reference
            # seen before that class's own definition was reached in this
            # pass (see its docstring) - this pass never saw a real class
            # definition for it, so reporting it as "doesn't inherit the
            # base" would be a guess, not a finding - see module docstring.
            continue
        if not _belongs_to_tenant_app(graph, node_id, tenant_app_ids):
            continue  # Sec 3.2's SintelTenantBaseModel mandate is stated for tenant-schema models only
        name = node.properties.get("name", "")
        if any(name == prefix for prefix in _EXEMPT_MODEL_NAME_PREFIXES):
            continue
        if _reaches_base(node_id, set()):
            continue
        violations.append(f"{node.properties.get('app_label')}.{name} ({node.properties.get('defined_in', node_id)})")
    return sorted(violations)


def _path_violates_own_app(path: str, app_node: schema.Node, expected_infix: str) -> bool:
    """Uses the Application node's own `schema`/`folder` properties (set by
    extract_app_python() - see its docstring) rather than assuming
    apps/tenant/ - apps/public/* apps are extracted under a namespaced
    `name` (e.g. "public_core") that never matches the real on-disk
    `folder` ("core"), so building the expected path from `name` alone
    would falsely flag every public app's own JS as misplaced. Apps
    extracted before this property existed (none as of this writing, but
    defensive) fall back to "tenant"/`name` - the only convention that
    existed before apps/public/* coverage was added."""
    schema_root = app_node.properties.get("schema", "tenant")
    folder = app_node.properties.get("folder", app_node.properties.get("name", ""))
    expected_prefix = f"apps/{schema_root}/{folder}/{expected_infix}"
    return not path.startswith(expected_prefix)


def find_js_outside_own_app_static_path(graph: schema.Graph) -> list[str]:
    violations = []
    for node_id, node in graph.nodes.items():
        if node.label != schema.NODE_JS or node.properties.get("external"):
            continue
        path = node.properties.get("path", "")
        app_ids = [e.target_id for e in graph.edges if e.source_id == node_id and e.rel_type == schema.REL_BELONGS_TO]
        for app_id in app_ids:
            app_node = graph.nodes.get(app_id)
            if app_node is None:
                continue
            app_name = app_node.properties.get("name", "")
            folder = app_node.properties.get("folder", app_name)
            if _path_violates_own_app(path, app_node, f"static/{folder}/js/"):
                violations.append(f"{path} (belongs_to={app_name})")
    return sorted(set(violations))


def find_templates_outside_own_app_path(graph: schema.Graph) -> list[str]:
    violations = []
    for node_id, node in graph.nodes.items():
        if node.label != schema.NODE_TEMPLATE or node.properties.get("external"):
            continue
        path = node.properties.get("path", "")
        app_ids = [e.target_id for e in graph.edges if e.source_id == node_id and e.rel_type == schema.REL_BELONGS_TO]
        for app_id in app_ids:
            app_node = graph.nodes.get(app_id)
            if app_node is None:
                continue
            app_name = app_node.properties.get("name", "")
            folder = app_node.properties.get("folder", app_name)
            # "templates/tenant/<app>/" - the inner "tenant" is a literal
            # subfolder convention (arquitectura_general.md Sec 4.1), not
            # the schema_root; templates are only extracted for schema_root
            # == "tenant" apps at all (see build_app_graph()'s docstring),
            # so this branch is never reached for a public app in practice.
            if _path_violates_own_app(path, app_node, f"templates/tenant/{folder}/"):
                violations.append(f"{path} (belongs_to={app_name})")
    return sorted(set(violations))


SEDE_AWARE_MODEL_NAME = "SedeAwareModel"
# Sede/Area organizational FK targets - a field is only "organizational" if
# it actually references one of these two models (a field merely NAMED
# "sede"/"area" that points elsewhere, e.g. a future non-organizational
# reuse of the name, would not be a real hit - none exist today, verified
# by grepping every `sede =`/`area =` model field before writing this rule).
_ORGANIZATIONAL_FIELD_NAMES = ("sede", "area")
# Empresa/Sede/Area *are* the hierarchy definition, not consumers of it:
# Area.sede is the intrinsic "which Sede owns this Area" structural FK, not
# an opt-in to sede-scoped business data - flagging Area itself would be a
# false positive, found on first run of this rule (2026-08-08).
_HIERARCHY_MODEL_NAME_EXEMPTIONS = ("Empresa", "Sede", "Area")


def models_with_organizational_sede_or_area_field(graph: schema.Graph) -> set[str]:
    """Model node ids (tenant apps only, hierarchy models exempted) that
    declare a real `sede`/`area` FK to `empresa.Sede`/`Area` - the
    population `find_sede_or_area_field_without_sede_aware_model()` checks
    for SedeAwareModel compliance. Exported separately (not just inlined in
    that function) so platform.py's compliance_summary() can report a
    percentage against the same denominator the rule itself uses, instead
    of guessing a population independently and risking the two silently
    drifting apart."""
    tenant_app_ids = _tenant_app_ids(graph)

    # Field:<app>.<Model>.<field_name> -> the Model node id it belongs to,
    # so a HAS_FIELD hit can be walked back to check the owning model's
    # inheritance chain.
    model_of_field: dict[str, str] = {}
    for e in graph.edges:
        if e.rel_type == schema.REL_HAS_FIELD:
            model_of_field[e.target_id] = e.source_id

    organizational_field_targets: set[str] = set()
    for e in graph.edges:
        if e.rel_type != schema.REL_REFERENCES:
            continue
        field_node = graph.nodes.get(e.source_id)
        if field_node is None or field_node.label != schema.NODE_FIELD:
            continue
        field_name = field_node.properties.get("name", "")
        target_node = graph.nodes.get(e.target_id)
        target_name = target_node.properties.get("name", "") if target_node else ""
        if field_name in _ORGANIZATIONAL_FIELD_NAMES and target_name in ("Sede", "Area"):
            organizational_field_targets.add(e.source_id)

    models: set[str] = set()
    for field_id in organizational_field_targets:
        model_id = model_of_field.get(field_id)
        if model_id is None:
            continue
        model_node = graph.nodes.get(model_id)
        if model_node is None or model_node.properties.get("external"):
            continue
        name = model_node.properties.get("name", "")
        if name in _HIERARCHY_MODEL_NAME_EXEMPTIONS or name == SEDE_AWARE_MODEL_NAME:
            continue
        if not _belongs_to_tenant_app(graph, model_id, tenant_app_ids):
            continue
        models.add(model_id)
    return models


def find_sede_or_area_field_without_sede_aware_model(graph: schema.Graph) -> list[str]:
    base_ids = {
        n.id for n in graph.nodes.values()
        if n.label == schema.NODE_MODEL and n.properties.get("name") == SEDE_AWARE_MODEL_NAME
    }
    if not base_ids:
        return ["ERROR: SedeAwareModel node not found in graph - is `core` app merged in?"]

    inherits_by_source: dict[str, list[str]] = {}
    for e in graph.edges:
        if e.rel_type == schema.REL_INHERITS:
            inherits_by_source.setdefault(e.source_id, []).append(e.target_id)

    def _reaches_sede_aware(node_id: str, seen: set[str]) -> bool:
        if node_id in base_ids:
            return True
        if node_id in seen:
            return False
        seen.add(node_id)
        return any(_reaches_sede_aware(target, seen) for target in inherits_by_source.get(node_id, []))

    violations = []
    for model_id in models_with_organizational_sede_or_area_field(graph):
        if model_id in base_ids or _reaches_sede_aware(model_id, set()):
            continue
        model_node = graph.nodes[model_id]
        name = model_node.properties.get("name", "")
        app_label = model_node.properties.get("app_label", "")
        violations.append(f"{app_label}.{name} ({model_node.properties.get('defined_in', model_id)})")
    return sorted(violations)


def find_import_cycles_between_tenant_apps(graph: schema.Graph) -> list[str]:
    """OSF Fase F16 ("gobernanza automatica ampliada", ultima fase del
    proyecto): detecta ciclos de import entre apps tenant a nivel de
    services/ (arquitectura_general.md / AGENTS.md §17 BRIDGE: las apps
    tenant deben comunicarse via Bridges/Soft References - UUID + lookup en
    tiempo de ejecucion -, nunca via import directo mutuo de sus modulos de
    servicio; un ciclo A importa de B y B importa de A es precisamente lo
    que ese patron existe para evitar).

    Usa unicamente aristas IMPORTS ya pobladas por extract_services()
    (apps.tenant.<app> imports dentro de services/, ver
    extract_python.py:_cross_tenant_app_from_module) - cero extractor
    nuevo, mismo criterio que el resto de este modulo ("nunca reclamar un
    check que el grafo no pueda respaldar"). Deteccion de ciclos via DFS de
    3 colores sobre el subgrafo App->App inducido por IMPORTS.
    """
    app_edges: dict[str, set[str]] = {}
    for e in graph.edges:
        if e.rel_type != schema.REL_IMPORTS:
            continue
        src = graph.nodes.get(e.source_id)
        dst = graph.nodes.get(e.target_id)
        if src is None or dst is None:
            continue
        if src.label != schema.NODE_APPLICATION or dst.label != schema.NODE_APPLICATION:
            continue
        app_edges.setdefault(e.source_id, set()).add(e.target_id)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {}
    cycles: list[list[str]] = []

    def _app_name(app_id: str) -> str:
        node = graph.nodes.get(app_id)
        return node.properties.get("name", app_id) if node else app_id

    def _dfs(node_id: str, stack: list[str]) -> None:
        color[node_id] = GRAY
        stack.append(node_id)
        for target in sorted(app_edges.get(node_id, ())):
            if color.get(target, WHITE) == WHITE:
                _dfs(target, stack)
            elif color.get(target) == GRAY:
                cycle_start = stack.index(target)
                cycles.append(stack[cycle_start:] + [target])
        stack.pop()
        color[node_id] = BLACK

    for app_id in sorted(app_edges):
        if color.get(app_id, WHITE) == WHITE:
            _dfs(app_id, [])

    violations = sorted({" -> ".join(_app_name(a) for a in cycle) for cycle in cycles})
    return violations


def run(graph: schema.Graph) -> int:
    checks = {
        "viewsets_without_service_layer": find_viewsets_without_service_layer(graph),
        "models_not_inheriting_tenant_base": find_models_not_inheriting_tenant_base(graph),
        "js_outside_own_app_static_path": find_js_outside_own_app_static_path(graph),
        "templates_outside_own_app_path": find_templates_outside_own_app_path(graph),
        "sede_or_area_field_without_sede_aware_model": find_sede_or_area_field_without_sede_aware_model(graph),
        "import_cycles_between_tenant_apps": find_import_cycles_between_tenant_apps(graph),
    }

    print(f"EKG governance sweep: {graph.node_count()} nodes, {graph.edge_count()} edges\n")
    print("(see tools/ekg/governance.py module docstring for rules deliberately NOT implemented)\n")
    total_violations = 0
    for name, issues in checks.items():
        status = "FAIL" if issues else "OK"
        print(f"[{status}] {name}: {len(issues)}")
        for issue in issues:
            print(f"    - {issue}")
        total_violations += len(issues)

    return 1 if total_violations else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the EKG governance sweep across all 17 pilot apps.")
    parser.add_argument("--offline", action="store_true", help="Merge JSON dumps under tools/ekg/out/ (default)")
    args = parser.parse_args()
    del args  # only one mode implemented today - see module docstring for why --live isn't (yet)

    graph = load_full_offline_graph()
    sys.exit(run(graph))


if __name__ == "__main__":
    main()
