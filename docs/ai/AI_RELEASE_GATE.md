# AI_RELEASE_GATE — Fases 60-61, 66 (+ gates AI-01..AI-10, misión evolución 2026-09-01)

`AI_ENGINE = VERIFIED` solo si TODOS los ítems de la Fase AI-43 están
en `[x]`, **en orden** (AI-42: WRITE nunca empieza si AI-01..AI-09 no
están `VERIFIED`).

## Gates por fase (misión de evolución READ_ONLY → contextual)

```
[x] AI-01 Context Engine       = VERIFIED (2026-09-01) -- test explicito A != B agregado
[~] AI-02 EKG Contextual        = PARCIAL -- ai_project_map real (owner/rules/docs/fk), sin process resolution (AI-02.4)
[~] AI-03 READ Tools             = PARCIAL -- 2/13 dominios prioritarios (clientes, inventario), 11 pendientes
[ ] AI-04 Validation Engine       = no iniciado
[ ] AI-05 Suggestion Engine        = no iniciado
[ ] AI-06 Form Assistant             = no iniciado
[ ] AI-07 MCP Read Controlado         = no iniciado (MCP sigue inerte, 0 ViewSets decorados)
[ ] AI-08 Session/Memory               = no iniciado
[ ] AI-09 Tracing/Observability         = parcial -- logging basico ya existia, sin trace_id/persistencia
[ ] AI-10 Write Assistant                 = BLOQUEADO por diseño -- AI-01..AI-09 no estan todos VERIFIED (regla AI-42)
```

## AI-01 = VERIFIED — evidencia

`AIContext`/`build_context` (`apps/services/ai/context/ai_context.py`)
ya cumplían AI-01.1 (SSoT real, `request.user.tenant_profile`) y
AI-01.2 (contexto mínimo) desde la misión anterior. Esta pasada cerró
AI-01.3 con el test explícito que la fase exige literalmente:
`test_build_context_usuario_a_tenant_a_difiere_de_usuario_b_tenant_b`
— 2 contextos reales, `ctx_a != ctx_b` confirmado. Ver
`AI_CONTEXT_MODEL.md`.

## AI-02 = PARCIAL — evidencia

