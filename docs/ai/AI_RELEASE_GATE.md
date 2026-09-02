# AI_RELEASE_GATE — Fases 60-61, 66 (+ gates AI-01..AI-10, misión evolución 2026-09-01)

`AI_ENGINE = VERIFIED` solo si TODOS los ítems de la Fase AI-43 están
en `[x]`, **en orden** (AI-42: WRITE nunca empieza si AI-01..AI-09 no
están `VERIFIED`).

## Gates por fase (misión de evolución READ_ONLY → contextual)

```
[x] AI-01 Context Engine       = VERIFIED (2026-09-01) -- test explicito A != B agregado
[~] AI-02 EKG Contextual        = PARCIAL -- ai_project_map real (owner/rules/docs/fk), sin process resolution (AI-02.4)
[x] AI-03 READ/SUGGEST Tools     = VERIFIED (2026-09-01) -- 10 dominios con tool real (clientes, inventario, proveedores, ventas, compras, cotizaciones, gastos, proyectos, facturas, empleados, bancos, contabilidad = 12; impuestos/reporting DEFERRED formalmente, no deuda). Ver AI_TOOL_REGISTRY.md "Cierre formal de AI-03".
[~] AI-04 Validation Engine       = PARCIAL -- 6 tools reales (clientes, proveedores, inventario, compras, cotizaciones, gastos); ventas investigado y descartado por falta de validate() real (no wrap-a-ciegas); facturas/empleados/bancos/contabilidad no aplican (READ-only/import-only/ya valida internamente); impuestos/reporting DEFERRED
[ ] AI-05 Suggestion Engine        = BLOQUEADO POR DISEÑO (investigado 2026-09-01) -- no hay logica de negocio real que envolver, ver seccion abajo
[~] AI-06 Form Assistant             = PARCIAL (2026-09-01) -- orquestador real (apps/services/ai/orchestrator/), primer caller real de AIProvider; sin endpoint HTTP todavia (decision aparte)
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

## AI-03 = VERIFIED — evidencia (actualizado 2026-09-01, cierre formal)

Completado en el orden acordado con el usuario tras su mensaje de
priorización estratégica: `task_a8ca8af1` (hallazgo no-relacionado) →
`facturas` READ-only → `AI_SECURITY_MODEL.md` → `empleados` → `bancos`
→ diseño de integración con el Asistente Contable
(`AI_CONTABILIDAD_INTEGRATION.md`) → `contabilidad`. 12 tools READ/
SUGGEST reales cubriendo 10 dominios de negocio (`clientes`,
`inventario`, `proveedores`, `ventas`, `compras`, `cotizaciones`,
`gastos`, `proyectos`, `facturas`, `empleados`, `bancos`,
`contabilidad`) + `ai_project_map` (platform/EKG). `impuestos`/
`reporting` quedan `DEFERRED` formalmente (decisión explícita, no
deuda técnica) -- ver `AI_TOOL_REGISTRY.md` "Definición de AI-03
terminado" y "Cierre formal de AI-03" para el criterio exacto que
sustenta declarar VERIFIED sin cobertura de los 13 dominios.

## AI-04 = PARCIAL — evidencia (2026-09-01, primer lote)

6 tools `validar_*` reales (`clientes`, `proveedores`, `inventario`,
`compras`, `cotizaciones`, `gastos`), todas envolviendo el
`Serializer.is_valid()` de ESCRITURA real de cada dominio (nunca
reimplementan la regla) -- ver `AI_TOOL_REGISTRY.md` §"AI-04
(Validation Engine)" para el árbol VERIFIED/PENDIENTE completo y los
hallazgos reales encontrados durante la implementación (limitaciones
honestas de cada tool, no solo éxitos). `ventas` fue investigado y
**deliberadamente no implementado**: `VentaDetailSerializer` no tiene
un método `validate()` propio verificable, y envolverlo tal cual solo
validaría campos superficiales, no las reglas de negocio reales
(posiblemente ligadas a `COMERCIAL-05`, la máquina de estados
Venta↔Factura que el usuario ya identificó como trabajo separado) --
se prefirió no implementar antes que implementar algo engañoso.
`facturas`/`empleados`/`bancos`/`contabilidad` no aplican (dominios
READ-only/import-only, o el Asistente Contable ya valida
internamente antes de sugerir). `impuestos`/`reporting` siguen
`DEFERRED`.

## AI-05 = BLOQUEADO POR DISEÑO — investigación real (2026-09-01)

Antes de escribir ninguna tool `SUGGEST` nueva se investigó si existe
lógica de negocio real que envolver (mismo criterio que AI-03/AI-04:
nunca inventar lógica dentro de `apps/services/ai/`, solo orquestar lo
que ya existe). Búsqueda exhaustiva (`grep -rn "def sugerir_\|def
suggest_" apps/tenant/*/services/*.py apps/public/*/services/*.py`):
**la única función de sugerencia real en todo el ERP es
`ContabilidadBusinessService.sugerir_lineas_asiento_ia()`**, ya
envuelta por `sugerir_asiento_contable` desde AI-03.

