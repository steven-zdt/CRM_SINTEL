# MCP_SKILLS_ALIGNMENT — reconciliación de `SINTEL_MCP_SKILLS/` con la implementación real

> Este documento fija la **regla vigente** para el MCP Control Plane: las
> 12 skills en `SINTEL_MCP_SKILLS/` (raíz del repo) quedan **adoptadas**
> como el contrato de comportamiento que toda tool nueva del catálogo
> `platform`/negocio debe cumplir — pero **reinterpretadas bajo la
> arquitectura ya decidida en `ADR-MCP-001.md`**: no existe un "MCP
> Server" de protocolo real detrás de esto, es `AIToolRegistry`/
> `AIEngine` (`apps/services/ai/`). Donde una skill asume el protocolo
> MCP literal, este documento traduce esa exigencia al mecanismo real
> equivalente — nunca se ignora la regla, se reubica.
>
> Fuente de las skills: `SINTEL_MCP_SKILLS/00..11` + `README.md`,
> generadas contra `arquitectura_general.md` v3.64.0 (2026-09-08) — el
> nombre de archivo con sufijo de timestamp que citan
> (`arquitectura_general(20260925-152022).md`) **no existe en el repo**;
> es un artefacto de cómo la herramienta que generó las skills nombró su
> snapshot de entrada, no una fuente perdida — mismo patrón ya
> documentado antes en esta sesión con otros planes maestros externos
> (`project-adk-integration`, memoria del usuario). El contenido
> citado (versión 3.64.0, DOC-M51) sí coincide con el `arquitectura_
> general.md` real del repo — verificado, no un `DOCUMENTATION_DRIFT`.

## 1. Traducción de vocabulario (regla fija, no reabre el ADR)

| Término en las skills | Mecanismo real en este repo |
|---|---|
| "MCP Client → MCP Server" | Caller (vista HTTP/orquestador/ADK) → `AIEngine.run_tool()` — nunca protocolo MCP (`/mcp/` sigue bloqueado por AI-07, ver `MCP_BASELINE.md`) |
| "AuthN/AuthZ" | `[JWTAuthentication/SessionAuthentication]` + `IsTenantMember`/`IsTenantAdminOrReadOnly` (donde hay HTTP) + `build_context()` (siempre) |
| "Tenant Context / Organizational Scope" | `AIContext` (`empresa_id`, `schema_name`, `alcance`, `sede_ids`, `area_ids`) — ver `AI_CONTEXT_MODEL.md` |
| "Tool Policy" | `AIEngine.run_tool()`: flags `AI_ENABLED`/`AI_<KIND>_ENABLED` + `AUTO_APPROVED_KINDS` |
| "AIToolRegistry/AIEngine" | Igual — ya existe, no se crea nada nuevo aquí |
| "Service Layer/BusinessService/CRUDService/Selector" | Igual, sin cambios — cada tool de negocio ya envuelve el Selector/Service real de su dominio (`AI_TOOL_REGISTRY.md`) |
| "MCP_ENABLED, MCP_READ_ENABLED, ..." (skill 11 §F8) | Ya existen como `AI_ENABLED`/`AI_READ_ENABLED`/`AI_SUGGEST_ENABLED`/`AI_VALIDATE_ENABLED`/`AI_WRITE_ENABLED` — **no se crea un segundo set de flags** con prefijo `MCP_`, violaría la regla de no duplicar configuración (§76 del prompt maestro original, ya aplicada) |

## 2. Reconciliación del Tool Catalog (skill 10) contra `MCP_TOOL_CATALOG.md`

### 2.1 Ya IMPLEMENTED (sin cambios, la skill confirma el diseño ya construido)

`project_inventory`, `inspect_model`, `inspect_dependencies` (=`audit_dependencies`), `django_check`, `migration_check`, `production_readiness`, `governance_audit`, `ekg_query`→ver nota (`DEFERRED`, cubierto por `ai_project_map`), `knowledge_search`, `audit_domain`.

`inspect_api` de la skill = nuestro `api_inventory` (mismo dato, nombre alternativo — sin duplicar).

### 2.2 Gap real encontrado: `crud_capabilities` ≠ `domain_inventory`

La skill 10 pide `crud_capabilities` (por modelo: Create/Read/Update/
Delete/Service/API/Permissions/Tests/Status — igual al `Capability
contract` YAML de la skill 01) — **esto NO es lo mismo que nuestro
`domain_inventory` ya implementado** (que solo filtra qué AI tools
existen para un dominio). `crud_capabilities` es un censo nuevo,
`DESIGNED`, no implementado: requeriría cruzar `inspect_model` (ya
real) con la presencia de Serializer de escritura, `ServiceMixin`,
`BusinessService`, permisos y tests por modelo — más profundo que lo
que `project_inventory`/`inspect_model` ya dan. Se agrega a
`MCP_TOOL_CATALOG.md` como fila nueva, `DESIGNED`.

