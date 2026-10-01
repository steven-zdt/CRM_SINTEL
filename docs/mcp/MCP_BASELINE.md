# MCP_BASELINE — LOOP 0 (solo inspección)

> Generado siguiendo `PROMPT_MAESTRO_SINTEL_MCP_CONTROL_PLANE.md` §80
> (LOOP 0 OBLIGATORIO). **No se modificó código de negocio en esta
> pasada** — inspección y consolidación de fuentes reales únicamente.
> Estados usan la taxonomía de la misión (§48): `DOCUMENTED`,
> `IMPLEMENTED`, `VERIFIED`, `PARTIAL`, `DEFERRED`, `NOT_IMPLEMENTED`,
> `BLOCKED`. Fuente de verdad priorizada según §49: código real >
> tests > config > EKG > documentación.

## 0. Resumen ejecutivo

El propio §1 del prompt maestro describe MCP como "andamiaje inerte,
sin una capa MCP operativa completa" — **correcto para el transporte
MCP en sí**, pero la capa que ese transporte expondría (`AIEngine`/
`AIToolRegistry`/`AIContext`) está **mucho más madura** de lo que el
prompt maestro asume: no es un esqueleto, es un motor real con 20
tools registradas, 83 tests en PASS, y un modelo de seguridad
verificado por código (no solo documentado). El hallazgo central de
este LOOP 0, que condiciona todo el diseño de LOOP 1, es:

> **Hay tres superficies distintas que comparten la palabra "MCP" o el
> objetivo "control plane", y el prompt maestro no distingue entre
> ellas.** Antes de diseñar nada en LOOP 1 hace falta decidir a cuál
> de las tres (o combinación) apunta esta misión. Ver §7 "Conflictos y
> decisiones pendientes".

## 1. Estado real de `apps/services/ai/` (el "AI Engine")

Contradice la premisa de `NOT_VERIFIED` global del prompt maestro solo
en el sentido de "todo bloqueado" — el veredicto agregado (`AI_ENGINE
= NOT_VERIFIED`, `docs/ai/AI_RELEASE_GATE.md:208`) es real y sigue
vigente, pero es un veredicto *agregado* de 10 gates, no evidencia de
que no haya nada construido:

| Componente | Ruta real | Estado |
|---|---|---|
| `AIProvider` / `AnthropicProvider` | `apps/services/ai/providers/` | `VERIFIED` — único provider real; `OpenAIProvider`/`LocalProvider` diseñados, no implementados |
| `AIContext` / `build_context()` | `apps/services/ai/context/ai_context.py` | `VERIFIED` (AI-01) — frozen dataclass, SSoT = `request.user.tenant_profile`, nunca el payload |
| `BaseTool` / `ToolKind` / `ToolRisk` / `AUTO_APPROVED_KINDS` | `apps/services/ai/tools/base.py` (leído completo) | `VERIFIED` — `ToolKind∈{READ,SUGGEST,VALIDATE,WRITE}`; `AUTO_APPROVED_KINDS` excluye `WRITE` incondicionalmente (estructural, verificado en código, no solo documentado) |
| `AIToolRegistry` | `apps/services/ai/tools/registry.py` (leído completo) | `VERIFIED` — registro explícito a mano (`register_tool`), nunca introspección automática de ViewSets/ORM; `tool_metadata()` es el único objeto serializable expuesto a un LLM/caller |
| `AIEngine.run_tool()` | `apps/services/ai/engine/ai_engine.py` (leído completo) | `VERIFIED` — único punto de entrada; 4 verificaciones en orden (`AI_ENABLED` → `AI_<KIND>_ENABLED` → `AUTO_APPROVED_KINDS` → `build_context()`), cada una capaz de bloquear antes de que la tool exista la oportunidad de ejecutarse |
| Tools reales registradas | `apps/services/ai/tools/*.py` | **20 tools**: 14 READ/SUGGEST (12 dominios de negocio + `ai_project_map` transversal) + 6 VALIDATE. Ver tabla completa en `docs/ai/AI_TOOL_REGISTRY.md` |
| Orquestador NL→tool | `apps/services/ai/orchestrator/form_assistant.py` | `PARTIAL` (AI-06) — primer caller real de `AIProvider`, endpoint `POST /api/v1/ai/ask/`, guardrail de prompt-injection real (mensaje del usuario tratado como dato); falta verificación E2E con credenciales LLM reales en este entorno |
| ADK (Google ADK, tool-calling autónomo) | `apps/services/ai/adk/` | Fases 0-5 del plan ADK original en `PASS` (LLM real LM Studio/Qwen3.5 conectado, tool-calling verificado en vivo) — ver `docs/adk/ADK_STATUS.md`. Router multi-dominio (Fase 6) y primer WRITE controlado (Fase 7) son trabajo pendiente, no bloqueado |
| Resolver de LLM activo (Hub multimodelo) | `apps/public/console/`, `apps/services/ai/providers/__init__.py::resolve_active_llm()` | Fases 0-1-5-6-8-9-10-11 en `PASS` (UI en `/console/`, secrets con Fernet, fallback/health verificados) — ver `docs/ai/LLM_PROVIDER_HUB_STATUS.md`. **Nada de esto está commiteado todavía** (confirmar antes de asumirlo en producción) |
| WRITE tools | — | `NOT_IMPLEMENTED` por diseño — `AIEngine.run_tool()` rechaza `WRITE` incondicionalmente hasta que exista un flujo de aprobación real (no existe hoy) |
| Suggestion Engine (AI-05) | — | `BLOCKED` por diseño — investigación exhaustiva (`grep -rn "def sugerir_\|def suggest_"`) encontró una sola función de sugerencia pura real en todo el ERP, ya envuelta |
| Session/Memory (AI-08) | `apps/services/ai/policies/`, `memory/`, `tracing/` | `NOT_IMPLEMENTED` — deliberadamente no se crearon paquetes vacíos sin lógica real |

