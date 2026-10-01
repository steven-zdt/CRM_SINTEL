# ADK_TOOL_CONTRACT — Fase 3 (Tool Contract)

**Fecha:** 2026-09-22
**Fuente:** `PLAN_MAESTRO_INTEGRACION_GOOGLE_ADK_ASISTENTE_IA_SINTEL.md` §61, §29-36
**Depende de:** `docs/adk/ADK_DOMAIN_INVENTORY.md` (Fase 1), `docs/adk/ADK_KNOWLEDGE_MAP.md` (Fase 2)

STATUS FASE 3: **PASS** (documental — formaliza el contrato ya vigente en código para READ/VALIDATE/SUGGEST; especifica, sin implementar todavía, lo que falta para WRITE).

---

## Parte A — READ / VALIDATE / SUGGEST: contrato YA implementado, no a diseñar de nuevo

El plan (§30) pide que cada tool declare `name, domain, risk_level, read_only, required_permission, input_schema, output_schema, idempotent, supports_preview, supports_rollback, audit_event`. Comparado campo a campo contra `apps/services/ai/tools/base.py::BaseTool` + `registry.py::tool_metadata()`:

| Campo pedido por el plan | Existe hoy como | Estado |
|---|---|---|
| `name` | `BaseTool.name` | PASS |
| `domain` | `BaseTool.domain` | PASS |
| `risk_level` | `BaseTool.risk` (`ToolRisk`) | PASS (más granular: 5 niveles, no 4) |
| `read_only` | derivado de `BaseTool.kind` (`READ`/`VALIDATE`/`SUGGEST` = siempre read-only; solo `WRITE` no lo es) | PASS |
| `required_permission` | `AIContext` + `IsTenantMember` (permiso único de acceso al Engine, no por tool — ver `ADK_KNOWLEDGE_MAP.md` "Permisos") | PASS (modelo distinto al del plan, pero cubre el mismo requisito) |
| `input_schema` | firma de `tool.run(context, **kwargs)` por tool (no un JSON Schema formal) | **PARCIAL** — funciona, pero no hay un schema declarativo que ADK pueda leer sin inspeccionar código. Candidato real de trabajo en Fase 4 (adaptador ADK → tool: ahí es donde generar/declarar el schema, no antes). |
| `output_schema` | `ToolResult` (`status`, `data`, `message`) — normalizado, igual para las 18 tools | PASS |
| `idempotent` | `BaseTool.idempotent` (bool, ya en `tool_metadata()`) | PASS — declarado; para READ/VALIDATE/SUGGEST es trivialmente cierto (no mutan nada). |
| `supports_preview` | N/A para READ/VALIDATE/SUGGEST (no aplica — nada que confirmar antes de ejecutar una lectura) | N/A, correcto por diseño |
| `supports_rollback` | N/A por el mismo motivo | N/A |
| `audit_event` | `logger.info("ai_engine.tool_call ...")` en `AIEngine.run_tool()` | **PARCIAL** — logging real, sin persistencia estructurada ni `trace_id` (ver Parte C). |

**Conclusión Parte A:** no hay que diseñar un contrato nuevo para READ/VALIDATE/SUGGEST — ya existe, ya se usa en 18 tools reales, y ADK debe consumirlo tal cual (leer `tool_metadata()`, invocar siempre vía `AIEngine.run_tool()`, nunca `tool.run()` directo — el orquestador `form_assistant.py` ya establece este precedente).

---

## Parte B — WRITE: contrato especificado aquí, NO implementado (correcto para esta fase)

Cero tools `WRITE` existen hoy (Fase 1). El plan exige, antes del primer WRITE real (Fase 7, §65), que el contrato cubra §31-36. Esta sección fija ese contrato para que la Fase 7 lo implemente sin reinterpretarlo — no se escribe código de WRITE en esta fase.

### B.1 — Resultado estructurado (§31)

Toda tool `WRITE` debe devolver, dentro del `ToolResult.data` ya existente (sin cambiar la forma de `ToolResult` en sí):

```json
{
  "ok": true,
  "status": "CREATED",
  "entity": { "type": "cliente", "uuid": "..." },
  "warnings": [],
  "errors": [],
  "audit_id": "..."
}
```

`ToolResult.status` (el campo que YA existe: `OK | VALIDATION_ERROR | PERMISSION_DENIED | NOT_FOUND | CONFLICT | DOMAIN_ERROR`) se reutiliza tal cual — no se necesita un segundo campo de estado. `entity`/`audit_id` van dentro de `ToolResult.data`.

### B.2 — Write idempotente (§32)

