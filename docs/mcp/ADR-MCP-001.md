# ADR-MCP-001 — El "MCP Control Plane" es el AIToolRegistry/AIEngine existente, no un servidor MCP nuevo

**Estado:** Aceptado (2026-09-25, decisión explícita del usuario tras
revisar `MCP_BASELINE.md`)
**Contexto de la misión:** `PROMPT_MAESTRO_SINTEL_MCP_CONTROL_PLANE.md`, LOOP 1 (§81)

## Contexto

`MCP_BASELINE.md` (LOOP 0) encontró tres superficies distintas que
comparten la palabra "MCP" o el objetivo "control plane":

1. **`django-rest-framework-mcp`** (`/mcp/`, protocolo MCP real) —
   instalado y montado, pero **bloqueado**: 0 ViewSets decorados,
   defecto real de terceros (`execute_tool()` nunca asigna
   `request.method`, rompe `IsTenantAdminOrReadOnly`) más un gap de
   autenticación sin corregir en la capa de descubrimiento
   (`tools/list`/`initialize`).
2. **`sintel_agent_unified.py`** (Antigravity, externo al repo) — MCP
   de *tooling de desarrollo* (auditoría del propio código desde el
   editor), sin relación con datos de tenants ni con esta misión.
3. **`AIToolRegistry`/`AIEngine`** (`apps/services/ai/`) — motor real
   y maduro: 20 tools de negocio, 83 tests, seguridad verificada por
   código. Es el único camino que hoy ejecuta algo de verdad, y no
   pasa por MCP.

El prompt maestro pide un "MCP server" que combine tools de auditoría
de código (`project_inventory`, `inspect_model`, `audit_domain`, ...)
con tools de negocio (`create_record`, `execute_domain_action`, ...)
bajo autenticación/autorización/tenant-context/audit unificados.

## Decisión

**El "MCP Control Plane" de esta misión es el `AIToolRegistry` +
`AIEngine` ya existente, extendido con nuevas tools de dominio
`platform`** (auditoría de código/arquitectura), invocadas mediante
`AIEngine.run_tool()` desde Python/HTTP interno — **no** el protocolo
MCP literal expuesto en `/mcp/`.

Consecuencias explícitas de esta decisión:

- No se decorará ningún ViewSet con `@mcp_viewset`/`@mcp_tool` como
  parte de esta misión. El defecto AI-07 y el gap de autenticación de
  `tools/list` **no se heredan** — quedan exactamente donde estaban,
  documentados en `AI_MCP_POLICY.md`, pendientes de una decisión aparte
  si en el futuro se quiere exponer MCP-protocolo real a clientes
  externos (n8n, Antigravity, etc.).
- No se crea un "MCP Tool Registry / Adapter" nuevo (§81 del prompt
  maestro) — `AIToolRegistry` (`apps/services/ai/tools/registry.py`)
  cumple exactamente ese rol hoy: registro explícito a mano,
  `tool_metadata()` serializable, sin introspección automática de
  ViewSets/ORM.
- Las nuevas tools de auditoría (`project_inventory`, `inspect_model`,
  `inspect_service`, `inspect_api`, `inspect_dependencies`,
  `audit_domain`, `audit_endpoint`, `audit_integrations`, `ekg_query`,
  `run_tests`, `django_check`, `migration_check`, `governance_audit`,
  `production_readiness`) se implementan como subclases de `BaseTool`
  (`ToolKind.READ` o `ToolKind.VALIDATE`, `domain="platform"`), mismo
  patrón que `ai_project_map` (`ProjectMapTool`) — **reutilizando**
  `tools/ekg/`, `tools/organizational_governance/`,
  `apps/public/core/production_readiness/` y el registro vivo de
  Django, nunca reimplementando su lógica.
- Ninguna tool `WRITE` se registra en esta fase (§53/§69 del prompt
  maestro: WRITE está bloqueado estructuralmente en `AIEngine` hoy —
  `AUTO_APPROVED_KINDS` excluye `WRITE` incondicionalmente; esto
  aplica igual a tools de negocio y de plataforma).
- `list_mcp_tools` (§44 del prompt maestro) se satisface con
  `tool_metadata()`, ya existente — no se crea una segunda lista.
- Los "MCP Resources"/"MCP Prompts" (§45-46, dependientes del
  protocolo MCP) quedan explícitamente **fuera de alcance** mientras
  se use este camino — no aplican a una fachada Python/HTTP interna.
  Si en el futuro se decide exponer protocolo MCP real, esos dos
  puntos se retoman en un ADR aparte junto con AI-07.

## Alternativas consideradas

- **Protocolo MCP real (`/mcp/`)** — descartada para esta fase: exige
  primero resolver o rodear AI-07 (actualizar el paquete, o decorar
  solo ViewSets cuyo `permission_classes` no dependa de
  `request.method`), trabajo real no autorizado en esta sesión y sin
  relación directa con el valor que la misión busca (auditoría/CRUD
  controlado para un agente autorizado interno).
- **Servidor MCP nuevo dentro del repo** (`mcp/`, `apps/services/mcp/`)
  — descartada: duplicaría exactamente el rol de `AIToolRegistry`,
  violando §0/§87 del propio prompt maestro ("no crear un segundo Tool
  Registry").
- **Ambas superficies con frontera explícita** — no descartada
  permanentemente, solo diferida: nada en esta decisión impide que,
  una vez resuelto AI-07, se decoren ViewSets puntuales para exponer
  un subconjunto de las mismas tools también vía `/mcp/` — ese sería
  un ADR de seguimiento (`ADR-MCP-002`), no una reapertura de este.

## Consecuencias

- Todo el trabajo de LOOP 1 en adelante (nuevas tools de auditoría) se
  mide contra el release gate ya existente de `AI_RELEASE_GATE.md`
  (flags `AI_ENABLED`/`AI_READ_ENABLED`/etc., `AUTO_APPROVED_KINDS`),
  no contra un gate MCP-protocolo aparte.
- El vocabulario "MCP" en el resto de la documentación de esta misión
  (`MCP_ARCHITECTURE.md`, `MCP_TOOL_CATALOG.md`, etc.) se usa como
  nombre de la *misión/iniciativa* ("control plane operativo para un
  agente autorizado"), no como referencia al protocolo Model Context
  Protocol expuesto por terceros.
- Si el usuario pide en el futuro clientes MCP externos reales, este
  ADR debe revisarse explícitamente (no asumir que sigue vigente sin
  releer `AI_MCP_POLICY.md` para el estado de AI-07 en ese momento).

## Addendum (2026-09-25) — `SINTEL_MCP_SKILLS/`

El usuario entregó 12 skills adicionales (`SINTEL_MCP_SKILLS/` en la
raíz del repo) que describen el mismo control plane con más detalle
(CRUD write, domain actions, code repair). Se adoptan como regla de
comportamiento — **sin reabrir esta decisión**: siguen traducidas a
`AIToolRegistry`/`AIEngine`, nunca al protocolo MCP literal. Ver
`MCP_SKILLS_ALIGNMENT.md` para la reconciliación completa, tool por
tool, incluido el vocabulario ("MCP Server" = `AIEngine.run_tool()`).
