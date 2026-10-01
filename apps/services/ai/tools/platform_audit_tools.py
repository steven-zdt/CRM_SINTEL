"""
LOOP 1 del MCP Control Plane (ver docs/mcp/ADR-MCP-001.md): tools de
auditoria/inspeccion de PLATAFORMA (arquitectura del propio proyecto,
no datos de negocio), agregadas al AIToolRegistry ya existente -- mismo
patron que `ai_project_map` (Fase AI-02, `ekg_tools.py`), nunca un
segundo motor/registro/servidor MCP (Regla Absoluta del prompt
maestro, §0/§87: reutilizar, no duplicar).

`project_inventory` censa lo que Django YA sabe con autoridad total
(`django.apps.apps.get_app_configs()`/`get_models()`, registro vivo,
nunca un snapshot) + presencia estructural real en filesystem
(existencia de `services/`, `api/`, `tests/`, `tasks.py`, `signals.py`,
`management/commands/`) -- nunca analisis estatico de codigo (eso es
`tools/ekg/`, ya reutilizado por `ai_project_map` para lo que si
necesita un snapshot). No repite lo que `ai_project_map` ya responde
(owner/rules/docs/fk/endpoints de un modelo o app individual) -- esto
es el censo agregado de TODO el proyecto o de una app completa.
"""

from __future__ import annotations

import os

from apps.services.ai.context import AIContext

from .base import BaseTool, ToolKind, ToolResult, ToolRisk
from .registry import tool_metadata


def _management_commands(app_path: str) -> list[str]:
    commands_dir = os.path.join(app_path, "management", "commands")
    if not os.path.isdir(commands_dir):
        return []
    return sorted(
        f[:-3] for f in os.listdir(commands_dir) if f.endswith(".py") and f != "__init__.py"
    )


def _app_inventory(app_config) -> dict:
    path = app_config.path
    models = list(app_config.get_models())
    return {
        "app_label": app_config.label,
        "verbose_name": str(app_config.verbose_name),
        "models": sorted(m.__name__ for m in models),
        "model_count": len(models),
        # Presencia estructural real (FSD, CLAUDE.md) -- nunca contenido
        # parseado. `has_signals=True` es una senal de posible violacion
        # de la regla "No Signals for business logic" (CLAUDE.md), no una
        # confirmacion -- requeriria inspeccionar el archivo para saber si
        # solo registra logging/auditoria o logica de negocio real.
        "has_services_layer": os.path.isdir(os.path.join(path, "services")),
        "has_api": os.path.isdir(os.path.join(path, "api")),
        "has_tests": os.path.isdir(os.path.join(path, "tests")),
        "has_tasks": os.path.isfile(os.path.join(path, "tasks.py")),
        "has_signals": os.path.isfile(os.path.join(path, "signals.py")),
        "management_commands": _management_commands(path),
    }


class ProjectInventoryTool(BaseTool):
    name = "project_inventory"
    description = (
        "Censa apps/modelos/estructura FSD real del proyecto: registro vivo "
        "de Django (apps, modelos) + presencia de carpetas services/api/tests, "
        "tasks.py, signals.py y management commands por app. Con `app_label` "
        "censa solo esa app; sin argumento, censa todas las apps registradas "
        "mas el catalogo de AI tools ya registradas y el estado real de MCP. "
        "Nunca analisis estatico de codigo (eso vive en tools/ekg/, ver "
        "ai_project_map)."
    )
    domain = "platform"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, app_label: str | None = None) -> ToolResult:
        from django.apps import apps as django_apps

        if app_label:
            try:
                app_config = django_apps.get_app_config(app_label)
            except LookupError:
                return ToolResult(
                    status="NOT_FOUND", message=f"App '{app_label}' no esta registrada."
                )
            return ToolResult(
                status="OK",
                data={"source": "django_app_registry", "app": _app_inventory(app_config)},
            )

        apps_data = [_app_inventory(ac) for ac in django_apps.get_app_configs()]
        return ToolResult(
            status="OK",
            data={
                "source": "django_app_registry",
                "app_count": len(apps_data),
                "apps": apps_data,
                "ai_tools_registered": tool_metadata(),
                "mcp_tools_registered": [],
                "mcp_status": (
                    "BLOCKED -- django-rest-framework-mcp montado en /mcp/ pero "
                    "0 ViewSets decorados con @mcp_viewset/@mcp_tool (defecto real "
                    "de terceros, AI-07). Ver docs/mcp/MCP_BASELINE.md #2.1."
                ),
            },
        )


