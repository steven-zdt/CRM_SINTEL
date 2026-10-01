# MCP_ARCHITECTURE — Fase 3/LOOP 1

> Ver `ADR-MCP-001.md` antes de leer este documento: "MCP" aquí es el
> nombre de la misión, no el protocolo. La arquitectura real es la
> extensión del `AIToolRegistry`/`AIEngine` ya existente, documentada
> en detalle en `docs/ai/AI_ENGINE_ARCHITECTURE.md` — este documento
> **no la duplica**, solo señala qué cambia con las tools `platform`
> nuevas de esta misión.

## Flujo real (sin cambios en la cadena, nuevo `domain`)

```
Caller (vista/backend/orquestador/ADK -- nunca MCP-protocolo)
  -> AIEngine.run_tool(tool_name, request, **kwargs)
       -> AI_ENABLED + AI_<KIND>_ENABLED (settings, nunca request)
       -> AIToolRegistry.get_tool(tool_name)
       -> WRITE bloqueado estructuralmente (AUTO_APPROVED_KINDS)
       -> build_context(request)  -- SSoT real (TenantProfile)
       -> tool.run(context, **kwargs)
            -> domain="platform": registro vivo de Django +
               tools/ekg/ + tools/organizational_governance/ +
               apps/public/core/production_readiness/
               (nunca ORM directo de negocio, nunca SQL)
            -> domain=<negocio>: Selector/Service ya existente
               (sin cambios, ver AI_TOOL_REGISTRY.md)
       -> ToolResult normalizado
```

Las tools `platform` **no** filtran por `empresa_id` (no son datos de
un tenant) — mismo criterio ya establecido por `ai_project_map`. Siguen
pasando por `build_context()` porque `AIEngine.run_tool()` es el único
punto de entrada y no distingue `domain` para el gate de autenticación
— un caller sin `TenantProfile` válido no ejecuta ninguna tool,
plataforma o negocio.

## Dónde vive el código nuevo

```
apps/services/ai/tools/
  platform_audit_tools.py   # nuevo -- tools domain="platform"
  registry.py                # sin cambios -- mismo registro
apps/services/ai/tests/
  test_project_inventory_tool.py   # nuevo
docs/mcp/                          # nuevo -- documentación de esta mision
```

Ninguna carpeta nueva a nivel de `apps/services/ai/` (no
`apps/services/ai/mcp/`, no `mcp/` en la raíz) — descartado
explícitamente en `ADR-MCP-001.md`.

## Fuentes de datos reutilizadas (nunca reimplementadas)

| Tool (catálogo §4 del prompt maestro) | Fuente real reutilizada |
|---|---|
| `project_inventory` | `django.apps.apps.get_app_configs()`/`get_models()` (registro vivo) + presencia filesystem (services/api/tests/tasks.py/signals.py/management commands) — **implementada** |
| `project_map`, `model_schema` (fk/endpoints) | `ai_project_map` (`ekg_tools.py`), ya implementada — no se duplica |
| `inspect_service`, `inspect_api`, `inspect_dependencies` | `tools/ekg/queries.py` (offline) + `tools/ekg/out/<app>.json` — **diseño, no implementado en esta pasada** |
| `audit_domain`, `audit_endpoint` | Combinación de `ai_project_map` + `tools/organizational_governance/rules.py` — **diseño, no implementado** |
| `audit_dependencies`, `dependency_inventory` | `tools/organizational_governance/dependencies.py` — **diseño, no implementado** |
| `run_tests` | `pytest` con targets allowlisted (nunca shell arbitraria) — **diseño, no implementado** |
| `django_check` | `python manage.py check` — **diseño, no implementado** |
| `migration_check` | `makemigrations --check` / `showmigrations` — **diseño, no implementado** |
| `governance_audit` | `tools/organizational_governance/cli.py` (ya existe, reutilizable tal cual) — **diseño de wrapper, no implementado** |
| `production_readiness` | `apps/public/core/management/commands/production_readiness.py` (ya existe) — **diseño de wrapper, no implementado** |
| `ekg_query` | `tools/ekg/queries.py` / `make ekg-ask` (Neo4j vivo) — **diseño, no implementado** |
| `knowledge_search` | `apps.tenant.ai_knowledge.services.RetrievalService` vía la tool `buscar_conocimiento` ya existente — **ya cubierto, no se duplica** |

Ver `MCP_TOOL_CATALOG.md` para el estado exacto (`IMPLEMENTED`/
`DESIGNED`/`DEFERRED`) de cada tool de esta lista.

## Por qué no un "MCP Resource"/"MCP Prompt" (§45-46 del prompt maestro)

Ambos son primitivas del protocolo MCP (`project://architecture`,
prompts reutilizables server-side). Sin un servidor MCP real detrás
(`ADR-MCP-001.md`), no hay transporte que los sirva. El equivalente
funcional ya existe de otra forma: `tool_metadata()` (catálogo
programático) + esta misma documentación (`docs/mcp/`, `docs/ai/`)
como el "resource" legible por humanos/agentes vía filesystem.