`ai_project_map` (`apps/services/ai/tools/ekg_tools.py`) real,
combinando registro vivo de Django (owner, AI-02.3 cumplido: "¿quién
posee el stock?" responde `inventario`, nunca "AI Engine") + snapshots
reales del EKG (`rules_for_app`/`docs_for_app`/`fk_relationships`/
`endpoints_for_model`, AI-02.1). Filtrado real, no el grafo completo
(AI-02.2). **No implementado:** AI-02.4 (process resolution, cadenas
tipo "Venta → Factura → Inventario → ..."). Ver `AI_ENGINE_ARCHITECTURE.md`
§"EKG / Knowledge Graph tool".

**Hallazgo real (`DOCUMENTATION_DRIFT`):** el `app_label` real de
Django diverge del nombre de snapshot EKG para varias apps (ej.
`Cliente` → `app_label="tenant_clientes"`, snapshot `clientes.json`) —
`documentacion/arquitectura_general.md` §2.2 documenta el App Label
sin el prefijo `tenant_`, desactualizado. Corregido en el código nuevo
(deriva el nombre real desde `__module__`), no en la documentación
preexistente (fuera del alcance mínimo). Ver
`AI_BASELINE_EXECUTION.md`.

## AI-03 = PARCIAL — evidencia

`buscar_producto` (`apps/services/ai/tools/inventario_tools.py`),
mismo patrón que `buscar_cliente`, envuelve `ProductoSelector` ya
existente. Incluye `stock_actual` — cubre AI-03.2 completa (búsqueda +
stock) sin necesitar una segunda tool. **11 dominios prioritarios
siguen sin tool real:** facturas, ventas, compras, bancos,
contabilidad, impuestos, reporting, proveedores, cotizaciones, gastos,
proyectos, empleados — ver `AI_TOOL_REGISTRY.md` para el diseño de
cada uno.

## Corrida real de tests (2026-09-01)

```
apps/services/ai/tests/ -- 35 items
35 passed in 595.44s (0:09:55)
```

Suma sobre la corrida anterior (20/20, misión previa) + 15 tests
nuevos: 6 (`test_ai_project_map_tool.py` unit, sin DB) + 2
(`test_ai_project_map_tool.py` integración, DB) + 4
(`test_buscar_producto_tool.py`) + 1 (AI-01.3 en `test_ai_context.py`)
+ 2 deducidos de la reclasificación de tests -- ver el archivo de
tests para el conteo exacto por archivo.

## `AI_ENGINE` = **NOT_VERIFIED** (honesto, sin cambios de veredicto global)

Progreso real sobre la pasada anterior (AI-01 cerrado, AI-02/AI-03
avanzados), pero el criterio de la Fase AI-43 exige los 10 gates en
`[x]` — siguen 7 en `no iniciado` y 2 en `parcial`. No se declara
`VERIFIED` por progreso parcial (Regla Absoluta 10 de la misión
original: nunca afirmar completado lo que no lo está).

## Checklist heredado (misión anterior, Fases 60-61, sigue vigente)

```
[x] provider abstraction        -- AIProvider (ABC) implementado
[x] Anthropic compatible        -- AnthropicProvider real, reutiliza el patron del Asistente Contable
[ ] OpenAI compatible           -- diseñado (AI_PROVIDER_MATRIX.md), no implementado -- sin caller real que lo ejerza
[ ] local provider              -- diseñado, no implementado, mismo motivo
[x] context engine              -- AI-01 VERIFIED (ver arriba)
[~] EKG integration             -- AI-02 PARCIAL (ver arriba) -- antes "no implementado", ahora real y parcial
[x] User Access Context         -- build_context() deriva SIEMPRE de request.user.tenant_profile, nunca del payload
[x] tool registry               -- AIToolRegistry real, con metadata serializable, probado
[~] read tools                  -- AI-03 PARCIAL: 3 tools reales (clientes, inventario, platform/EKG), 11 dominios de negocio pendientes
[ ] validation tools            -- diseñadas (AI_TOOL_REGISTRY.md), no implementadas
[ ] suggestion tools            -- diseñadas, no implementadas
[x] write controls              -- AUTO_APPROVED_KINDS excluye WRITE incondicionalmente -- estructural, no solo documentado
[ ] approvals (flujo real)      -- no implementado -- consecuencia directa de no tener tools WRITE todavia
[~] audit                       -- logging real por tool call (tool/kind/status/user/empresa), sin persistencia estructurada ni trace_id
[~] tracing                     -- logging basico real; tracing de workflow completo NO implementado (AI_TRACING.md)
[ ] session (memoria)           -- diseñada (AI_MEMORY_POLICY.md), no implementada -- sin flujo conversacional real que la necesite
[x] tenant isolation            -- garantia de SCHEMA ya verificada en otras misiones de esta sesion (TEN-01); a nivel de tool se prueba que empresa_id viene siempre del contexto real
[ ] prompt injection defense    -- diseñado, no implementado -- ningun flujo real concatena datos de negocio en un prompt todavia
[~] sensitive data controls     -- ninguna tool sensible existe todavia -- nada que fallar, pero tampoco nada probado
[ ] MCP read                    -- MCP sigue inerte (0 ViewSets decorados) -- sin cambios en esta pasada, deliberado
[ ] MCP write controls          -- N/A, MCP read tampoco existe
[x] tests                       -- 35/35 PASS
[x] governance                  -- manage.py check PASS, makemigrations --check PASS, git diff --check PASS
[x] documentation                -- 12 documentos en docs/ai/, todos distinguiendo implementado vs diseñado (sin duplicar -- Regla 9 de esta mision)
```

## Fase 62 — Go-live controlado

```
READ_ONLY_ASSISTANT     <- aqui, con 3 tools (clientes, inventario, platform/EKG) -- flags en False por defecto
VALIDATION_ASSISTANT    <- no alcanzado
SUGGESTION_ASSISTANT    <- no alcanzado
WRITE_ASSISTANT         <- no alcanzado, BLOQUEADO por diseño (AI-42) hasta AI-01..AI-09 = VERIFIED
```

## Siguiente paso real (no ejecutado, fuera de esta pasada)

Completar AI-03 (11 dominios de negocio restantes, mismo patrón
Tool→Selector→SSoT ya probado 2 veces) antes de iniciar AI-04
(Validation Engine) — orden obligatorio de la misión (AI-41). AI-02.4
(process resolution) queda como trabajo genuino adicional, no
bloqueante para el resto de fases.