_VALID_SEVERITIES = frozenset({"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"})


class GovernanceAuditTool(BaseTool):
    name = "governance_audit"
    description = (
        "Corre el motor de reglas organizacionales real "
        "(tools/organizational_governance, F14) contra el grafo actual del "
        "repo -- Service Layer ausente, herencia de SintelTenantBaseModel, "
        "JS fuera de su app, etc. Nunca reimplementa las reglas, invoca "
        "build_organizational_graph()+run_all_rules() tal cual. "
        "severity_filter opcional: CRITICAL|HIGH|MEDIUM|LOW|INFO."
    )
    domain = "platform"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, severity_filter: str | None = None) -> ToolResult:
        from dataclasses import asdict

        from tools.organizational_governance.build import build_organizational_graph
        from tools.organizational_governance.rules import run_all_rules

        if severity_filter is not None:
            severity_filter = severity_filter.upper()
            if severity_filter not in _VALID_SEVERITIES:
                return ToolResult(
                    status="VALIDATION_ERROR",
                    message=f"severity_filter debe ser una de: {sorted(_VALID_SEVERITIES)}",
                )

        graph = build_organizational_graph()
        findings = run_all_rules(graph)
        if severity_filter:
            findings = [f for f in findings if f.severity == severity_filter]

        fail_count = sum(1 for f in findings if f.status == "FAIL")
        warn_count = sum(1 for f in findings if f.status == "WARN")
        overall_status = "FAIL" if fail_count else ("WARN" if warn_count else "PASS")

        return ToolResult(
            status="OK",
            data={
                "source": "tools.organizational_governance",
                # PASS/WARN/FAIL (exit code 0/1/2 de organizational_governance.cli),
                # NO la escala P0-P3 de production_readiness -- cada motor usa la
                # suya propia, no se inventa una tercera escala unificada aqui.
                "overall_status": overall_status,
                "fail_count": fail_count,
                "warn_count": warn_count,
                "finding_count": len(findings),
                "findings": [dict(asdict(f), status=f.status) for f in findings],
            },
        )


class ProductionReadinessTool(BaseTool):
    name = "production_readiness"
    description = (
        "Corre el Production Check Registry real "
        "(apps/public/core/production_readiness, run_all_checks()) contra "
        "config/entorno actual. Nunca reimplementa los checks -- misma "
        "fuente que 'python manage.py production_readiness'."
    )
    domain = "platform"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext) -> ToolResult:
        from apps.public.core.production_readiness.registry import (
            compute_blockers,
            compute_scorecard,
            overall_status,
            run_all_checks,
        )

        results = run_all_checks()
        blockers = compute_blockers(results)
        scorecard = compute_scorecard(results)
        status = overall_status(results)

        return ToolResult(
            status="OK",
            data={
                "source": "apps.public.core.production_readiness",
                "overall_status": status,
                "scorecard": scorecard,
                "blocker_count": len(blockers),
                "results": [r.to_dict() for r in results],
            },
        )


_VALID_CLASSIFICATIONS = frozenset(
    {
        "ALLOWED",
        "CONTROLLED",
        "SOFT_REFERENCE",
        "BRIDGE",
        "DTO",
        "PULL",
        "PUSH_CONTROLLED",
        "FORBIDDEN",
        "CIRCULAR",
        "UNKNOWN",
    }
)