Se evaluó una candidata adicional: `ContabilidadBusinessService.
inferir_y_crear_plantilla_desde_documento()` (línea 895) usa
`ReglaContable` (mapa concepto→cuenta, sin LLM) para inferir cuentas
contables -- en apariencia un buen candidato para una tool `SUGGEST`
determinística, sin dependencia de Anthropic. **Descartada**: pese a
su nombre parcial ("inferir"), el método **escribe** en la base de
datos -- crea un `PlantillaContable` real (`PlantillaContable.objects.
create(..., activo=False)`), aunque quede inactivo. Envolverla como
`SUGGEST` violaría la Regla Absoluta 6/7 (ninguna escritura se
auto-aprueba, y `SUGGEST` está en `AUTO_APPROVED_KINDS`) -- necesitaría
primero una refactorización en `apps/tenant/contabilidad/` que separe
el cálculo puro (qué cuentas aplicarían) de la persistencia del
borrador, que está fuera del alcance del AI Engine (tocaría lógica de
negocio de otra app, Regla Absoluta 1).

**Conclusión honesta**: AI-05 como "Suggestion Engine" genérico no
tiene más lógica real que envolver hoy sin (a) que el AI Engine
empiece a generar sugerencias por su cuenta con un prompt propio
(prohibido -- convertiría al AI Engine en una segunda capa de
negocio, exactamente lo que `AI_CONTABILIDAD_INTEGRATION.md` advierte
evitar) o (b) que una app de dominio (ej. `contabilidad`) exponga
primero una función de sugerencia pura (sin escritura) para envolver,
lo cual es trabajo de esa app, no del AI Engine. Se documenta como
`BLOQUEADO POR DISEÑO`, no como `DEFERRED`: no es una decisión de
"fuera de alcance", es una dependencia real (una función pura que
sugerir) que hoy no existe.

## AI-06 = PARCIAL — evidencia (2026-09-01, elegido por el usuario tras el bloqueo de AI-05)

`apps/services/ai/orchestrator/` (`ask(request, message, screen=None)`)
es el **primer caller real** de `AIProvider`/`AnthropicProvider` en
todo el AI Engine -- verificado antes de este commit:
`apps/services/ai/providers/` solo se importaba desde tests, nunca
desde un flujo real (`AI_ENGINE_ARCHITECTURE.md` ya lo documentaba
como "listo para cuando exista un flujo real", Fase 17+). Implementa
exactamente ese diseño: recibe lenguaje natural + contexto de
pantalla opcional (Fase 23, `build_context(screen=...)`, hasta ahora
sin ningún caller real tampoco), pide al LLM que elija UNA tool ya
registrada (`tool_metadata()`) respondiendo JSON puro (mismo patrón
que `sugerir_lineas_asiento_ia()`, no el protocolo nativo de tool-use
de Anthropic), y ejecuta la decisión exclusivamente vía
`AIEngine.run_tool()` -- el orquestador nunca llama `tool.run()`
directo, así que toda la seguridad estructural ya existente (flags,
`AUTO_APPROVED_KINDS`, contexto real) sigue aplicando sin
reimplementarla.