**Corrección al prompt maestro:** las tools `buscar_cliente`/
`buscar_producto`/`ai_project_map`/`buscar_conocimiento` que el prompt
maestro cita como ejemplos (§1) son 4 de **20**, no el catálogo
completo. Dominios ya cubiertos con tool real: `clientes`,
`inventario`, `proveedores`, `ventas`, `compras`, `cotizaciones`,
`gastos`, `proyectos`, `facturas` (read-only permanente),
`empleados`/`bancos` (`SENSITIVE_READ`, campos PII/financieros
clasificados campo por campo en `AI_SECURITY_MODEL.md`),
`contabilidad` (`SUGGEST`, envuelve el Asistente Contable existente).
Formalmente `DEFERRED` (no deuda): `impuestos`, `reporting`.

## 2. Estado real de MCP — tres superficies, no una

### 2.1 `django-rest-framework-mcp` (el "MCP" del prompt maestro)

- Instalado (`requirements.txt:17`, `>=0.1.0a4,<0.2` — paquete alfa,
  confirmado sin cambios en esta sesión), montado en
  `config/urls_tenant.py:166` y `config/urls_public.py:117`
  (`path('mcp/', include('djangorestframework_mcp.urls'))`).
- **Cero ViewSets decorados** (`@mcp_viewset`/`@mcp_tool`) — verificado
  de nuevo (`grep -r "mcp_viewset\|mcp_tool" apps/` → 0 resultados).
- **`BLOCKED` por un defecto real de terceros (AI-07)**: se intentó
  decorar `ClienteViewSet` (`actions=["list","retrieve"]`) y se
  encontró que `execute_tool()` del paquete nunca asigna
  `HttpRequest.method` en la petición interna que fabrica — rompe
  cualquier permiso que dependa de `request.method in SAFE_METHODS`
  (el patrón más común del proyecto, `IsTenantAdminOrReadOnly`).
  Confirmado con test real: un usuario `OPERADOR` (no-admin) haciendo
  una lectura legítima vía MCP recibía `Forbidden`. Se revirtió el
  decorador (código vuelto a su estado exacto anterior). Ver
  `docs/ai/AI_MCP_POLICY.md` "AI-07".