### 2.3 Nuevo en las skills, no en nuestro catálogo — todo `DESIGNED`/`BLOCKED`, nada implementado

| Tool (skill 10) | Kind real que le correspondería | Estado |
|---|---|---|
| `read_record`, `list_records`, `search_records`, `get_related_records` | READ | `DESIGNED` — genérico por modelo; cada dominio de negocio ya tiene su propia tool específica (`buscar_cliente`, etc., `AI_TOOL_REGISTRY.md`) — una versión genérica necesitaría resolver Selector por modelo dinámicamente, riesgo de violar Regla Absoluta 4 (tools semánticas, no genéricas) si no se diseña con cuidado |
| `validate_create`, `validate_update`, `validate_delete`, `validate_domain_action`, `dry_run` | VALIDATE | `DESIGNED` — `validate_create`/`validate_update` ya existen por dominio como `validar_*` (`AI_TOOL_REGISTRY.md`, AI-04); `validate_delete`/`validate_domain_action`/`dry_run` genérico no existen |
| `create_record`, `update_record`, `delete_record`, `execute_domain_action`, `bulk_create`, `bulk_update` | **WRITE** | **BLOCKED por diseño** — `AUTO_APPROVED_KINDS` excluye `WRITE` incondicionalmente hoy (`ai_engine.py`). Ninguna se registra sin un flujo de aprobación real (Regla Absoluta 6/7, skill 00 "Reglas absolutas"). Esto es exactamente F4/F5 de `11_mcp_implementation_prompt.md` — **no autorizado a implementar en esta pasada** |
| `audit_endpoint`, `audit_service` | READ | Ya cubiertos parcialmente por `audit_domain` (agrega inventory+rules+dependencies); auditoría dedicada por endpoint/servicio individual sigue `DESIGNED` |
| `audit_tenant_isolation`, `audit_frontend_api_contract`, `audit_integrations` | READ | `DESIGNED` — nuevos, no investigados todavía. `audit_integrations` es el mismo gap ya anotado como `integration_inventory` en `MCP_TOOL_CATALOG.md` (sin fuente de verdad única en código) |
| `propose_code_fix`, `apply_code_fix` | **CODE_MODIFICATION (CRITICAL)** | `NOT_IMPLEMENTED` — LOOP 5 del prompt maestro original, requiere aprobación humana + rollback; **no autorizado** |

## 3. Módulo Matrix (skill 08) — estado real vs. aspiracional

La tabla de `08_mcp_module_matrix.md` describe un estado objetivo
("CRUD + Kardex/traslados", "CRUD + nómina gateada", etc.) que **no
existe hoy para ningún dominio via MCP/AIToolRegistry** — es la Fase 4
completa (WRITE) que la skill 11 secuencia para más adelante. Estado
real hoy, dominio por dominio, usando la taxonomía de la skill 08:

| Dominio | Estado real hoy |
|---|---|
| `clientes`, `inventario`, `proveedores`, `ventas`, `compras`, `cotizaciones`, `gastos`, `proyectos`, `facturas`, `empleados`, `bancos`, `contabilidad` | `READ_READY` (READ/SUGGEST reales, AI-03 `VERIFIED`) — ver `AI_TOOL_REGISTRY.md` |
| `clientes`, `proveedores`, `inventario`, `compras`, `cotizaciones`, `gastos` | también `VALIDATE_READY` (AI-04) |
| Todos los anteriores | `WRITE_READY` = **NO** (ninguno) — `BLOCKED` por `AUTO_APPROVED_KINDS`, no por dominio individual |
| `empresa`, `perfil` | `NOT_DISCOVERED` para MCP/AIToolRegistry — sin tool alguna hoy (existen APIs REST normales, fuera del alcance de este catálogo) |
| `dashboard` | `NOT_DISCOVERED` |
| `ai_knowledge` | `READ_READY` vía `buscar_conocimiento`/`RetrievalTool` (AI-VECTOR-07), nunca edición directa — coincide con lo que pide la skill 08 ("no edición directa por defecto") |
| `impuestos`, `reporting` | `DEFERRED` formalmente (AI-03, decisión explícita, no deuda) |
| `core`, `landing`, `db_extensions` | `NOT_APPLICABLE` — coincide con la regla explícita de la skill 01/08 ("no deben convertirse automáticamente en CRUD de negocio") |

No se crea una tabla separada duplicando `AI_TOOL_REGISTRY.md` — esta
sección es la traducción de la skill 08 al estado real ya documentado
ahí, para que quien lea las skills primero encuentre el puente.

## 4. Contrato de resultado (skill 00 §"Contrato de resultado") vs. `ToolResult` real

