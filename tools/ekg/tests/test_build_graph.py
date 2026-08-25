from pathlib import Path

from tools.ekg import schema
from tools.ekg.build_graph import build_app_graph
from tools.ekg.queries import offline_fk_relationships, offline_js_consuming_endpoint_route
from tools.ekg.validate import find_dangling_edges, find_unexposed_endpoints

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_full_pilot_graph_has_no_dangling_edges():
    graph = build_app_graph("compras", PROJECT_ROOT)
    assert find_dangling_edges(graph) == []


def test_js_literal_endpoint_links_to_real_router_endpoint():
    graph = build_app_graph("compras", PROJECT_ROOT)
    targets = {
        e.target_id
        for e in graph.edges
        if e.rel_type == schema.REL_CONSUMES
        and e.source_id == schema.js_id("apps/tenant/compras/static/compras/js/compras.api.js")
    }
    assert schema.endpoint_id("compras", "plantillas", "api") in targets


def test_sample_question_fk_relationships():
    graph = build_app_graph("compras", PROJECT_ROOT)
    results = offline_fk_relationships(graph, "OrdenCompra")
    assert any("proveedor" in r and "Proveedor" in r for r in results)
    assert any("plantilla" in r and "PlantillaOrdenCompra" in r for r in results)


def test_sample_question_js_consuming_endpoint():
    graph = build_app_graph("compras", PROJECT_ROOT)
    results = offline_js_consuming_endpoint_route(graph, "plantillas")
    assert any("compras.api.js" in r for r in results)


def test_cross_app_fk_stub_resolves_to_real_node_once_both_apps_are_merged():
    """The whole point of extracting multiple apps into one shared Neo4j
    graph is that a stub created from one app's FK string (e.g. compras'
    OrdenCompra.proveedor -> "tenant_proveedores.Proveedor") collapses onto
    the real Model node once proveedores itself is also extracted and
    merged - both must produce the exact same node id (keyed by Django's
    real app_label, not the apps/tenant/<folder> name) or they stay two
    permanently-disconnected nodes. See extract_python.py's
    resolve_model_target() docstring for the bug this pins."""
    compras = build_app_graph("compras", PROJECT_ROOT)
    proveedores = build_app_graph("proveedores", PROJECT_ROOT)

    proveedor_id = schema.model_id("tenant_proveedores", "Proveedor")
    assert compras.nodes[proveedor_id].properties["external"] is True

    merged = schema.Graph()
    merged.merge(compras)
    merged.merge(proveedores)

    resolved = merged.nodes[proveedor_id]
    assert resolved.properties["external"] is False
    assert "defined_in" in resolved.properties


def test_external_flag_is_monotonic_across_merge_order():
    """gastos has its own `proveedor` FK, so build_app_graph("gastos", ...)
    independently produces its own external=True stub for
    Model:tenant_proveedores.Proveedor - a perfectly correct thing for that
    one app's standalone extraction to do. The bug: merging gastos AFTER
    proveedores (whose own extraction resolved that same node for real,
    external=False) was silently downgrading it back to a stub, because
    Graph.add_node's dict-union merge let whichever app merged last win.
    Found while extracting an 8th app in the rollout - see PILOT_REPORT.md
    spot-check #8. Pin both merge orders so this can't silently regress."""
    proveedores = build_app_graph("proveedores", PROJECT_ROOT)
    gastos = build_app_graph("gastos", PROJECT_ROOT)
    target_id = schema.model_id("tenant_proveedores", "Proveedor")

    real_then_stub = schema.Graph()
    real_then_stub.merge(proveedores)
    real_then_stub.merge(gastos)
    assert real_then_stub.nodes[target_id].properties["external"] is False

    stub_then_real = schema.Graph()
    stub_then_real.merge(gastos)
    stub_then_real.merge(proveedores)
    assert stub_then_real.nodes[target_id].properties["external"] is False


