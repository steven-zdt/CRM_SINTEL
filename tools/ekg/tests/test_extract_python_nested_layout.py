"""
facturas/ has grown a nested api/services layout (api/mixins/*.py,
services/dian/*.py, api/views_mail_ingestion.py) that compras/ventas don't
have. These assertions pin the fix in extract_services/extract_viewsets
that walks those directories recursively instead of only the four
canonical FSD filenames - see tools/ekg/PILOT_REPORT.md's "Rollout
spot-check #2" section for the bug this closes.
"""

from pathlib import Path

from tools.ekg import schema
from tools.ekg.extract_python import extract_app_python

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _graph():
    return extract_app_python("facturas", PROJECT_ROOT)


def test_nested_dian_service_modules_are_extracted():
    graph = _graph()
    node = graph.nodes[schema.service_id("facturas", "dian.cufe", "CufeService")]
    assert node.properties["kind"] == schema.SERVICE_KIND_OTHER


def test_api_mixins_subpackage_extracted_as_mixin_kind():
    graph = _graph()
    node = graph.nodes[schema.viewset_id("facturas", "FacturaXMLMixin")]
    assert node.properties["kind"] == schema.VIEWSET_KIND_MIXIN


def test_factura_viewset_inherits_its_api_level_mixins():
    graph = _graph()
    viewset_id = schema.viewset_id("facturas", "FacturaViewSet")
    inherited = {
        graph.nodes[e.target_id].properties["name"]
        for e in graph.edges
        if e.source_id == viewset_id and e.rel_type == schema.REL_INHERITS
    }
    assert {"FacturaUBLMixin", "FacturaMailMixin", "FacturaXMLMixin"} <= inherited


def test_router_include_mount_is_not_a_spurious_endpoint():
    """apps/tenant/inventario/api/urls.py mounts its router via
    `path('', include(router.urls))`, unlike compras/proveedores/etc which
    do `urlpatterns = router.urls` directly and never hit the path()
    extraction branch at all. Before _is_include_call(), this line produced
    a permanently-unexposed `Endpoint:inventario::api` node for the
    include() mount itself, not a real route. The `path('', ProductoViewSet
    .as_view(...))` list-view endpoint from inventario's app-level urls.py
    (group="ui") is a real, separate, legitimately-empty-route endpoint and
    must still be extracted - this only targets the include() case."""
    graph = extract_app_python("inventario", PROJECT_ROOT)
    assert schema.endpoint_id("inventario", "", "api") not in graph.nodes
    assert schema.endpoint_id("inventario", "", "ui") in graph.nodes


def test_module_qualified_path_view_reference_resolves():
    """dashboard/api/urls.py does `from . import views` (not `from .views
    import DashboardDataAPIView`), so its path() calls reference
    `views.DashboardDataAPIView.as_view()` - module-qualified, not a bare
    class name. `view_text.split(".", 1)[0]` used to grab "views" (the
    module name) instead of the class, so these endpoints could never
    resolve. See _extract_view_class_name() and PILOT_REPORT.md's spot-check
    #16."""
    graph = extract_app_python("dashboard", PROJECT_ROOT)
    endpoint_id = schema.endpoint_id("dashboard", "data/", "api")
    exposes = [e for e in graph.edges if e.target_id == endpoint_id and e.rel_type == schema.REL_EXPOSES]
    assert len(exposes) == 1
    assert graph.nodes[exposes[0].source_id].properties["name"] == "DashboardDataAPIView"


def test_module_qualified_router_register_reference_resolves():
    """Same bug, the router.register() branch: dashboard/api/urls.py does
    `router.register(r'', viewsets.DashboardViewSet, ...)`."""
    graph = extract_app_python("dashboard", PROJECT_ROOT)
    endpoint_id = schema.endpoint_id("dashboard", "/", "api")
    exposes = [e for e in graph.edges if e.target_id == endpoint_id and e.rel_type == schema.REL_EXPOSES]
    assert len(exposes) == 1
    assert graph.nodes[exposes[0].source_id].properties["name"] == "DashboardViewSet"


def test_module_qualified_base_class_resolves_to_sibling_mixin():
    """apps/tenant/inventario/api/viewsets.py declares
    `class ProductoViewSet(BaseViewSet, inv_services.ProductoServiceMixin)`
    - a module-qualified base class reference, not a bare name. Looking it
    up in class_to_node/service_nodes by the raw qualified text never
    matched, so every ViewSet in inventario using this import style looked
    unwired to its ServiceMixin - a dead-code false positive caught while
    running a real audit against the live graph. See _base_class_name()."""
    graph = extract_app_python("inventario", PROJECT_ROOT)
    viewset_id = schema.viewset_id("inventario", "ProductoViewSet")
    mixin_id = schema.service_id("inventario", "api_mixins", "ProductoServiceMixin")
    uses = [e for e in graph.edges if e.source_id == viewset_id and e.target_id == mixin_id and e.rel_type == schema.REL_USES]
    assert len(uses) == 1


def test_viewset_direct_selector_call_resolves():
    """contabilidad/api/viewsets.py calls `CuentaContableSelector
    .get_qs_list(...)` directly from CuentaContableViewSet, bypassing the
    ServiceMixin class-attribute injection pattern entirely. Without
    scanning ViewSet bodies for these direct calls, CuentaContableSelector
    (and any Service only ever reached this way) looked unreferenced - the
    third distinct dead-code false positive caught auditing the graph in
    one session (see also test_mixin_uses_business_service_via_class_
    attribute_injection and test_module_qualified_base_class_resolves_to_
    sibling_mixin)."""
    graph = extract_app_python("contabilidad", PROJECT_ROOT)
    viewset_id = schema.viewset_id("contabilidad", "CuentaContableViewSet")
    selector_id = schema.service_id("contabilidad", "selectors", "CuentaContableSelector")
    uses = [e for e in graph.edges if e.source_id == viewset_id and e.target_id == selector_id and e.rel_type == schema.REL_USES]
    assert len(uses) == 1


def test_other_kind_files_get_calls_scanned_too():
    """proyectos/services/presupuesto_service.py isn't one of the 4
    canonical FSD filenames, so it gets kind=SERVICE_KIND_OTHER. It still
    has the exact same intra-file Business->CRUD delegation pattern as
    business_service.py (`PresupuestoCRUDService.save_item(item)` called
    from PresupuestoBusinessService in the same file), which the CALLS
    scan used to skip entirely because it was restricted to kind=business.
    Fourth and final dead-code false positive of this family caught in one
    audit session (see also the mixin-injection, qualified-base-class, and
    ViewSet-direct-call fixes above)."""
    graph = extract_app_python("proyectos", PROJECT_ROOT)
    business_id = schema.service_id("proyectos", "presupuesto_service", "PresupuestoBusinessService")
    crud_id = schema.service_id("proyectos", "presupuesto_service", "PresupuestoCRUDService")
    calls = [e for e in graph.edges if e.source_id == business_id and e.target_id == crud_id and e.rel_type == schema.REL_CALLS]
    assert len(calls) == 1


def test_mail_ingestion_apiviews_extracted_and_exposed():
    graph = _graph()
    node_id = schema.viewset_id("facturas", "MailIngestionRunCreateAPIView")
    assert graph.nodes[node_id].properties["kind"] == schema.VIEWSET_KIND_VIEW
    exposes = [e for e in graph.edges if e.source_id == node_id and e.rel_type == schema.REL_EXPOSES]
    assert len(exposes) == 1
    assert graph.nodes[exposes[0].target_id].properties["route"] == "ingesta-correo/run/"