- **Hallazgo adicional, no corregido (2026-09-10, N8N-SINTEL-02)**: la
  capa de *descubrimiento* MCP (`initialize`/`tools/list`) no exige
  ninguna credencial hoy — `MCPView.authentication_classes = []` a
  nivel de paquete (`djangorestframework_mcp/views.py:26`), nunca
  sobreescrito por SINTEL. `BYPASS_VIEWSET_AUTHENTICATION=False`/
  `BYPASS_VIEWSET_PERMISSIONS=False` (`config/settings.py:710-711`,
  verificado en esta pasada) solo aplican dentro de `tools/call`
  (por-ViewSet), no a `tools/list`. Impacto real hoy: ninguno (0 tools
  → lista vacía sin credenciales). Impacto si se decora un ViewSet sin
  corregir esto primero: nombre/descripción/schema de cada tool (no
  los datos) quedarían visibles sin JWT.
- Diseño ya escrito para cuando se retome (`AI_MCP_POLICY.md`, Fases
  31-33): READ-first estricto (solo `GET`/`HEAD`/`OPTIONS`), WRITE
  condicionado a aprobación+idempotencia+auditoría reales, filtrado
  server-side por `ToolRisk`/permisos DRF ya existentes — **nada de
  esto implementado, todo diseño**.

### 2.2 `.antigravity/` / `sintel_agent_unified.py` — MCP de tooling de desarrollo

- Servidor **externo al repo** (`.vscode/mcp.json:3-13` lo referencia
  como `sintel_agent_unified.py` en un path de otra máquina —
  infraestructura del propio editor/Antigravity, no de SINTEL).
- Ya expone tools de auditoría de *este mismo código* (no de datos de
  tenants): `list_available_skills`, `sintel_app_quality_plan(app_name,
  scope)`, `audit_bridge_isolation` (citado también en
  `AGENTS.md:320` como el mecanismo real de validación de la regla de
  bridge cross-schema), `check_infrastructure_health`,
  `antigravity_official_context`/`antigravity_flash_brief`/
  `antigravity_flash_check`.
- **No tiene nada que ver con datos de tenants ni usuarios finales**
  (`docs/ai/AI_CURRENT_STATE.md:63-64`, explícito) — es equivalente en
  espíritu a varias secciones del prompt maestro (`project_inventory`,
  `audit_domain`, `dependency_inventory`) pero para *auditar el propio
  repo desde el editor*, nunca para servir a un agente de negocio en
  producción.

### 2.3 AIEngine/AIToolRegistry invocado directamente (sin MCP)

El único camino **real y funcionando** para que un agente de IA
ejecute algo en SINTEL hoy es Python directo:
`AIEngine.run_tool(tool_name, request, **kwargs)`, invocado desde:
vistas HTTP (`POST /api/v1/ai/ask/`), el orquestador NL
(`form_assistant.py`), y el agente ADK (`apps/services/ai/adk/tools.py`
llama a `AIEngine.run_tool()` directamente en Python, sin HTTP, sin
MCP). **No pasa por `/mcp/` en ningún punto.**

## 3. EKG (`tools/ekg/`) — grafo de código estático, no IA

Herramienta madura (Tree-sitter + Neo4j opcional, snapshots JSON en
`tools/ekg/out/`), rollout completo 17/17 apps tenant
(`tools/ekg/PILOT_REPORT.md`). Comandos reales (`Makefile:228-273`):

```
make ekg-build APP=<app>       # construye snapshot real
make ekg-dry-run APP=<app>     # snapshot sin persistir
make ekg-validate APP=<app>    # integridad del grafo
make ekg-ask Q="..."           # consulta viva (Neo4j)
make ekg-impact NAME="..."     # impacto offline sobre snapshot
make ekg-governance            # reglas F7 (ver §4)
make ekg-explorer              # HTML navegable
make ekg-summary / ekg-dossier # resumen / dossier por entidad
```