class InspectDependenciesTool(BaseTool):
    name = "inspect_dependencies"
    description = (
        "Descubre dependencias reales entre apps tenant (AST de imports, "
        "F15 de tools/organizational_governance/dependencies.py) -- nunca "
        "grep de texto. Cada dependencia viene clasificada "
        "(ALLOWED/CONTROLLED/SOFT_REFERENCE/BRIDGE/DTO/PULL/"
        "PUSH_CONTROLLED/FORBIDDEN/UNKNOWN) contra las convenciones ya "
        "auditadas del proyecto (Bridge, Pull Model, Bounded Context). "
        "Los ciclos (`cycles`) siempre se calculan sobre el grafo COMPLETO, "
        "nunca sobre el subconjunto filtrado, para no ocultar un ciclo real. "
        "`app_label` filtra edges donde esa app es origen o destino; "
        "`classification` filtra por clasificacion."
    )
    domain = "platform"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(
        self,
        context: AIContext,
        *,
        app_label: str | None = None,
        classification: str | None = None,
    ) -> ToolResult:
        from dataclasses import asdict

        from tools.organizational_governance.dependencies import (
            detect_cycles,
            discover_dependency_edges,
        )

        if classification is not None:
            classification = classification.upper()
            if classification not in _VALID_CLASSIFICATIONS:
                return ToolResult(
                    status="VALIDATION_ERROR",
                    message=f"classification debe ser una de: {sorted(_VALID_CLASSIFICATIONS)}",
                )

        all_edges = discover_dependency_edges()
        cycles = detect_cycles(all_edges)

        edges = all_edges
        if app_label:
            edges = [e for e in edges if e.source_app == app_label or e.target_app == app_label]
        if classification:
            edges = [e for e in edges if e.classification == classification]

        forbidden_count = sum(1 for e in all_edges if e.classification == "FORBIDDEN")

        return ToolResult(
            status="OK",
            data={
                "source": "tools.organizational_governance.dependencies",
                "edge_count": len(edges),
                "edges": [asdict(e) for e in edges],
                # Siempre sobre el grafo completo -- ver docstring de la tool.
                "cycle_count": len(cycles),
                "cycles": cycles,
                "forbidden_count_total": forbidden_count,
            },
        )


_EKG_GOVERNANCE_RULES = (
    "viewsets_without_service_layer",
    "models_not_inheriting_tenant_base",
    "js_outside_own_app_static_path",
    "templates_outside_own_app_path",
    "sede_or_area_field_without_sede_aware_model",
    "import_cycles_between_tenant_apps",
)