**Deliberadamente PARCIAL, no VERIFIED**: no hay endpoint HTTP
todavía. Exponer una URL (`BaseTenantViewSet`, dual-auth JWT/session,
nueva superficie de ataque real) es una decisión separada que merece
su propio commit/revisión -- mismo criterio que `AIEngine.run_tool()`
se construyó primero como motor puro testeable antes de que existiera
cualquier tool real que lo ejercitara.

Guardrail de Fase 55 (prompt injection) aplicado, no solo diseñado: el
`system` prompt instruye explícitamente al modelo a tratar el mensaje
del usuario como **dato**, nunca como instrucción a seguir si
contradice las reglas -- primer caso real de esta regla implementada
en código, antes solo estaba documentada en `AI_SECURITY_MODEL.md`
como "ningún flujo real la ejercita todavía".

Defensa en profundidad probada con test explícito: si el LLM
"alucina" un nombre de tool inexistente, el orquestador NO lo valida
él mismo -- confía en que `AIEngine.run_tool()` lo rechace con
`NOT_FOUND` (`test_llm_alucina_tool_inexistente_es_manejado_por_ai_engine`).

## Corrida real de tests (2026-09-01, corrida mas reciente)

```
apps/services/ai/tests/ -- 78 items
78 passed, 2 warnings (warnings preexistentes de DRF, no relacionados)
```

## Corrida real de tests (2026-09-01, corrida original de esta seccion, historica)

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

Progreso real sobre la pasada anterior (AI-01 y AI-03 ahora VERIFIED,
AI-02/AI-04/AI-06 parciales, AI-05 investigado y BLOQUEADO POR
DISEÑO), pero el criterio de la Fase AI-43 exige los 10 gates en `[x]`
— siguen 4 en `no iniciado`, 1 `BLOQUEADO POR DISEÑO` y 3 en `parcial`
(AI-02, AI-04, AI-06). No se declara `VERIFIED` por progreso parcial
(Regla Absoluta 10 de la misión original: nunca afirmar completado lo
que no lo está).

## Checklist heredado (misión anterior, Fases 60-61, sigue vigente)

