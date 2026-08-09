"""
Orquestador (F13.11, F13.12, F13.13): corre los extractores de extract.py
sobre las 17 apps tenant reales + docs/ADR-*.md + git log, y arma el Graph.
"""
from __future__ import annotations

from tools.organizational_governance import extract
from tools.organizational_governance.graph import Edge, Graph, Node
from tools.organizational_governance.schema import (
    NODE_ADR,
    NODE_APP,
    NODE_GIT_COMMIT,
    NODE_MODEL,
    NODE_PERMISSION,
    NODE_VIEWSET,
    REL_GOVERNS,
    REL_MODIFIES,
    REL_OWNS,
    REL_USES_CONTEXT,
    REL_USES_PERMISSION,
    REL_USES_SCOPE,
    SCOPE_AREA,
    SCOPE_EMPRESA,
    SCOPE_NONE,
    SCOPE_SEDE,
    SCOPE_SEDE_LEGACY_NULLSAFE,
)

# [ADR-005] Apps donde `sede` es SedeAwareModel real (NOT NULL, endurecido) -
# unico caso hoy es compras. Las demas apps con campo `sede` son legacy
# NULL-safe (ver OSF F7) - el grafo debe distinguir ambos, no tratarlos
# igual (ver schema.SCOPE_SEDE vs SCOPE_SEDE_LEGACY_NULLSAFE).
SEDE_AWARE_MODEL_APPS = frozenset({"compras"})


def build_organizational_graph() -> Graph:
    graph = Graph()

    app_labels = extract.discover_tenant_apps()
    for app_label in app_labels:
        graph.add_node(Node(NODE_APP, app_label, {}))

    # -- Modelos ------------------------------------------------------------
    for app_label in app_labels:
        for model in extract.extract_models_for_app(app_label):
            if model.inherits_sede_aware_model:
                scope = SCOPE_SEDE if app_label in SEDE_AWARE_MODEL_APPS else SCOPE_SEDE_LEGACY_NULLSAFE
            elif model.has_sede:
                scope = SCOPE_SEDE_LEGACY_NULLSAFE
            elif model.has_area:
                scope = SCOPE_AREA
            elif model.has_empresa:
                scope = SCOPE_EMPRESA
            else:
                scope = SCOPE_NONE

            graph.add_node(
                Node(
                    NODE_MODEL,
                    model.qualified_id,
                    {
                        "class_name": model.class_name,
                        "bases": list(model.bases),
                        "scope": scope,
                        "has_sede": model.has_sede,
                        "has_area": model.has_area,
                        "has_empresa": model.has_empresa,
                        "inherits_sede_aware_model": model.inherits_sede_aware_model,
                    },
                )
            )
            graph.add_edge(Edge(REL_OWNS, (NODE_APP, app_label), (NODE_MODEL, model.qualified_id)))

    # -- ViewSets + permisos + OCF/OSF ---------------------------------------
    for app_label in app_labels:
        for vs in extract.extract_viewsets_for_app(app_label):
            graph.add_node(
                Node(
                    NODE_VIEWSET,
                    vs.qualified_id,
                    {
                        "class_name": vs.class_name,
                        "file_path": vs.file_path,
                        "line": vs.line,
                        "uses_organizational_context_mixin": vs.uses_organizational_context_mixin,
                        "uses_organizational_scope": vs.uses_organizational_scope,
                    },
                )
            )
            graph.add_edge(Edge(REL_OWNS, (NODE_APP, app_label), (NODE_VIEWSET, vs.qualified_id)))

            for perm_name in vs.permission_names:
                graph.add_node(Node(NODE_PERMISSION, perm_name, {}))
                graph.add_edge(Edge(REL_USES_PERMISSION, (NODE_VIEWSET, vs.qualified_id), (NODE_PERMISSION, perm_name)))

    # -- OrganizationalContext/Scope a nivel de app (no solo ViewSet, ver
    # extract.app_uses_organizational_scope() para el porque) -----------------
    for app_label in app_labels:
        if extract.app_uses_organizational_context(app_label):
            graph.add_edge(Edge(REL_USES_CONTEXT, (NODE_APP, app_label), (NODE_APP, app_label)))
        if extract.app_uses_organizational_scope(app_label):
            graph.add_edge(Edge(REL_USES_SCOPE, (NODE_APP, app_label), (NODE_APP, app_label)))

    # -- ADRs -----------------------------------------------------------------
    for adr in extract.extract_adrs():
        graph.add_node(Node(NODE_ADR, adr.adr_id, {"title": adr.title, "estado": adr.estado, "file_path": adr.file_path}))
        # Gobierna las apps que su propio titulo/estado menciona explicitamente
        # (heuristica simple y honesta: no se infiere gobernanza no declarada).
        for app_label in app_labels:
            if app_label in adr.title.lower() or app_label in adr.file_path.lower():
                graph.add_edge(Edge(REL_GOVERNS, (NODE_ADR, adr.adr_id), (NODE_APP, app_label)))

    # -- Git (recientes) -------------------------------------------------------
    for commit in extract.extract_recent_git_commits(limit=10):
        graph.add_node(Node(NODE_GIT_COMMIT, commit.sha[:12], {"subject": commit.subject, "files_count": len(commit.files)}))
        touched_apps = {
            f.split("apps/tenant/")[1].split("/")[0]
            for f in commit.files
            if f.startswith("apps/tenant/") and "/" in f.split("apps/tenant/")[1]
        }
        for app_label in touched_apps & set(app_labels):
            graph.add_edge(Edge(REL_MODIFIES, (NODE_GIT_COMMIT, commit.sha[:12]), (NODE_APP, app_label)))

    return graph