class BusinessRuleInventoryTool(BaseTool):
    name = "business_rule_inventory"
    description = (
        "Corre las reglas de gobernanza F7 del EKG "
        "(tools/ekg/governance.py) contra el snapshot mergeado real de "
        "tools/ekg/out/*.json -- ViewSet sin Service Layer, modelo sin "
        "heredar SintelTenantBaseModel, JS/templates fuera de su propia "
        "app, campo sede/area sin modelo sede-aware, ciclos de import "
        "entre apps tenant. Complementa (no duplica) `governance_audit`, "
        "que corre las reglas de tools/organizational_governance sobre un "
        "grafo AST propio, mas liviano y siempre fresco. `rule` opcional "
        "filtra a una sola regla; sin el, corre las 6. SIEMPRE reporta que "
        "es un snapshot point-in-time (correr 'make ekg-build' para "
        "refrescar), nunca oculta que no es el estado vivo."
    )
    domain = "platform"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, rule: str | None = None) -> ToolResult:
        from tools.ekg import governance as ekg_governance
        from tools.ekg.impact import OUT_DIR, PILOT_APPS, PUBLIC_APPS, load_full_offline_graph

        if rule is not None and rule not in _EKG_GOVERNANCE_RULES:
            return ToolResult(
                status="VALIDATION_ERROR",
                message=f"rule debe ser una de: {sorted(_EKG_GOVERNANCE_RULES)}",
            )

        check_funcs = {
            "viewsets_without_service_layer": ekg_governance.find_viewsets_without_service_layer,
            "models_not_inheriting_tenant_base": ekg_governance.find_models_not_inheriting_tenant_base,
            "js_outside_own_app_static_path": ekg_governance.find_js_outside_own_app_static_path,
            "templates_outside_own_app_path": ekg_governance.find_templates_outside_own_app_path,
            "sede_or_area_field_without_sede_aware_model": ekg_governance.find_sede_or_area_field_without_sede_aware_model,
            "import_cycles_between_tenant_apps": ekg_governance.find_import_cycles_between_tenant_apps,
        }

        graph = load_full_offline_graph()
        selected = {rule: check_funcs[rule]} if rule else check_funcs
        results = {name: fn(graph) for name, fn in selected.items()}
        total_violations = sum(len(v) for v in results.values())

        snapshot_mtimes = [
            os.path.getmtime(p)
            for p in (OUT_DIR / f"{app}.json" for app in (*PILOT_APPS, *PUBLIC_APPS))
            if p.exists()
        ]

        return ToolResult(
            status="OK",
            data={
                "source": "tools.ekg.governance",
                # SIEMPRE explicito -- este grafo es un merge de snapshots
                # generados por 'make ekg-build', nunca el codigo vivo.
                "snapshot_oldest": (
                    __import__("datetime").datetime.fromtimestamp(min(snapshot_mtimes)).isoformat()
                    if snapshot_mtimes
                    else None
                ),
                "snapshot_newest": (
                    __import__("datetime").datetime.fromtimestamp(max(snapshot_mtimes)).isoformat()
                    if snapshot_mtimes
                    else None
                ),
                "node_count": graph.node_count(),
                "edge_count": graph.edge_count(),
                "overall_status": "FAIL" if total_violations else "PASS",
                "total_violations": total_violations,
                "checks": {
                    name: {"violation_count": len(v), "violations": v}
                    for name, v in results.items()
                },
            },
        )


class TenantContextTool(BaseTool):
    name = "tenant_context"
    description = (
        "Devuelve el AIContext YA resuelto por AIEngine.run_tool() para esta "
        "llamada -- empresa/schema/rol/alcance/sedes/areas reales del "
        "usuario autenticado. Util para que un agente confirme bajo que "
        "identidad esta operando antes de interpretar el resultado de otra "
        "tool. Nunca acepta un parametro que permita cambiar el contexto -- "
        "solo lo refleja (Regla Absoluta: nunca aceptar tenant_id/"
        "schema_name/empresa_id del agente como forma de cambiar el "
        "contexto de seguridad)."
    )
    domain = "platform"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext) -> ToolResult:
        return ToolResult(
            status="OK",
            data={
                "source": "AIContext (build_context(), ya resuelto por AIEngine antes de esta tool)",
                "user_id": context.user_id,
                "empresa_id": context.empresa_id,
                "schema_name": context.schema_name,
                "rol": context.rol,
                "alcance": context.alcance,
                "sede_ids": list(context.sede_ids),
                "area_ids": list(context.area_ids),
                "screen_app": context.screen_app,
                "screen_entity": context.screen_entity,
                "screen_entity_id": context.screen_entity_id,
                "screen_operation": context.screen_operation,
            },
        )


class DomainInventoryTool(BaseTool):
    name = "domain_inventory"
    description = (
        "Lista las AI tools ya registradas para un dominio de negocio "
        "(ej. 'clientes', 'ventas', 'contabilidad') via "
        "AIToolRegistry.tool_metadata() filtrado -- nunca reconstruye el "
        "catalogo aparte. Para la estructura FSD completa de la app "
        "propietaria de ese dominio (modelos, services/, api/, tests/), "
        "usar `project_inventory(app_label=...)` -- esta tool solo cubre "
        "el eje 'que puede hacer un agente de IA en este dominio hoy', no "
        "el censo completo de la app."
    )
    domain = "platform"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, domain: str) -> ToolResult:
        if not domain or not domain.strip():
            return ToolResult(status="VALIDATION_ERROR", message="domain es obligatorio.")
        domain = domain.strip()

        matches = [m for m in tool_metadata() if m["domain"] == domain]
        if not matches:
            return ToolResult(
                status="NOT_FOUND",
                message=(
                    f"Ningun AI tool registrado para domain='{domain}'. Ver "
                    "docs/ai/AI_TOOL_REGISTRY.md para dominios diseñados pero "
                    "no implementados todavia."
                ),
            )
        return ToolResult(
            status="OK",
            data={
                "source": "AIToolRegistry.tool_metadata()",
                "domain": domain,
                "tool_count": len(matches),
                "tools": matches,
            },
        )


