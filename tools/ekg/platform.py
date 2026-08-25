"""
EKG "Plataforma Enterprise" (Fase 10 of the spec): not a new analysis engine
- a thin synthesis layer over what impact.py (Fase 6) and governance.py
(Fase 7) already compute honestly from the graph, so answering one of the
spec's example questions doesn't mean re-deriving it by hand each time.

Mapping from the spec's example questions to what actually answers them:
  "Quien usa este modelo?"        -> impact.py's reverse-dependency hits
  "Que rompe este cambio?"        -> impact.py's full impacted set
  "Que APIs/JS dependen?"         -> impact.py's hits filtered by label
  "Que pruebas existen?"          -> impact.py's report.tests
  "Que documentacion/ADR aplica?" -> impact.py's report.docs / report.rules
  "Que porcentaje cumple la
   arquitectura?"                 -> compliance_summary() below (NEW)
  "Que modulos estan
   desacoplados?"                 -> decoupled_apps() below (NEW)
  "Que reglas de AGENTS.md
   incumple / que necesita
   refactorizacion?"              -> governance.py's violation lists,
                                      unfiltered - see PILOT_REPORT.md's
                                      manual triage table for which of
                                      those are real findings vs.
                                      extractor noise; this module does not
                                      re-triage them.

Deliberately NOT here (same boundary drawn in governance.py's module
docstring, restated because "Plataforma Enterprise" invites scope creep):
no DSV/permission/N+1/Celery/event analysis - none of that is graph data.
A single "% arquitectura cumplida" number is a coarse proxy over exactly
the rules governance.py can check (5 as of OCF Fase 13, 2026-08-08 -
sede_or_area_field_without_sede_aware_model added there), not a certified
compliance score - treated and labeled as such below.

CLI: python -m tools.ekg.platform --dossier "OrdenCompra" [--label Model]
     python -m tools.ekg.platform --summary
"""

from __future__ import annotations

import argparse

from tools.ekg import schema
from tools.ekg.governance import (
    _belongs_to_tenant_app,
    _tenant_app_ids,
    find_js_outside_own_app_static_path,
    find_models_not_inheriting_tenant_base,
    find_sede_or_area_field_without_sede_aware_model,
    find_templates_outside_own_app_path,
    find_viewsets_without_service_layer,
    models_with_organizational_sede_or_area_field,
)
from tools.ekg.impact import find_nodes_by_name, find_nodes_by_path_fragment, impact_of_offline, load_full_offline_graph

# Cross-app edges that indicate two apps are architecturally coupled (a
# reason NOT to call either one "decoupled"). Narrower than
# impact.py's REVERSE_DEP_RELS: BELONGS_TO itself is excluded since every
# node trivially belongs to exactly one app and would make this metric
# vacuous.
_COUPLING_RELS = frozenset(
    {
        schema.REL_IMPORTS,
        schema.REL_INHERITS,
        schema.REL_USES,
        schema.REL_CALLS,
        schema.REL_CONSUMES,
        schema.REL_REFERENCES,
    }
)


def compliance_summary(graph: schema.Graph) -> dict:
    """One pass/fail-with-percentage row per governance.py rule. The
    denominator is the population each rule actually applies to (e.g. only
    tenant-schema, non-placeholder models) - not "all nodes with this
    label" - so a rule that correctly skips public-schema or unresolved
    nodes doesn't get penalized in the percentage for skipping them."""
    tenant_app_ids = _tenant_app_ids(graph)

    tenant_models = [
        n for n in graph.nodes.values()
        if n.label == schema.NODE_MODEL
        and not n.properties.get("external")
        and n.properties.get("defined_in")
        and _belongs_to_tenant_app(graph, n.id, tenant_app_ids)
    ]
    tenant_viewsets = [
        n for n in graph.nodes.values()
        if n.label == schema.NODE_VIEWSET
        and not n.properties.get("external")
        and n.properties.get("kind") == schema.VIEWSET_KIND_VIEWSET
        and _belongs_to_tenant_app(graph, n.id, tenant_app_ids)
    ]
    all_js = [n for n in graph.nodes.values() if n.label == schema.NODE_JS and not n.properties.get("external")]
    all_templates = [
        n for n in graph.nodes.values() if n.label == schema.NODE_TEMPLATE and not n.properties.get("external")
    ]

    def _row(checked: list, violations: list[str]) -> dict:
        total = len(checked)
        ok = total - len(violations)
        return {
            "checked": total,
            "violations": len(violations),
            "compliant_pct": round(100.0 * ok / total, 1) if total else None,
        }

    # Denominator here is deliberately NOT "all tenant models" (unlike the
    # other three rows): not every model needs a sede/area FK, only the
    # ones that declare one - reuses the exact same population the rule
    # itself checks (models_with_organizational_sede_or_area_field), so
    # this percentage can never silently drift from what the rule reports.
    organizational_field_models = [
        graph.nodes[m] for m in models_with_organizational_sede_or_area_field(graph)
    ]

    return {
        "models_not_inheriting_tenant_base": _row(tenant_models, find_models_not_inheriting_tenant_base(graph)),
        "viewsets_without_service_layer": _row(tenant_viewsets, find_viewsets_without_service_layer(graph)),
        "js_outside_own_app_static_path": _row(all_js, find_js_outside_own_app_static_path(graph)),
        "templates_outside_own_app_path": _row(all_templates, find_templates_outside_own_app_path(graph)),
        "sede_or_area_field_without_sede_aware_model": _row(
            organizational_field_models, find_sede_or_area_field_without_sede_aware_model(graph)
        ),
    }


