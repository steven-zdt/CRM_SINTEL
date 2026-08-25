"""
Runs the Python extractor against the real apps/tenant/compras source (not
fixtures) so these assertions double as a correctness proof of the pilot
graph, cross-checked against the ground truth gathered by hand while
building this pipeline (see tools/ekg/PILOT_REPORT.md).
"""

from pathlib import Path

from tools.ekg import schema
from tools.ekg.extract_python import extract_app_python, resolve_app_label

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _graph():
    return extract_app_python("compras", PROJECT_ROOT)


def test_app_label_resolution_matches_real_django_labels():
    """Roughly half of apps/tenant/* override AppConfig.label with
    "tenant_<name>" and half keep Django's bare default - discovered while
    spot-checking the ventas rollout (ventas.Venta.factura_asociada points
    at "facturas.Factura", and facturas does not set label = "tenant_facturas").
    This pins both cases so the app_label resolver can't silently regress
    back to the "tenant_<app_name>" assumption for either kind."""
    assert resolve_app_label("compras", PROJECT_ROOT) == "tenant_compras"
    assert resolve_app_label("facturas", PROJECT_ROOT) == "facturas"


def test_models_and_fields():
    """Model ids are keyed by the real Django app_label ("tenant_compras"),
    not the apps/tenant/<folder> name - see resolve_model_target()'s
    docstring for why (cross-app FK resolution depends on it)."""
    graph = _graph()
    orden_compra = graph.nodes[schema.model_id("tenant_compras", "OrdenCompra")]
    assert orden_compra.label == schema.NODE_MODEL

    field = graph.nodes[schema.field_id("compras", "OrdenCompra", "proveedor")]
    assert field.properties["type"] == "ForeignKey"


def test_fk_targets_resolve_to_external_stubs():
    graph = _graph()
    field_id = schema.field_id("compras", "OrdenCompra", "proveedor")
    refs = [e for e in graph.edges if e.source_id == field_id and e.rel_type == schema.REL_REFERENCES]
    assert len(refs) == 1
    target = graph.nodes[refs[0].target_id]
    assert target.properties["name"] == "Proveedor"
    assert target.properties["app_label"] == "tenant_proveedores"
    assert target.properties["external"] is True
    assert target.id == schema.model_id("tenant_proveedores", "Proveedor")


def test_fk_target_within_same_app_is_not_a_stub():
    graph = _graph()
    field_id = schema.field_id("compras", "OrdenCompra", "plantilla")
    refs = [e for e in graph.edges if e.source_id == field_id and e.rel_type == schema.REL_REFERENCES]
    assert len(refs) == 1
    target = graph.nodes[refs[0].target_id]
    assert target.id == schema.model_id("tenant_compras", "PlantillaOrdenCompra")
    assert target.properties["external"] is False


def test_business_service_calls_crud_service():
    graph = _graph()
    business_id = schema.service_id("compras", "business_service", "OrdenCompraBusinessService")
    crud_id = schema.service_id("compras", "crud_service", "OrdenCompraCRUDService")
    calls = [
        e for e in graph.edges
        if e.source_id == business_id and e.target_id == crud_id and e.rel_type == schema.REL_CALLS
    ]
    assert len(calls) == 1
    assert "crear_orden" in calls[0].properties["methods"]


def test_mixin_uses_business_service_via_class_attribute_injection():
    """apps/tenant/compras/services/api_mixins.py wires OrdenCompraServiceMixin
    to OrdenCompraBusinessService via `business_service_class =
    OrdenCompraBusinessService` (class-attribute injection), not a method
    call - a plain call-scan never sees this, which made every CRUD/Business
    service in the app look like dead code when audited via the graph
    (found running a real dead-code audit; OrdenCompraBusinessService is
    demonstrably live). See extract_services()'s SERVICE_KIND_MIXIN branch."""
    graph = _graph()
    mixin_id = schema.service_id("compras", "api_mixins", "OrdenCompraServiceMixin")
    business_id = schema.service_id("compras", "business_service", "OrdenCompraBusinessService")
    crud_id = schema.service_id("compras", "crud_service", "OrdenCompraCRUDService")
    selector_id = schema.service_id("compras", "selectors", "OrdenCompraSelector")
    uses_targets = {e.target_id for e in graph.edges if e.source_id == mixin_id and e.rel_type == schema.REL_USES}
    assert business_id in uses_targets
    assert crud_id in uses_targets
    assert selector_id in uses_targets