class AuditDomainTool(BaseTool):
    name = "audit_domain"
    description = (
        "Auditoria agregada de una app/dominio: orquesta 3 tools "
        "`platform` ya reales (project_inventory, ai_project_map con "
        "question='rules_for_app', inspect_dependencies) en una sola "
        "llamada -- no reimplementa ninguna. Cubre: modelos+estructura "
        "FSD (inventory), reglas documentadas del EKG si hay snapshot "
        "(rules), dependencias reales con otras apps (dependencies). NO "
        "cubre permisos/integraciones/maquinas de estado/transacciones -- "
        "eso sigue DESIGNED, ver docs/mcp/MCP_TOOL_CATALOG.md."
    )
    domain = "platform"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, app_label: str) -> ToolResult:
        from .ekg_tools import ProjectMapTool, _folder_name_from_module

        if not app_label or not app_label.strip():
            return ToolResult(status="VALIDATION_ERROR", message="app_label es obligatorio.")
        app_label = app_label.strip()

        inventory_result = ProjectInventoryTool().run(context, app_label=app_label)
        if inventory_result.status != "OK":
            return inventory_result

        from django.apps import apps as django_apps

        app_config = django_apps.get_app_config(app_label)
        ekg_folder = _folder_name_from_module(app_config.name)

        rules_result = (
            ProjectMapTool().run(context, question="rules_for_app", name=ekg_folder)
            if ekg_folder
            else ToolResult(
                status="NOT_FOUND", message="No se pudo derivar el nombre de snapshot EKG."
            )
        )
        # inspect_dependencies (tools/organizational_governance) trabaja con
        # nombres de CARPETA (ej. "clientes"), no con el app_label real de
        # Django (ej. "tenant_clientes") -- mismo DOCUMENTATION_DRIFT ya
        # conocido de ekg_tools.py. Pasar app_label tal cual aqui filtraria
        # silenciosamente a 0 resultados; se usa ekg_folder, que es el mismo
        # nombre de carpeta.
        dependencies_result = InspectDependenciesTool().run(context, app_label=ekg_folder)

        return ToolResult(
            status="OK",
            data={
                "source": "audit_domain (project_inventory + ai_project_map + inspect_dependencies)",
                "app_label": app_label,
                "inventory": inventory_result.data["app"],
                "rules_status": rules_result.status,
                "rules": rules_result.data if rules_result.status == "OK" else None,
                "rules_message": "" if rules_result.status == "OK" else rules_result.message,
                "dependencies": dependencies_result.data,
                "not_covered": [
                    "permissions_detail",
                    "integrations",
                    "state_machines",
                    "transactions",
                    "idempotency",
                ],
            },
        )


def _describe_field(field) -> dict | None:
    entry: dict = {"name": getattr(field, "name", None), "type": field.__class__.__name__}
    if entry["name"] is None:
        return None
    for attr in ("null", "blank", "unique", "primary_key", "db_column"):
        if hasattr(field, attr):
            entry[attr] = getattr(field, attr)
    choices = getattr(field, "choices", None)
    if choices:
        entry["choices"] = [list(c) for c in choices]
    if getattr(field, "is_relation", False):
        entry["relation"] = {
            "kind": (
                "many_to_many"
                if getattr(field, "many_to_many", False)
                else "one_to_one"
                if getattr(field, "one_to_one", False)
                else "many_to_one"
                if getattr(field, "many_to_one", False)
                else "one_to_many"
                if getattr(field, "one_to_many", False)
                else "unknown"
            ),
            "related_model": field.related_model.__name__
            if getattr(field, "related_model", None)
            else None,
        }
    return entry