```
[x] provider abstraction        -- AIProvider (ABC) implementado
[x] Anthropic compatible        -- AnthropicProvider real, reutiliza el patron del Asistente Contable; AI-06 es su primer caller real (antes solo se importaba desde tests)
[ ] OpenAI compatible           -- diseñado (AI_PROVIDER_MATRIX.md), no implementado -- sin caller real que lo ejerza
[ ] local provider              -- diseñado, no implementado, mismo motivo
[x] context engine              -- AI-01 VERIFIED (ver arriba)
[~] EKG integration             -- AI-02 PARCIAL (ver arriba) -- antes "no implementado", ahora real y parcial
[x] User Access Context         -- build_context() deriva SIEMPRE de request.user.tenant_profile, nunca del payload
[x] tool registry               -- AIToolRegistry real, con metadata serializable, probado
[x] read tools                  -- AI-03 VERIFIED: 12 tools READ/SUGGEST reales, 10 dominios de negocio + platform/EKG, impuestos/reporting DEFERRED formalmente
[~] validation tools            -- AI-04 PARCIAL: 6 tools reales (clientes, proveedores, inventario, compras, cotizaciones, gastos); ventas investigado y descartado (sin validate() real que envolver), ver AI_TOOL_REGISTRY.md
[ ] suggestion tools            -- AI-05 BLOQUEADO POR DISEÑO (investigado 2026-09-01) -- sin funcion de sugerencia pura que envolver mas alla de sugerir_lineas_asiento_ia (ya cubierta en AI-03)
[x] write controls              -- AUTO_APPROVED_KINDS excluye WRITE incondicionalmente -- estructural, no solo documentado
[ ] approvals (flujo real)      -- no implementado -- consecuencia directa de no tener tools WRITE todavia
[~] audit                       -- logging real por tool call (tool/kind/status/user/empresa), sin persistencia estructurada ni trace_id
[~] tracing                     -- logging basico real; tracing de workflow completo NO implementado (AI_TRACING.md)
[ ] session (memoria)           -- diseñada (AI_MEMORY_POLICY.md), no implementada -- sin flujo conversacional real que la necesite
[x] tenant isolation            -- garantia de SCHEMA ya verificada en otras misiones de esta sesion (TEN-01); a nivel de tool se prueba que empresa_id viene siempre del contexto real
[x] prompt injection defense    -- AI-06 implementa el guardrail real (Fase 55): el system prompt marca el mensaje del usuario como dato, nunca instruccion -- primer flujo real que lo ejercita
[~] sensitive data controls     -- empleados/bancos/contabilidad ya tienen tools reales con clasificacion aplicada (AI_SECURITY_MODEL.md) -- 2 tools SENSITIVE_READ + 1 SUGGEST probadas, no solo diseñadas
[ ] MCP read                    -- MCP sigue inerte (0 ViewSets decorados) -- sin cambios en esta pasada, deliberado
[ ] MCP write controls          -- N/A, MCP read tampoco existe
[x] tests                       -- 78/78 PASS (corrida completa mas reciente, apps/services/ai/tests/)
[x] governance                  -- manage.py check PASS, makemigrations --check PASS, git diff --check PASS
[x] documentation                -- 14 documentos en docs/ai/ (12 originales + AI_SECURITY_MODEL.md ampliado + AI_CONTABILIDAD_INTEGRATION.md nuevo), todos distinguiendo implementado vs diseñado
```

## Fase 62 — Go-live controlado

```
READ_ONLY_ASSISTANT     <- CERRADO (AI-03 VERIFIED, 12 tools) -- flags en False por defecto
VALIDATION_ASSISTANT    <- EN PROGRESO (AI-04 PARCIAL, 6 tools) -- flags en False por defecto
SUGGESTION_ASSISTANT    <- BLOQUEADO POR DISEÑO (AI-05 investigado 2026-09-01 -- sin logica pura que envolver, ver seccion arriba)
FORM_ASSISTANT           <- EN PROGRESO (AI-06 PARCIAL, orquestador real sin endpoint HTTP) -- flags en False por defecto
WRITE_ASSISTANT         <- no alcanzado, BLOQUEADO por diseño (AI-42) hasta AI-01..AI-09 = VERIFIED
```

## Siguiente paso real (2026-09-01, actualizado tras AI-06)

AI-03 está cerrado, AI-04 y AI-06 tienen su primer lote real hecho.
AI-05 sigue `BLOQUEADO POR DISEÑO` (sin función de sugerencia pura que
envolver). El usuario eligió explícitamente **AI-06 (Form Assistant)**
cuando se le presentó el bloqueo de AI-05 (vía `AskUserQuestion`,
2026-09-01) -- se implementó el orquestador real
(`apps/services/ai/orchestrator/`), primer caller real de
`AIProvider`, pero **sin endpoint HTTP todavía** (decisión de
superficie de ataque separada, no bloqueante para el resto). Próximos
pasos reales disponibles: exponer el endpoint HTTP de AI-06 (requiere
diseño de permisos/dual-auth, ver `AGENTS.md` §15), o avanzar a AI-07
(MCP Read) -- ninguno depende de que AI-05 se desbloquee. AI-02.4
(process resolution) sigue como trabajo genuino adicional, no
bloqueante.
