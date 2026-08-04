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
