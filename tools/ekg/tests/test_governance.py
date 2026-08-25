from pathlib import Path

from tools.ekg import schema
from tools.ekg.build_graph import build_app_graph
from tools.ekg.governance import (
    find_import_cycles_between_tenant_apps,
    find_js_outside_own_app_static_path,
    find_models_not_inheriting_tenant_base,
    find_sede_or_area_field_without_sede_aware_model,
    find_templates_outside_own_app_path,
    find_viewsets_without_service_layer,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _merged(*apps: str) -> schema.Graph:
    graph = schema.Graph()
    for app in apps:
        if app.startswith("public_"):
            folder = app[len("public_") :]
            graph.merge(build_app_graph(app, PROJECT_ROOT, schema_root="public", folder_name=folder))
        else:
            graph.merge(build_app_graph(app, PROJECT_ROOT))
    return graph


def test_textchoices_class_is_not_flagged_as_a_model():
    """apps/tenant/perfil/models.py's RolTenant(models.TextChoices) is a
    plain enum of string constants, not a Django Model - it must not even
    be created as a Model node (so it can't spuriously fail the "inherits
    SintelTenantBaseModel" check, and doesn't pollute any other Model-based
    query either). Confirmed as a real extractor false positive - not an
    architecture violation - by reading the source before writing this
    exclusion; see extract_python.py's _NON_MODEL_BASE_NAMES."""
    graph = _merged("perfil")
    assert schema.model_id("perfil", "RolTenant") not in graph.nodes


def test_bare_cross_app_fk_reference_resolves_to_the_real_model_id():
    """empleados' `empresa = ForeignKey(Empresa, ...)` (a bare imported
    identifier, after `from apps.tenant.empresa.models import Empresa` -
    not the dotted "app_label.Model" string form) used to resolve as if
    Empresa were defined in the SAME app as the subclass, producing a
    wrongly-namespaced, never-merging placeholder (`Model:tenant_empleados.
    Empresa`) instead of the one real `Model:empresa.Empresa` - the same
    class of bug fixed for INHERITS, here in resolve_model_target(). Once
    fixed, the wrong id must not exist at all, and the correct one must be
    a genuine external stub (empresa itself not merged in) that resolves
    once it is - mirroring test_build_graph.py's cross-app FK stub test."""
    graph = _merged("empleados")
    wrong_id = schema.model_id("tenant_empleados", "Empresa")
    assert wrong_id not in graph.nodes

    real_id = schema.model_id("empresa", "Empresa")
    assert graph.nodes[real_id].properties["external"] is True

    graph.merge(build_app_graph("empresa", PROJECT_ROOT))
    assert graph.nodes[real_id].properties["external"] is False


def test_models_not_inheriting_tenant_base_excludes_unresolved_placeholders():
    """A genuinely unresolved same-app placeholder (a self-referential FK
    seen before its own class definition, still the one remaining case
    with no `defined_in` - see resolve_model_target()) must never be
    reported as "doesn't inherit the base": this pass never saw a real
    class definition for it, so flagging it would be a guess, not a
    finding."""
    graph = _merged("compras", "core")
    unresolved = [
        n for n in graph.nodes.values()
        if n.label == schema.NODE_MODEL and not n.properties.get("defined_in") and not n.properties.get("external")
    ]
    violations = find_models_not_inheriting_tenant_base(graph)
    for node in unresolved:
        assert not any(node.properties.get("name", "\0") in v for v in violations)


def test_models_not_inheriting_tenant_base_on_a_clean_app():
    """compras' own models (OrdenCompra, ItemOrdenCompra, PlantillaOrdenCompra)
    all correctly inherit SintelTenantBaseModel once `core` is merged in -
    this is the "OK" case the rule must not false-positive on."""
    graph = _merged("compras", "core")
    violations = find_models_not_inheriting_tenant_base(graph)
    assert not any("compras" in v for v in violations)


def test_viewset_service_layer_check_follows_inherits_transitively():
    """apps/tenant/core/api/v1/contabilidad/viewsets.py's
    CuentaContableCoreViewSet(CuentaContableViewSet) is the ADR-002 public/
    tenant dual-registration pattern - it inherits the real tenant ViewSet
    wholesale rather than re-declaring its own USES edge to a Service. A
    direct-USES-only check flagged this (and 12 siblings) as false
    positives before this rule walked INHERITS transitively - confirmed by
    reading the source (a thin get_serializer_class() override, nothing
    else) before trusting the fix."""
    graph = _merged("core", "contabilidad")
    violations = find_viewsets_without_service_layer(graph)
    assert not any("CuentaContableCoreViewSet" in v for v in violations)


def test_tenant_only_rules_do_not_flag_public_schema_models_or_viewsets():
    """SintelTenantBaseModel inheritance (Sec 3.2) and Service Layer usage
    (Sec 4.2) are both stated in the architecture doc as tenant-app
    requirements - apps/public/* (impuestos, accounts, tenants, console)
    are a different, shared-schema part of the system with its own,
    undocumented-here conventions. The very first run against the merged
    22-app graph flagged 19 public models and 24 public ViewSets before
    this scoping fix - none of them a real finding, just the wrong rule
    applied to the wrong schema."""
    graph = _merged("core", "public_impuestos", "public_accounts")
    model_violations = find_models_not_inheriting_tenant_base(graph)
    viewset_violations = find_viewsets_without_service_layer(graph)

    assert not any("public_impuestos" in v or "public_accounts" in v for v in model_violations)
    assert not any("impuestos" in v.lower() or "accounts" in v.lower() for v in viewset_violations)


def test_js_and_template_namespace_rules_pass_on_a_clean_app():
    """Both rules must report zero violations for a real, compliant app -
    proves the rule isn't trivially vacuous (e.g. never matching anything
    due to a path-format mismatch) as well as proving compras is compliant."""
    graph = build_app_graph("compras", PROJECT_ROOT)
    assert find_js_outside_own_app_static_path(graph) == []
    assert find_templates_outside_own_app_path(graph) == []


def test_sede_or_area_rule_does_not_flag_the_migrated_pilot():
    """compras.OrdenCompra (ADR-003 pilot) inherits SedeAwareModel instead
    of redeclaring `sede` by hand - the rule must recognize this as
    compliant, not just detect the non-compliant case."""
    graph = _merged("compras", "core")
    violations = find_sede_or_area_field_without_sede_aware_model(graph)
    assert not any("OrdenCompra" in v for v in violations)


def test_sede_or_area_rule_flags_a_preexisting_sede_field_not_yet_migrated():
    """gastos.DocumentoSoporte has a real `sede` FK to empresa.Sede
    (DT-SEDE-0X tag, predates SedeAwareModel) but still inherits
    SintelTenantBaseModel directly - a real, known, not-yet-migrated case
    (ADR-003 rollout pending), not a false positive."""
    graph = _merged("gastos", "core", "empresa")
    violations = find_sede_or_area_field_without_sede_aware_model(graph)
    assert any("DocumentoSoporte" in v for v in violations)


def test_sede_or_area_rule_does_not_flag_the_hierarchy_models_themselves():
    """empresa.Area has its own `sede` FK (which Sede owns this Area - the
    hierarchy definition itself), not an opt-in to sede-scoped business
    data. Flagging Area/Sede/Empresa would be a false positive - found on
    the first real run of this rule before this exemption was added."""
    graph = _merged("empresa", "core")
    violations = find_sede_or_area_field_without_sede_aware_model(graph)
    assert not any(v.startswith("empresa.Area") or v.startswith("empresa.Sede") for v in violations)


def test_import_cycle_rule_detects_a_synthetic_two_app_cycle():
    """Algorithm-level check independent of current real app state (so this
    test stays meaningful even if the real cycle below is ever refactored
    away): a minimal App-App-IMPORTS graph with a deliberate A<->B cycle
    must be detected by the DFS."""
    graph = schema.Graph()
    app_a = schema.application_id("app_a")
    app_b = schema.application_id("app_b")
    app_c = schema.application_id("app_c")
    graph.add_node(schema.Node(app_a, schema.NODE_APPLICATION, {"name": "app_a"}))
    graph.add_node(schema.Node(app_b, schema.NODE_APPLICATION, {"name": "app_b"}))
    graph.add_node(schema.Node(app_c, schema.NODE_APPLICATION, {"name": "app_c"}))
    graph.add_edge(schema.Edge(app_a, app_b, schema.REL_IMPORTS))
    graph.add_edge(schema.Edge(app_b, app_a, schema.REL_IMPORTS))
    graph.add_edge(schema.Edge(app_a, app_c, schema.REL_IMPORTS))  # acyclic edge, must not spuriously report a_c cycle

    violations = find_import_cycles_between_tenant_apps(graph)

    assert violations == ["app_a -> app_b -> app_a"]


def test_import_cycle_rule_finds_the_real_core_empresa_perfil_cycles():
    """OSF Fase F16: real, known finding (evaluated, not fixed - see
    governance.py module docstring) - `core`/`empresa`/`perfil` (foundational
    apps) cross-import each other's *models* (Empresa/TenantProfile/Area,
    never a Service class) from within services/ files, forming 2 real
    cycles. Confirms the rule fires on real data, not just the synthetic
    case above."""
    graph = _merged("core", "empresa", "perfil")
    violations = find_import_cycles_between_tenant_apps(graph)
    assert any(v == "empresa -> perfil -> empresa" for v in violations)
    assert any(v.startswith("core -> empresa -> perfil -> core") for v in violations)