**No inventar un mecanismo nuevo.** `apps/tenant/facturas/services/business_service.py` y `electronic_invoice_service.py` ya implementan idempotencia real para la transmisión fiscal (probado en `test_fiscal_04_idempotencia_transmision.py`, suite en PASS). Cada dominio que reciba una tool `WRITE` en Fase 7+ debe usar el mecanismo de idempotencia que YA tenga ese dominio (constraint único, estado + reintento controlado, etc.) — si el dominio no tiene ninguno, construirlo es trabajo de ESE dominio (Service Layer), no de la capa de IA, coherente con la Regla Absoluta 1 del propio AI Engine ("nunca lógica de negocio dentro de `apps/services/ai/`").

### B.3 — Preview / `MutationPlan` (§33)

Antes de ejecutar cualquier `WRITE`, la tool debe poder construir (sin persistir nada) un plan:

```json
{
  "action": "CREATE",
  "domain": "clientes",
  "changes": { "razon_social": "ABC", "nit": "900..." },
  "risk": "LOW_WRITE",
  "requires_confirmation": true
}
```

Esto implica que cada futura tool `WRITE` se implemente en **dos pasos explícitos** desde el inicio (no como un añadido posterior): `plan_<accion>()` (puro, sin escritura) y `ejecutar_<accion>()` (solo tras aprobación). El `BusinessService` del dominio ya suele separar validación de persistencia (Fase 1: `Serializer.is_valid()` ya es el paso de validación reutilizado por las tools `VALIDATE`) — el paso de preview de Fase 7 se apoya en esa misma separación, no en una nueva.

### B.4 — Approval tool (§34)

`request_approval` / `resolve_approval` son mecanismos **transversales** (no por dominio) — deben vivir en `apps/services/ai/` (junto a `engine`/`context`/`registry`), no duplicarse por app. Consecuencia directa de la Regla Absoluta de "no 5 implementaciones independientes" (plan §5): un solo par de funciones de aprobación para las 12 apps.

### B.5 — Supervisor post-write (§35)

Tras cualquier `WRITE`, releer la entidad persistida (vía el `Selector` real del dominio, no confiar en el eco de la escritura) antes de reportar éxito al usuario. Mismo principio que ya usa `ContabilidadBusinessService.sugerir_lineas_asiento_ia()` (revalida contra `CuentaContable` real antes de devolver la sugerencia) — se generaliza a "toda escritura se reconfirma leyendo de nuevo", no se inventa un patrón distinto.

### B.6 — Auditoría (§36)

Hoy: `logger.info` con `tool/kind/status/user/empresa` — sin `session_id`, sin `input hash`, sin persistencia. Antes de activar la primera tool `WRITE` (Fase 7), la auditoría debe pasar a un modelo persistido (nuevo, mínimo: `AIAuditLog` o equivalente, en el schema del tenant) con exactamente los campos que pide el plan: `session_id, user, tenant, agent, specialist, tool, input_hash, sanitized_input, approval, timestamp, result, entity_uuid, error` — nunca passwords/tokens/secret keys/datos sensibles no autorizados (mismo criterio que `INDEXABLE_SOURCES` ya aplica al RAG). Este modelo es trabajo real de Fase 7, no de esta fase.

---

## Parte C — Observabilidad (§37): gap real, no bloqueante para Fase 4-6

Medir latencia/tokens/tool calls/retrieval/errores/aprobaciones/writes/fallos no existe hoy más allá del logging básico. No bloquea el ADK Spike (Fase 4) ni el Router (Fase 6), que son READ-only — sí debe resolverse antes de Fase 7 (First Write), junto con B.6.

---

## Conclusión de Fase 3

```
FASE 3 — TOOL CONTRACT = PASS
```

READ/VALIDATE/SUGGEST: contrato ya vigente, documentado y verificado campo por campo. WRITE: contrato especificado (B.1-B.6) para que la Fase 7 lo implemente sin ambigüedad, cero código WRITE escrito en esta fase — consistente con la Regla Absoluta del plan (§1: nunca empezar por WRITE indiscriminado) y con el estado real del sistema (`AUTO_APPROVED_KINDS` sigue bloqueando estructuralmente cualquier WRITE).

Con esto se cierran las 4 fases documentales que no requieren decisión externa (0, 1, 2, 3). La Fase 4 (ADK Spike) es el primer punto que requiere instalar una dependencia nueva (`google-adk`) y decidir qué LLM va a hablar con ella — ver `docs/adk/ADK_BASELINE.md` "Decisión pendiente" y `docs/adk/ADK_STATUS.md`.