La skill pide un contrato más rico: `status`, `operation_id`, `domain`,
`model`, `action`, `dry_run`, `tenant_verified`, `authorization_
verified`, `validation`, `result`, `warnings`, `audit`, `evidence`.

`ToolResult` real (`apps/services/ai/tools/base.py`) hoy es más simple:
`status`, `data`, `message` — suficiente para READ/VALIDATE puro (lo
único que existe). **Decisión explícita, no ejecutada todavía**: NO se
ensancha `ToolResult` en esta pasada — sería anticipar un contrato para
WRITE/domain-actions que no están autorizados. Cuando se autorice F4
(WRITE por dominio), esta ampliación de contrato es el primer paso de
diseño real, y debe decidirse entonces si se extiende `ToolResult` o se
añade un segundo dataclass específico para operaciones WRITE
(`WriteResult` con `operation_id`/`dry_run`/`audit`) sin romper las 30+
tools READ/VALIDATE que ya devuelven el contrato simple.

Igual con la taxonomía de errores de `02_mcp_crud_read_write.md`
(`AUTHENTICATION_ERROR`, `TENANT_SCOPE_ERROR`, `BUSINESS_RULE_ERROR`,
`STATE_TRANSITION_ERROR`, `INTEGRITY_ERROR`, `IDEMPOTENCY_REPLAY`,
`EXTERNAL_INTEGRATION_ERROR`, ...) — más granular que los `status`
reales usados hoy (`OK`/`VALIDATION_ERROR`/`PERMISSION_DENIED`/
`NOT_FOUND`/`INTERNAL_ERROR`). Se adopta como **regla para cuando
existan tools WRITE**, no retroactiva sobre las tools READ ya
implementadas (ninguna necesita distinguir `STATE_TRANSITION_ERROR` de
`VALIDATION_ERROR` porque ninguna cambia estado).

## 5. Reglas ya cumplidas estructuralmente (confirmación, no trabajo nuevo)

Verificado contra el código real, estas reglas de las skills ya se
cumplen sin cambios:

- "Nunca aceptar `tenant_id`/`schema_name`/`empresa_id` del agente" → `build_context()` nunca lee el payload (`AI_SECURITY_MODEL.md`).
- "No crear RBAC/Service Layer/CRUD/grafo/vector DB paralelos" → cumplido en las 12 tools `platform` de LOOP 1 (todas envuelven fuentes reales: `tools/ekg/`, `tools/organizational_governance/`, registro vivo de Django).
- "No ejecutar SQL/shell/Python arbitrario" → ninguna tool nueva de esta sesión importa `connection.cursor()` directo salvo `production_readiness`/`migration_check`, que solo REUTILIZAN checks ya existentes del proyecto (no construyen SQL desde el input del agente).
- "Prohibido `rm -rf`/`DROP DATABASE`/`docker system prune`/etc. desde MCP" → ninguna tool los expone; no aplica todavía porque no hay capa de ejecución de comandos en absoluto.
- Flujo `OBSERVE → DISCOVER → RESOLVE CONTEXT → AUTHORIZE → VALIDATE → ...` → es el mismo flujo que `AIEngine.run_tool()` ya implementa estructuralmente para READ/VALIDATE (los pasos DRY RUN/CONFIRM/EXECUTE no aplican porque no hay WRITE).

## 6. Qué cambia esto para el trabajo futuro (la "regla" pedida)

A partir de este documento, toda tool nueva del catálogo `platform` o
de negocio debe:

1. Registrar su fila en `MCP_TOOL_CATALOG.md` usando el vocabulario de
   la skill 10 cuando exista equivalencia (para que alguien que lea las
   skills primero encuentre el mapeo sin buscar).
2. Si su `kind` es `WRITE`/`CODE_MODIFICATION`: **no se implementa sin
   pedir autorización explícita al usuario primero** — coincide
   exactamente con la Regla Absoluta de las skills 00/07 y con
   `AUTO_APPROVED_KINDS` ya estructural en `ai_engine.py`. Esta sesión
   no implementó ninguna, por diseño.
3. Cumplir el "Capability contract" YAML de la skill 01 como checklist
   de discovery antes de proponer cualquier tool nueva sobre un modelo
   de negocio no auditado todavía.
4. Cualquier ampliación de `ToolResult`/taxonomía de errores (§4 arriba)
   se decide una sola vez, documentada aquí, no ad-hoc por tool.

## 7. Estado del catálogo tras esta reconciliación

Sin cambios de código en esta pasada (documento de alineación, §65 del
prompt maestro original: LOOP 0/reconciliación no modifica código de
negocio). `MCP_TOOL_CATALOG.md`/`MCP_RELEASE_GATE.md` se actualizan
para referenciar este documento y agregar `crud_capabilities` como fila
`DESIGNED` nueva.