def _describe_model(model) -> dict:
    meta = model._meta
    fields = [f for f in (_describe_field(fld) for fld in meta.get_fields()) if f is not None]
    constraints = [
        {"type": c.__class__.__name__, "name": getattr(c, "name", None)} for c in meta.constraints
    ]
    indexes = [
        {"name": getattr(idx, "name", None), "fields": list(getattr(idx, "fields", ()))}
        for idx in meta.indexes
    ]
    return {
        "model": model.__name__,
        "app_label": meta.app_label,
        "db_table": meta.db_table,
        "field_count": len(fields),
        "fields": fields,
        "constraints": constraints,
        "indexes": indexes,
    }


class InspectModelTool(BaseTool):
    name = "inspect_model"
    description = (
        "Inspecciona un modelo real via Model._meta (registro vivo de "
        "Django) -- fields (tipo/nullable/blank/unique/choices/relacion), "
        "constraints e indexes. Complementa (no duplica) "
        "ai_project_map(question='fk_relationships'), que ya cubre "
        "relaciones FK de forma mas dirigida; esta tool da el censo "
        "completo del modelo. Si varios modelos registrados comparten "
        "nombre (poco comun), devuelve todos."
    )
    domain = "platform"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, model_name: str) -> ToolResult:
        from django.apps import apps as django_apps

        if not model_name or not model_name.strip():
            return ToolResult(status="VALIDATION_ERROR", message="model_name es obligatorio.")
        model_name = model_name.strip()

        matches = [m for m in django_apps.get_models() if m.__name__.lower() == model_name.lower()]
        if not matches:
            return ToolResult(
                status="NOT_FOUND", message=f"Ningun modelo llamado '{model_name}' esta registrado."
            )

        return ToolResult(
            status="OK",
            data={
                "source": "django Model._meta (registro vivo)",
                "match_count": len(matches),
                "models": [_describe_model(m) for m in matches],
            },
        )


def _walk_url_patterns(patterns, prefix: str, entries: dict) -> None:
    for p in patterns:
        sub_patterns = getattr(p, "url_patterns", None)
        if sub_patterns is not None:
            _walk_url_patterns(sub_patterns, prefix + str(p.pattern), entries)
            continue
        name = getattr(p, "name", None)
        if name is None or name in entries:
            # Deduplica variantes de formato (.json/.api, mismo `name` que la
            # ruta canonica) y patrones sin nombre (no capturables sin
            # colisionar entre si).
            continue
        callback = p.callback
        cls = getattr(callback, "cls", None)
        initkwargs = getattr(callback, "initkwargs", None) or {}
        entries[name] = {
            "path": prefix + str(p.pattern),
            "name": name,
            "view_class": cls.__name__ if cls else getattr(callback, "__name__", None),
            "basename": initkwargs.get("basename"),
            "detail": initkwargs.get("detail"),
        }


