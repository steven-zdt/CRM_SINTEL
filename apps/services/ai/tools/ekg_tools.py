"""
Fase AI-02 (EKG Contextual): tool semantica `ai_project_map`, reutiliza
`tools/ekg/` -- NO crea un segundo grafo (regla explicita de la mision).

Dos fuentes de verdad reales combinadas, cada una la MAS autoritativa
para su pregunta especifica:

1. **owner** (¿quien es dueño de este modelo?): se resuelve contra el
   registro de apps de Django (`django.apps.apps.get_models()`) en vez
   del grafo EKG -- es la fuente MAS actual posible (proceso vivo, no
   un snapshot), y "que app_label tiene este modelo" es exactamente lo
   que Django ya sabe con autoridad total, sin necesidad de un grafo.
2. **rules / docs / fk_relationships** (lo que el registro de Django
   NO sabe): se cargan desde los snapshots ya generados de
   `tools/ekg/out/<app>.json` (`tools.ekg.schema.graph_from_jsonable`
   + `tools.ekg.queries.offline_*`) -- son point-in-time (generados
   por `make ekg-build`, no en cada request), por eso la tool SIEMPRE
   informa `snapshot_generated_at` explicitamente, nunca oculta que es
   una fotografia, no el estado live.

No se implementa "process resolution" (AI-02.4, "que ocurre al
facturar una venta") en esta pasada -- requeriria resolver cadenas de
dependencia cross-app reales que el grafo actual no modela de forma
directamente consultable sin trabajo adicional genuino; ver
docs/ai/AI_BASELINE_EXECUTION.md para el detalle de este alcance.
"""
from __future__ import annotations

import json
import os

from apps.services.ai.context import AIContext

from .base import BaseTool, ToolKind, ToolResult, ToolRisk

_EKG_OUT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "tools", "ekg", "out")
)

_VALID_QUESTIONS = frozenset({"owner", "rules_for_app", "docs_for_app", "fk_relationships", "endpoints_for_model"})


def _folder_name_from_module(module_path: str) -> str | None:
    """
    'apps.tenant.clientes.models' -> 'clientes'
    'apps.public.tenants.models'  -> 'public_tenants'  (namespacing real
        de build_graph.py: los apps del schema public se extraen con
        prefijo 'public_', ver tools/ekg/build_graph.py:125)
    Nunca asume que folder == app_label -- ver nota en _resolve_owner.
    """
    parts = module_path.split(".")
    if len(parts) < 3 or parts[0] != "apps":
        return None
    schema_root, folder = parts[1], parts[2]
    if schema_root == "public":
        return f"public_{folder}"
    return folder


class ProjectMapTool(BaseTool):
    name = "ai_project_map"
    description = (
        "Responde preguntas sobre la arquitectura del proyecto: que app es "
        "dueña de un modelo (owner, siempre actual), que reglas/documentos "
        "gobiernan una app, y las relaciones FK/endpoints de un modelo "
        "(desde el ultimo snapshot real del EKG). No devuelve el grafo "
        "completo -- solo lo relevante a la pregunta."
    )
    domain = "platform"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, question: str, name: str) -> ToolResult:
        if question not in _VALID_QUESTIONS:
            return ToolResult(
                status="VALIDATION_ERROR",
                message=f"question debe ser una de: {sorted(_VALID_QUESTIONS)}",
            )
        if not name or not name.strip():
            return ToolResult(status="VALIDATION_ERROR", message="name es obligatorio.")
        name = name.strip()

        if question == "owner":
            return self._resolve_owner(name)
        return self._query_snapshot(question, name)

    # -- owner: registro vivo de Django, nunca un snapshot -----------------

    def _resolve_owner(self, model_name: str) -> ToolResult:
        from django.apps import apps as django_apps

        matches = [
            m for m in django_apps.get_models()
            if m.__name__.lower() == model_name.lower()
        ]
        if not matches:
            return ToolResult(status="NOT_FOUND", message=f"Ningun modelo llamado '{model_name}' esta registrado.")
        data = [
            {
                "model": m.__name__,
                "app_label": m._meta.app_label,
                "app_verbose_name": str(m._meta.app_config.verbose_name),
                # DOCUMENTATION_DRIFT real (encontrado al construir esta
                # tool): el "app_label" real de Django NO siempre coincide
                # con el nombre de carpeta que usa el snapshot del EKG (ej.
                # `Cliente` -> app_label real "tenant_clientes", pero el
                # snapshot es tools/ekg/out/clientes.json, nombrado por
                # carpeta -- ver build_graph.py). documentacion/
                # arquitectura_general.md §2.2 documenta el App Label sin
                # el prefijo "tenant_" para varias apps -- desactualizado,
                # no corregido en esta pasada (fuera del alcance minimo de
                # esta tool). Se deriva el nombre real de carpeta desde
                # __module__ en vez de asumir que coincide con app_label.
                "ekg_snapshot_name": _folder_name_from_module(m.__module__),
            }
            for m in matches
        ]
        return ToolResult(status="OK", data={"source": "django_app_registry", "matches": data})

    # -- rules/docs/fk/endpoints: snapshot real del EKG (out/<app>.json) ---

    def _query_snapshot(self, question: str, name: str) -> ToolResult:
        from tools.ekg import queries as ekg_queries
        from tools.ekg import schema as ekg_schema

        if question in ("rules_for_app", "docs_for_app"):
            # rules_for_app/docs_for_app reciben directamente un nombre de
            # snapshot (carpeta) -- ej. "clientes", no el app_label de
            # Django ("tenant_clientes"); ver _folder_name_from_module.
            app_name = name
        else:
            # fk_relationships / endpoints_for_model reciben un nombre de
            # MODELO -- resolver primero su carpeta EKG real (via Django +
            # __module__, no el app_label) para saber que snapshot cargar.
            owner_result = self._resolve_owner(name)
            if owner_result.status != "OK":
                return owner_result
            app_name = owner_result.data["matches"][0]["ekg_snapshot_name"]
            if app_name is None:
                return ToolResult(
                    status="NOT_FOUND",
                    message=f"No se pudo determinar el snapshot EKG para el modelo '{name}'.",
                )

        snapshot_path = os.path.join(_EKG_OUT_DIR, f"{app_name}.json")
        if not os.path.exists(snapshot_path):
            return ToolResult(
                status="NOT_FOUND",
                message=(
                    f"No existe snapshot EKG para la app '{app_name}' en "
                    f"tools/ekg/out/ -- correr 'make ekg-build' primero."
                ),
            )

        generated_at = __import__("datetime").datetime.fromtimestamp(
            os.path.getmtime(snapshot_path)
        ).isoformat()

        with open(snapshot_path, encoding="utf-8") as fh:
            graph = ekg_schema.graph_from_jsonable(json.load(fh))

        if question == "rules_for_app":
            results = ekg_queries.offline_rules_governing_app(graph, app_name)
        elif question == "docs_for_app":
            results = ekg_queries.offline_docs_for_app(graph, app_name)
        elif question == "fk_relationships":
            results = ekg_queries.offline_fk_relationships(graph, name)
        else:  # endpoints_for_model
            results = ekg_queries.offline_endpoints_for_model(graph, name)

        return ToolResult(
            status="OK",
            data={
                "source": "ekg_snapshot",
                "app_name": app_name,
                "snapshot_generated_at": generated_at,
                "results": results,
            },
        )