def test_core_viewset_inherits_real_tenant_viewset_across_apps_after_merge():
    """apps/tenant/core/api/v1/contabilidad/viewsets.py's
    CuentaContableCoreViewSet(CuentaContableViewSet) is the ADR-002 public/
    tenant dual-registration pattern: a `core`-app facade that inherits the
    real tenant ViewSet wholesale rather than re-implementing Service Layer
    delegation. Before this fix, cross-app ViewSet INHERITS was never
    resolved at all (same root cause as the Model INHERITS bug); after
    fixing that but before also marking real ViewSet nodes external=False
    explicitly, the stub this cross-app resolution creates could merge
    OVER the already-real contabilidad-side node and leave it looking like
    a stub forever - caught building the EKG governance sweep, which
    otherwise flagged CuentaContableViewSet as "no Service Layer usage"
    only because the merged graph couldn't see past the (wrongly-still-
    external) node to its real USES edges in some traversals."""
    core = build_app_graph("core", PROJECT_ROOT)
    contabilidad = build_app_graph("contabilidad", PROJECT_ROOT)

    target_id = schema.viewset_id("contabilidad", "CuentaContableViewSet")
    assert core.nodes[target_id].properties["external"] is True

    merged = schema.Graph()
    merged.merge(core)
    merged.merge(contabilidad)
    assert merged.nodes[target_id].properties["external"] is False

    core_first_id = schema.viewset_id("core", "CuentaContableCoreViewSet")
    inherits = [
        e for e in merged.edges
        if e.source_id == core_first_id and e.rel_type == schema.REL_INHERITS
    ]
    assert [e.target_id for e in inherits] == [target_id]


def test_application_node_survives_merge_regardless_of_order_with_a_cross_app_stub():
    """Same class of bug, same fix, as the ViewSet external=False fix
    above - extract_services() can create an external=True Application
    stub for another app when a receiver name matches a cross-app Service
    (see the "other_app_node_id" stub in extract_python.py). Without an
    explicit external=False on the real Application node, merge order
    could silently downgrade it back to looking external. Found while
    extending EKG coverage to apps/public/* and merging 22 apps together
    for the first time - a corrupted Application node would make every
    GOVERNED_BY/DOCUMENTED_BY/BELONGS_TO query for that app unreliable."""
    compras = build_app_graph("compras", PROJECT_ROOT)
    app_id = schema.application_id("compras")
    assert compras.nodes[app_id].properties["external"] is False

    stub = schema.Graph()
    stub.merge(schema.Graph())
    stub.add_node(schema.Node(app_id, schema.NODE_APPLICATION, {"name": "compras", "external": True}))

    stub_then_real = schema.Graph()
    stub_then_real.merge(stub)
    stub_then_real.merge(compras)
    assert stub_then_real.nodes[app_id].properties["external"] is False

    real_then_stub = schema.Graph()
    real_then_stub.merge(compras)
    real_then_stub.merge(stub)
    assert real_then_stub.nodes[app_id].properties["external"] is False


def test_public_and_tenant_apps_sharing_a_bare_folder_name_do_not_collide():
    """apps/tenant/core and apps/public/core are two entirely different,
    unrelated apps that happen to share the bare folder name "core".
    build_app_graph()'s app_name/folder_name split (see its docstring)
    must keep every id namespace - Application, ViewSet, JS, Endpoint -
    fully separate between them once both are merged into one graph."""
    tenant_core = build_app_graph("core", PROJECT_ROOT)
    public_core = build_app_graph("public_core", PROJECT_ROOT, schema_root="public", folder_name="core")

    assert schema.application_id("core") in tenant_core.nodes
    assert schema.application_id("public_core") in public_core.nodes
    assert schema.application_id("public_core") not in tenant_core.nodes
    assert schema.application_id("core") not in public_core.nodes

    merged = schema.Graph()
    merged.merge(tenant_core)
    merged.merge(public_core)
    assert merged.nodes[schema.application_id("core")].properties["name"] == "core"
    assert merged.nodes[schema.application_id("public_core")].properties["name"] == "public_core"
    assert find_dangling_edges(merged) == []


def test_ui_table_view_endpoint_is_a_known_gap():
    """apps/tenant/compras/views.py (OrdenCompraTableView, django-tables2)
    is not parsed by this pilot - documenting the gap here so it fails
    loudly (forcing an update to this test) instead of silently if a future
    change makes it look covered without extract_python.py actually having
    gained a View/Table extractor."""
    graph = build_app_graph("compras", PROJECT_ROOT)
    assert find_unexposed_endpoints(graph) == [
        f"{schema.endpoint_id('compras', 'tabla/', 'ui')} (route='tabla/')"
    ]