class ApiInventoryTool(BaseTool):
    name = "api_inventory"
    description = (
        "Recorre el resolver de URLs REAL y vivo de Django ('config."
        "urls_tenant' por defecto -- superficie API-first del tenant, ver "
        "CLAUDE.md) y lista los endpoints DRF registrados: path, name, "
        "view_class, basename, detail (ruta de lista vs. de detalle). "
        "Deduplica variantes de formato (.json) por `name`. NO extrae "
        "permission_classes ni el metodo HTTP exacto por accion (DRF no "
        "los conserva en initkwargs despues de as_view() -- "
        "reconstruirlos requeriria re-derivar la tabla Route/DynamicRoute "
        "del router, trabajo adicional no incluido aqui). `path_prefix` "
        "opcional filtra por un segmento de URL (ej. 'facturas'); sin el, "
        "se limita a los primeros 200 endpoints unicos con "
        "`truncated=true` si aplica (Fase 63: limites de tamaño)."
    )
    domain = "platform"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(
        self,
        context: AIContext,
        *,
        path_prefix: str | None = None,
        urlconf: str = "config.urls_tenant",
    ) -> ToolResult:
        from django.urls import get_resolver

        try:
            # url_patterns es un cached_property que importa el modulo del
            # urlconf de forma perezosa -- el error real (ej. modulo
            # inexistente) solo aparece aqui, no al construir el resolver.
            resolver = get_resolver(urlconf)
            top_level_patterns = resolver.url_patterns
        except Exception as exc:
            return ToolResult(status="VALIDATION_ERROR", message=f"urlconf invalido: {exc}")

        entries: dict = {}
        _walk_url_patterns(top_level_patterns, "", entries)

        items = list(entries.values())
        if path_prefix:
            items = [e for e in items if path_prefix in e["path"]]
        items.sort(key=lambda e: e["path"])

        truncated = False
        if not path_prefix and len(items) > 200:
            items = items[:200]
            truncated = True

        return ToolResult(
            status="OK",
            data={
                "source": f"django.urls.get_resolver('{urlconf}') -- registro vivo",
                "urlconf": urlconf,
                "endpoint_count": len(items),
                "truncated": truncated,
                "endpoints": items,
                "not_covered": [
                    "permission_classes",
                    "http_methods_exactos",
                    "request_response_schema",
                ],
            },
        )


class DjangoCheckTool(BaseTool):
    name = "django_check"
    description = (
        "Corre el System Check Framework real de Django "
        "(django.core.checks.run_checks(), la misma funcion que usa "
        "'manage.py check' internamente) -- nunca invoca manage.py como "
        "subproceso ni reimplementa los checks. include_deployment_checks "
        "opcional (default False, igual que 'manage.py check' sin "
        "--deploy)."
    )
    domain = "platform"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext, *, include_deployment_checks: bool = False) -> ToolResult:
        from django.core.checks import run_checks

        issues = run_checks(include_deployment_checks=include_deployment_checks)
        errors = [i for i in issues if i.is_serious() and not i.is_silenced()]
        warnings = [i for i in issues if not i.is_serious() and not i.is_silenced()]

        return ToolResult(
            status="OK",
            data={
                "source": "django.core.checks.run_checks()",
                "overall_status": "FAIL" if errors else ("WARN" if warnings else "PASS"),
                "error_count": len(errors),
                "warning_count": len(warnings),
                "issues": [
                    {"level": i.level, "id": i.id, "message": str(i), "is_error": i.is_serious()}
                    for i in issues
                    if not i.is_silenced()
                ],
            },
        )


class MigrationCheckTool(BaseTool):
    name = "migration_check"
    description = (
        "Corre 'manage.py makemigrations --check --dry-run' real via "
        "call_command() -- nunca escribe migraciones, solo detecta si "
        "faltan. Ese comando senala 'faltan migraciones' con "
        "sys.exit(1) (nunca una excepcion estandar) -- esta tool lo "
        "captura explicitamente como SystemExit, nunca lo deja escapar "
        "ni lo confunde con exito."
    )
    domain = "platform"
    kind = ToolKind.READ
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(self, context: AIContext) -> ToolResult:
        import io

        from django.core.management import call_command

        out, err = io.StringIO(), io.StringIO()
        has_missing_migrations = False
        try:
            call_command(
                "makemigrations", "--check", "--dry-run", verbosity=1, stdout=out, stderr=err
            )
        except SystemExit as exc:
            # makemigrations --check señala "faltan migraciones" con
            # sys.exit(1) -- nunca una excepcion normal, ver docstring.
            has_missing_migrations = exc.code != 0

        return ToolResult(
            status="OK",
            data={
                "source": "manage.py makemigrations --check --dry-run (call_command real)",
                "overall_status": "FAIL" if has_missing_migrations else "PASS",
                "has_missing_migrations": has_missing_migrations,
                "output": out.getvalue().strip(),
            },
        )