def test_viewset_uses_its_serializers():
    graph = _graph()
    viewset_id = schema.viewset_id("compras", "OrdenCompraViewSet")
    used_serializer_names = {
        graph.nodes[e.target_id].properties.get("name")
        for e in graph.edges
        if e.source_id == viewset_id and e.rel_type == schema.REL_USES
        and graph.nodes[e.target_id].label == schema.NODE_SERIALIZER
    }
    assert {"OrdenCompraListSerializer", "OrdenCompraDetailSerializer", "OrdenCompraCreateUpdateSerializer"} <= used_serializer_names


def test_serializer_meta_model_edge():
    graph = _graph()
    serializer_id = schema.serializer_id("compras", "OrdenCompraListSerializer")
    model_edges = [
        e for e in graph.edges
        if e.source_id == serializer_id and e.rel_type == schema.REL_USES
        and graph.nodes[e.target_id].label == schema.NODE_MODEL
    ]
    assert any(graph.nodes[e.target_id].id == schema.model_id("tenant_compras", "OrdenCompra") for e in model_edges)


def test_router_endpoint_extracted_with_correct_route():
    graph = _graph()
    endpoint = graph.nodes[schema.endpoint_id("compras", "plantillas", "api")]
    assert endpoint.properties["route"] == "plantillas"
    exposes = [
        e for e in graph.edges
        if e.target_id == endpoint.id and e.rel_type == schema.REL_EXPOSES
    ]
    assert graph.nodes[exposes[0].source_id].id == schema.viewset_id("compras", "PlantillaOrdenCompraViewSet")


def test_defined_in_is_relative_not_absolute():
    """PROJECT_ROOT in build_graph.py is always an absolute path, so every
    "defined_in" property was silently baking in the machine-specific
    absolute path (this machine's Windows path here, `/app` inside the
    Docker container in production) until extract_python.py's four
    `defined_in`-emitting extractors were threaded with `project_root` to
    make it relative. Found while extracting the `core` app (see
    PILOT_REPORT.md's spot-check #12) - the earlier apps' dry-run JSON had
    this bug too, just unnoticed because ad-hoc test scripts during this
    rollout mostly called build_app_graph with a relative `Path('.')`."""
    graph = _graph()
    orden_compra = graph.nodes[schema.model_id("tenant_compras", "OrdenCompra")]
    defined_in = orden_compra.properties["defined_in"]
    assert not Path(defined_in.split(":")[0]).is_absolute()
    assert defined_in == "apps/tenant/compras/models.py:90"


def test_no_dangling_edges():
    graph = _graph()
    for edge in graph.edges:
        assert edge.source_id in graph.nodes, f"dangling source: {edge}"
        assert edge.target_id in graph.nodes, f"dangling target: {edge}"


def test_model_inherits_cross_app_base_via_import_resolution():
    """OrdenCompra(SedeAwareModel) - the base is imported from
    apps.tenant.core.models, a different app than compras. Before this fix,
    extract_models() only ever resolved a base class as
    schema.model_id(<same app_label as the subclass>, base_name), so this
    INHERITS edge silently never existed for ANY tenant model in the whole
    project (every one of them inherits SintelTenantBaseModel from `core`,
    directly or - since ADR-003 - transitively via SedeAwareModel). Pinned
    as an external stub here (compras' own extraction can't know core has
    since been extracted for real); test_cross_app_fk_stub_... in
    test_build_graph.py already proves stubs correctly resolve to the real
    node once both apps are merged - not re-proven here. OrdenCompra
    switched from SintelTenantBaseModel to SedeAwareModel 2026-08-07
    (ADR-003, contexto organizacional Sede/Area) - this assertion tracks
    the real, current base, not a frozen snapshot."""
    graph = _graph()
    orden_compra = graph.nodes[schema.model_id("tenant_compras", "OrdenCompra")]
    base_id = schema.model_id("tenant_core", "SedeAwareModel")
    inherits = [
        e for e in graph.edges
        if e.source_id == orden_compra.id and e.rel_type == schema.REL_INHERITS
    ]
    assert [e.target_id for e in inherits] == [base_id]
    assert graph.nodes[base_id].properties["external"] is True