def decoupled_apps(graph: schema.Graph) -> list[str]:
    """Application names with zero cross-app coupling edge (in either
    direction) to or from any other app - i.e. genuinely isolated in the
    graph, not merely "has few dependents". Every real tenant app inherits
    SintelTenantBaseModel/BaseTenantViewSet from `core`, so an empty result
    here is the expected, honest outcome for a healthy rollout - it is not
    evidence the check never fires (see test_platform.py for a case that
    does)."""
    node_app: dict[str, str] = {}
    for edge in graph.edges:
        if edge.rel_type == schema.REL_BELONGS_TO:
            node_app[edge.source_id] = edge.target_id

    coupled_app_ids: set[str] = set()
    for edge in graph.edges:
        if edge.rel_type not in _COUPLING_RELS:
            continue
        src_app = node_app.get(edge.source_id)
        dst_app = node_app.get(edge.target_id)
        if src_app and dst_app and src_app != dst_app:
            coupled_app_ids.add(src_app)
            coupled_app_ids.add(dst_app)

    # Exclude Application nodes that were never actually extracted (e.g.
    # `apps/tenant/api/` - only ever seen as an external-stub target of
    # cross-app INHERITS, since it isn't one of the 22 apps build_graph.py
    # extracts on its own): an external Application's members never get a
    # real BELONGS_TO edge, so it would show up as "decoupled" purely for
    # lacking data this pilot never collected - not because it actually
    # has no dependents. Confirmed by hand: apps/tenant/api/'s
    # BaseTenantViewSet has 45 real INHERITS edges pointing at it project-
    # wide before this exclusion was added.
    all_app_ids = {
        n.id for n in graph.nodes.values()
        if n.label == schema.NODE_APPLICATION and not n.properties.get("external")
    }
    isolated = all_app_ids - coupled_app_ids
    return sorted(graph.nodes[a].properties.get("name", a) for a in isolated)


def print_summary(graph: schema.Graph) -> None:
    print(f"EKG platform summary: {graph.node_count()} nodes, {graph.edge_count()} edges\n")
    print("Cumplimiento de arquitectura (proxy sobre las reglas de governance.py, NO un score certificado):")
    for rule, row in compliance_summary(graph).items():
        pct = f"{row['compliant_pct']}%" if row["compliant_pct"] is not None else "n/a (0 aplicables)"
        print(f"  - {rule}: {pct} ({row['checked'] - row['violations']}/{row['checked']} cumplen)")

    isolated = decoupled_apps(graph)
    print(f"\nModulos sin acoplamiento cross-app detectado ({len(isolated)}):")
    for name in isolated:
        print(f"  - {name}")
    if not isolated:
        print("  (ninguno - toda app tiene al menos un IMPORTS/INHERITS/USES/CALLS/CONSUMES/REFERENCES cross-app)")

    print(
        "\nNo respondido aqui (no es dato del grafo - ver tools/ekg/governance.py):"
        " DSV, permisos por endpoint, .only()/empresa_id, N+1, Celery, eventos/signals."
    )


def print_dossier(graph: schema.Graph, name: str, label: str | None, max_hops: int) -> None:
    candidates = find_nodes_by_name(graph, name, label) or find_nodes_by_path_fragment(graph, name)
    if not candidates:
        print(f"No se encontro ningun nodo con name/path que contenga '{name}'" + (f" (label={label})" if label else ""))
        return
    if len(candidates) > 1:
        print(f"Multiples coincidencias para '{name}' - usando la primera; use --label para desambiguar:")
        for c in candidates:
            print(f"  - {c.label}: {c.id}")
        print()
    target = candidates[0]

    from tools.ekg.impact import _print_report  # local import: CLI-only helper, not part of the public API

    report = impact_of_offline(graph, target, max_hops=max_hops)
    _print_report(report)

    if target.label == schema.NODE_MODEL:
        violations = find_models_not_inheriting_tenant_base(graph)
        flagged = any(target.properties.get("name", "\0") in v for v in violations)
        print(f"\nCumple 'hereda SintelTenantBaseModel': {'NO' if flagged else 'SI'}")
        if target.id in models_with_organizational_sede_or_area_field(graph):
            sede_violations = find_sede_or_area_field_without_sede_aware_model(graph)
            sede_flagged = any(target.properties.get("name", "\0") in v for v in sede_violations)
            print(f"Cumple 'hereda SedeAwareModel' (tiene campo sede/area): {'NO' if sede_flagged else 'SI'}")
    elif target.label == schema.NODE_VIEWSET:
        violations = find_viewsets_without_service_layer(graph)
        flagged = any(target.properties.get("name", "\0") in v for v in violations)
        print(f"\nCumple 'usa Service Layer': {'NO' if flagged else 'SI'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="EKG platform: unified dossier/compliance view (Fase 10).")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dossier", metavar="NAME", help="Full dossier for one node: impact + compliance status")
    group.add_argument("--summary", action="store_true", help="Project-wide compliance % and decoupled-module list")
    parser.add_argument("--label", default=None, help="Disambiguate --dossier by node label, e.g. Model")
    parser.add_argument("--max-hops", type=int, default=4)
    args = parser.parse_args()

    graph = load_full_offline_graph()
    if args.summary:
        print_summary(graph)
    else:
        print_dossier(graph, args.dossier, args.label, args.max_hops)


if __name__ == "__main__":
    main()