Ya consumido por el AI Engine: `ai_project_map`
(`apps/services/ai/tools/ekg_tools.py`) combina el registro vivo de
Django (`django.apps.apps.get_models()`, autoridad total para "quién
es dueño de X") con los snapshots offline (`tools/ekg/queries.py`) para
`rules_for_app`/`docs_for_app`/`fk_relationships`/
`endpoints_for_model`. **No modela cadenas cross-app** ("¿qué pasa al
facturar una venta?") — eso es AI-02.4, `NOT_IMPLEMENTED`.
`DOCUMENTATION_DRIFT` real encontrado y corregido en código (no en
docs): `app_label` de Django diverge del nombre de carpeta del
snapshot para varias apps (ej. `Cliente` → `tenant_clientes`, snapshot
`clientes.json`).

## 4. Governance — dos motores de reglas complementarios, no duplicados

- `tools/ekg/governance.py` (`make ekg-governance`) — reglas F7
  acotadas a lo que los extractores del EKG *ya* pueblan
  (`viewsets_without_service_layer`, `models_not_inheriting_tenant_base`,
  `js_outside_own_app_static_path`) — declara explícitamente qué NO
  puede verificar honestamente (no hay análisis de control-flow).
- `tools/organizational_governance/cli.py` (leído completo, 57 líneas)
  — **exactamente** el target que el prompt maestro pide reutilizar en
  §24 (`governance_audit`). Construye su propio grafo organizacional
  (`build_organizational_graph()`) y corre `run_all_rules()`; exit code
  0/1/2 (PASS/WARN/FAIL). Su propio docstring documenta por qué no es
  un management command Django: tocar `apps/public/` requiere RFC +
  `needs-admin-approval`, y ningún app tenant es el lugar correcto para
  gobernanza de todo el repo.

`production_readiness` (§23 del prompt maestro) también existe ya:
`apps/public/core/management/commands/production_readiness.py` +
`apps/public/core/production_readiness/{checks,registry}.py` — 74
líneas el comando, con su propio registry de checks.

## 5. RAG / pgvector (`apps/tenant/ai_knowledge/`)

POC real, no diseño: `RetrievalService.search_for_context()` invocado
por la tool `buscar_conocimiento` (`RetrievalTool`,
`apps/services/ai/tools/retrieval_tools.py`). Vector Store **por
schema de tenant** (`tenant_ai_knowledge_*`, nunca `public.ai_chunks +
tenant_id`) — aislamiento cross-tenant probado con 2 tenants reales,
`cross_tenant_leaks = 0`. Allowlist curada a mano
(`sources.INDEXABLE_SOURCES`) impide indexar campos `FORBIDDEN`/
`MASKED` — verificado con test (`test_indexar_source_no_allowlisted_es_rechazado`).
Embeddings locales (`FastEmbedProvider`, ONNX, `jina-embeddings-v2-base-es`)
— cero egress de texto. Doble feature flag (`AI_READ_ENABLED` +
`AI_RETRIEVAL_ENABLED`, ambos `false` por defecto).

## 6. Permisos, autenticación, tenant isolation (reutilizables, no reinventar)

- `BaseTenantViewSet`: `[JWTAuthentication, SessionAuthentication]`,
  `lookup_field="uuid"` — nunca sobreescribir en ViewSets hijos
  (CLAUDE.md, confirmado como regla activa).
- Permisos: `apps/tenant/api/permissions.py` — `IsTenantAdminOrReadOnly`
  (la clase más usada del proyecto; permite `GET` a cualquier
  `TenantProfile` autenticado, exige `rol=ADMIN` para
  `POST`/`PUT`/`DELETE`) es precisamente la clase que el defecto AI-07
  rompe cuando se invoca vía MCP. Diff pendiente en este archivo (no
  commiteado, visto en `git status`) es sobre `dt()`/DataTables, **no**
  relacionado con MCP/AI — confirmado leyendo el diff completo.
- `IsTenantMember`: exige `TenantMembership` real en esquema público —
  requisito **distinto** de `TenantProfile` (esquema tenant) que
  `AIContext.build_context()` necesita. `AIAssistantViewSet`
  (`POST /api/v1/ai/ask/`) es el primer caller que ejercita ambos a la
  vez.
- Tenant isolation vía **schema real de PostgreSQL** (django-tenants),
  no `tenant_id` filtrado a mano — verificado en otras misiones (TEN-01)
  y de nuevo en el POC de RAG (§5).
- `AIContext` nunca acepta `empresa_id`/`tenant_id`/`schema_name` desde
  el payload del agente — deriva siempre de
  `request.user.tenant_profile` (mismo SSoT que
  `SintelDSVMixin.get_empresa_id()`).

## 7. Conflictos y decisiones pendientes (§49 — reportar, no ocultar)

1. **Qué significa "MCP" en esta misión.** El prompt maestro diseña un
   "MCP Control Plane" con tools de auditoría de código
   (`project_inventory`, `inspect_model`, `audit_domain`,
   `propose_code_fix`) *y* tools de negocio (`create_record`,
   `execute_domain_action`) bajo el mismo servidor. Hoy esas dos
   familias ya tienen hogares reales y **distintos**:
   - Auditoría de código/arquitectura → territorio de
     `sintel_agent_unified.py` (externo, editor) + `tools/ekg/` +
     `tools/organizational_governance/` (internos, CLI).
   - Tools de negocio con Service Layer/permisos/tenant real →
     territorio de `AIToolRegistry`/`AIEngine` (interno, ya maduro).
   - El transporte MCP real (`django-rest-framework-mcp`, `/mcp/`) no
     expone ninguna de las dos hoy, y está bloqueado por un defecto de
     terceros para la única vía que se probó (ViewSets DRF).

   **Esto no se puede decidir por auditoría — es una decisión de
   producto/arquitectura.** LOOP 1 (§81 del prompt maestro, "Crear
   ADR") debe fijar explícitamente: (a) si "MCP" en esta misión es el
   protocolo MCP literal (heredando el bloqueo AI-07 hasta resolverlo),
   o el `AIToolRegistry`/`AIEngine` ya existente invocado desde
   Python/HTTP (sin ese bloqueo, patrón ya probado por ADK/orquestador),
   o ambos con fronteras explícitas; y (b) si las tools de auditoría de
   *código* nuevas (§4-13 del prompt maestro) se construyen como
   `BaseTool`/`ToolKind.READ` dentro de `AIToolRegistry` (mismo patrón
   que `ai_project_map`, reutilizando `tools/ekg/` y
   `tools/organizational_governance/` como fuente de datos) en vez de
   un cuarto sistema paralelo.

2. **Madurez real vs. premisa del prompt maestro.** El prompt maestro
   trata el AI Engine como algo a "evolucionar" desde cero (§1); en
   realidad ya tiene 20 tools, 83 tests, un modelo de seguridad con
   enforcement verificado por código, y un ADR-equivalente de
   seguridad (`AI_SECURITY_MODEL.md`) más detallado que lo que el
   prompt maestro pide construir en sus §35-46. La mayor parte del
   trabajo de LOOP 1 (§81, "diseñar arquitectura MCP, integrar
   AIToolRegistry/AIEngine/Tenant Context/Authorization") ya está
   hecho para el lado no-MCP — el trabajo real pendiente es extender
   el catálogo de tools (audit_domain, inspect_model, etc.) siguiendo
   el patrón existente, no construir la integración desde cero.

3. **Nada de LLM Provider Hub / DataTables (Fase 5-BIS) está
   commiteado** — confirmado por `git status` al inicio de esta
   sesión: decenas de archivos modificados sin commit. Cualquier
   trabajo de LOOP 1 en adelante debe asumir que ese estado sigue sin
   consolidarse salvo que se verifique de nuevo.

## 8. Qué NO se tocó en este LOOP 0 (cumplimiento §65 "PROHIBIDO")

No se crearon modelos, migraciones, tools, ViewSets decorados con
`@mcp_viewset`, ni se modificó ninguna regla de negocio. Los únicos
archivos nuevos de esta pasada son los de `docs/mcp/`.

## 9. Entregable

Este documento cumple `docs/mcp/MCP_BASELINE.md` (§88). Los demás
entregables obligatorios de §88
(`MCP_ARCHITECTURE.md`/`MCP_SECURITY_MODEL.md`/`MCP_TOOL_CATALOG.md`/
`MCP_DOMAIN_MATRIX.md`/`MCP_AUDIT_WORKFLOW.md`/`MCP_RELEASE_GATE.md`/
`ADR-MCP-001.md`) son trabajo de **LOOP 1** (§81) — condicionados a la
decisión de §7.1, que requiere input explícito del usuario antes de
diseñar.