def test_viewset_inherits_cross_app_base_via_import_resolution():
    """OrdenCompraViewSet(OrganizationalContextMixin, OrdenCompraServiceMixin,
    SintelDSVMixin, BaseTenantViewSet) - OrdenCompraServiceMixin is a
    same-app Service (resolves to a USES edge, already worked before this
    fix); the other three are imported from apps.tenant.core/apps.tenant.api,
    infrastructure apps this pilot does not extract as one of its 17
    business apps (see documentacion/arquitectura_general.md Sec 2.3) - all
    three must still produce an INHERITS edge to an external stub, not
    silently vanish the way they did before this fix (confirmed missing on
    a fresh extraction while building the EKG governance tooling).
    OrganizationalContextMixin was added 2026-08-07 (OCF Fase 9, Migracion
    Aplicacion por Aplicacion) - this assertion tracks the real, current
    inheritance, not a frozen snapshot."""
    graph = _graph()
    viewset = graph.nodes[schema.viewset_id("compras", "OrdenCompraViewSet")]
    inherits_targets = {
        e.target_id for e in graph.edges
        if e.source_id == viewset.id and e.rel_type == schema.REL_INHERITS
    }
    assert inherits_targets == {
        schema.viewset_id("core", "OrganizationalContextMixin"),
        schema.viewset_id("api", "SintelDSVMixin"),
        schema.viewset_id("api", "BaseTenantViewSet"),
    }
    for target_id in inherits_targets:
        assert graph.nodes[target_id].properties["external"] is True

    uses_targets = {
        e.target_id for e in graph.edges
        if e.source_id == viewset.id and e.rel_type == schema.REL_USES
    }
    assert schema.service_id("compras", "api_mixins", "OrdenCompraServiceMixin") in uses_targets


def test_real_viewset_node_explicitly_marks_external_false():
    """A real ViewSet definition must set external=False explicitly (not
    just omit the key), mirroring extract_models()'s real-Model nodes -
    Graph.add_node's "external is monotonic" merge only forces false when
    the EXISTING node in the graph already has external is False; omitting
    the key entirely left a real ViewSet vulnerable to being silently
    downgraded back to a stub if a cross-app INHERITS stub for that same
    node (from another app, processed either before or after) merged in.
    Found via the EKG governance sweep: a `core` app CoreViewSet correctly
    resolved an INHERITS edge to a real tenant ViewSet, but that tenant
    ViewSet still showed external=True after both apps were merged."""
    graph = _graph()
    viewset = graph.nodes[schema.viewset_id("compras", "OrdenCompraViewSet")]
    assert viewset.properties["external"] is False


def test_cross_app_base_resolution_ignores_non_tenant_imports():
    """A base class imported from anywhere other than apps.tenant.* (a
    Django/DRF builtin, a third-party library, stdlib) must not produce a
    node/edge at all - only apps.tenant.* is within this pilot's scope
    (see PILOT_REPORT.md roadmap item 8). Regression guard for
    _resolve_cross_app_base_folder() being too eager."""
    from tools.ekg.extract_python import _resolve_cross_app_base_folder

    import_map = {
        "SintelTenantBaseModel": "apps.tenant.core.models",
        "models": "django.db",
        "ModelViewSet": "rest_framework.viewsets",
    }
    assert _resolve_cross_app_base_folder("SintelTenantBaseModel", import_map) == "core"
    assert _resolve_cross_app_base_folder("models", import_map) is None
    assert _resolve_cross_app_base_folder("ModelViewSet", import_map) is None
    assert _resolve_cross_app_base_folder("NeverImported", import_map) is None
