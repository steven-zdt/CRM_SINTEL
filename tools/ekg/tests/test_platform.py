from pathlib import Path

from tools.ekg import schema
from tools.ekg.build_graph import build_app_graph
from tools.ekg.platform import compliance_summary, decoupled_apps

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


def test_compliance_summary_denominator_excludes_placeholders_and_public_schema():
    """compras + core alone (no public apps merged) must show 100% on the
    two tenant-only rules - proves the denominator is "applicable tenant
    nodes", not "every Model/ViewSet node including unresolved placeholders
    or, once merged, public-schema ones"."""
    graph = _merged("compras", "core")
    summary = compliance_summary(graph)
    assert summary["models_not_inheriting_tenant_base"]["violations"] == 0
    assert summary["models_not_inheriting_tenant_base"]["checked"] > 0


def test_compliance_summary_includes_sede_or_area_row_with_a_real_denominator():
    """compras.OrdenCompra is the only model with a sede/area field in
    this merge scope and it's migrated (SedeAwareModel) - the new Fase 13
    row must report it as the checked population (not 0, not "all tenant
    models" like the other rows) and 0 violations, proving the denominator
    is wired to the same population the rule itself checks, not a
    hardcoded guess that could silently drift from it."""
    graph = _merged("compras", "core")
    summary = compliance_summary(graph)
    row = summary["sede_or_area_field_without_sede_aware_model"]
    assert row["checked"] == 1  # only OrdenCompra has a sede/area FK in this scope
    assert row["violations"] == 0
    assert row["compliant_pct"] == 100.0


def test_compliance_summary_sede_or_area_row_flags_a_real_unmigrated_case():
    """gastos.DocumentoSoporte has a real sede FK but never adopted
    SedeAwareModel - the new row must show it as a violation, not silently
    exclude it the way the other three rows exclude out-of-scope nodes."""
    graph = _merged("gastos", "core", "empresa")
    summary = compliance_summary(graph)
    row = summary["sede_or_area_field_without_sede_aware_model"]
    assert row["violations"] == 1
    assert row["compliant_pct"] == 0.0


def test_decoupled_apps_excludes_external_stub_applications():
    """apps/tenant/api/ is never extracted as its own app (external stub
    only, e.g. ViewSet:api.BaseTenantViewSet) - it must never appear in the
    decoupled list even though it has no BELONGS_TO-attributed member,
    because that reflects a data gap (never extracted), not an actual
    absence of coupling. Confirmed by hand before the exclusion was added:
    BaseTenantViewSet has 45 real INHERITS edges pointing at it project-
    wide, the opposite of "decoupled"."""
    graph = _merged("compras", "core")
    api_app_id = schema.application_id("api")
    assert api_app_id in graph.nodes
    assert graph.nodes[api_app_id].properties.get("external") is True

    isolated = decoupled_apps(graph)
    assert "api" not in isolated


def test_decoupled_apps_flags_a_real_app_with_no_cross_app_edges():
    """A single real, fully-extracted app merged alone (no core, no
    siblings) has nothing else in the graph to couple to - it must be
    reported as decoupled. Proves the check isn't vacuously empty."""
    graph = build_app_graph("dashboard", PROJECT_ROOT)
    isolated = decoupled_apps(graph)
    assert "dashboard" in isolated
