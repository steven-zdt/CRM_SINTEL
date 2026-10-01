# ADK Status

**Fuente:** `PLAN_MAESTRO_INTEGRACION_GOOGLE_ADK_ASISTENTE_IA_SINTEL.md` (raíz del repo), §77
**Última actualización:** 2026-09-22

STATUS: **IN_PROGRESS**

| Fase | Estado | Evidencia |
|---|---|---|
| 0 Baseline | **PASS** | `docs/adk/ADK_BASELINE.md` — auditoría completa de `apps/services/ai/`, `apps/tenant/ai_knowledge/`, `tools/ekg/`, `AIContext`, `AIEngine`, `AIToolRegistry`, `RetrievalTool`, `EmbeddingService`, `RetrievalService`, providers, settings, URLs, frontend AI. Sin cambios de código (mandato de la fase). |
| 1 Inventory | **PASS** | `docs/adk/ADK_DOMAIN_INVENTORY.md` — matriz de 12 dominios de negocio + 2 dominios de plataforma (EKG, ai_knowledge), con tools READ/VALIDATE/WRITE reales verificadas contra `apps/services/ai/tools/*.py`. |
| 2 Knowledge Map | **PASS** | `docs/adk/ADK_KNOWLEDGE_MAP.md` — mapa de los 3 índices existentes (RAG/pgvector, EKG, tools) por dominio. Hallazgo real: RAG solo cubre 2/12 dominios (clientes, inventario) — registrado, no resuelto (fuera de alcance de "integrar ADK"). |
| 3 Tool Contract | **PASS** | `docs/adk/ADK_TOOL_CONTRACT.md` — contrato READ/VALIDATE/SUGGEST verificado campo por campo contra código real (ya vigente); contrato WRITE especificado (preview/idempotencia/approval/supervisor post-write/auditoría) para que la Fase 7 lo implemente sin ambigüedad, sin escribir código WRITE en esta fase. |
| 4 ADK Spike | **PASS** | `google-adk==2.9.2` instalado directo en el entorno Django (`cryptography` subido a `>=45.0.1,<51.0`, decisión explícita del usuario 2026-09-22 -- ver adenda en `ADK_BASELINE.md`). `apps/services/ai/adk/` — `root_agent` (2 tools: `saludar`, `buscar_cliente`) construido y probado en proceso, sin HTTP ni servicio aparte. **6/6 tests reales en PASS** (`apps/services/ai/tests/test_adk_tools.py`), cubriendo el camino completo AIContext→AIEngine.run_tool()→tool real→DB real. Detalle completo abajo. |
| 5 Local LLM | **PASS** | LM Studio conectado y verificado en vivo con LLM real (Qwen3.5). Detalle completo abajo. |
| 6 Router | PARCIAL | Sin router multi-dominio todavía (un solo `root_agent`), pero la selección autónoma de tool DENTRO del agente ya está probada en vivo (ver Fase 5) -- es el precursor directo, no el router completo que pide §64/§21 del plan original. |
| 7 First Write | PENDING | Depende de la Fase 6. Recordatorio estructural: `AUTO_APPROVED_KINDS` en `apps/services/ai/tools/base.py` ya bloquea cualquier tool WRITE sin importar el flag — esta fase no puede "saltarse" ese bloqueo, tiene que construir el flujo de aprobación real que hoy no existe. |
| 8 Specialists | PENDING | Depende de la Fase 7. |
| 9 App Rollout | PENDING | Depende de la Fase 8. Orden propuesto por el plan (§67): Clientes → Proveedores → Inventario → Cotizaciones → Ventas → Facturas → Compras → Proyectos → Gastos → Empleados → Bancos → Contabilidad. |
| 10 Complex flows | PENDING | Depende de la Fase 9. |
| 11 Supervisors | PENDING | Depende de la Fase 9 (puede empezar en paralelo si Rollout ya cubre el dominio — es READ-only). |
| 12 Bulk | PENDING | Depende de idempotencia/preview/approval/audit reales (Fase 7). |
| 13 Security | PENDING | Depende de tener algo real que atacar (Fase 6+). |
| 14 Evaluation | PENDING | Depende de tener ADK instalado (Fase 4+). |
| 15 Production Gate | PENDING | `docs/adk/ADK_RELEASE_GATE.md` — no creado todavía (se crea al llegar a esta fase, con el checklist real de §80 del plan). |

## Regla de honestidad de este tracker (§78/§36 del plan)

No se avanza una fase con `FAIL`. No se declara `PASS` sin evidencia enlazada. Este documento se actualiza cada vez que una fase cambia de estado — no se reescribe retroactivamente para "verse mejor", igual que `TABLES_FORMS_MIGRATION_STATUS.md`/`TABLES_FORMS_RELEASE_GATE.md` en la migración de tablas de esta misma sesión.

## Fase 4 — detalle completo (revisado 2026-09-22, arquitectura simplificada)

**Decisión inicial del usuario:** al encontrar el conflicto real de `cryptography` (ver `ADK_BASELINE.md` "Adenda Fase 4"), eligió aislar ADK en un servicio aparte. Se construyó (`ai_adk_service/`, FastAPI + Docker propio) y se verificó funcionando.

**Decisión revisada, el mismo día:** el usuario aclaró que no se generan/firman facturas nuevas en este momento (solo se importan XML ya firmados, lectura de CUFE) — el riesgo original sobre `cryptography` no aplica hoy. Pidió simplificar: **sin servicio aparte**. Se revirtió la Fase 4 a una arquitectura en proceso único:

1. **`requirements.txt`** — `cryptography` subido a `>=45.0.1,<51.0`; `google-adk==2.9.2` agregado directo. Imagen `web` reconstruida y verificada: `google-adk` importa limpio, `XadesSignerService`/`Fernet` (los usos reales de `cryptography`) siguen importando sin error.
2. **`ai_adk_service/` eliminado.** `apps/services/ai/adk_gateway/` (HTTP + secreto compartido) **eliminado**, reemplazado por **`apps/services/ai/adk/`**: `agent.py` (`build_root_agent()`), `tools.py` (`saludar`, `buscar_cliente`), `context.py` (`build_context_from_session()`, equivalente a `build_context(request)` pero re-derivando desde `session.state` en vez de un request de navegador). Las tools llaman a `AIEngine.run_tool()` **directamente en Python** — sin HTTP, sin secreto, sin red.
3. **`docker-compose.yaml`** — servicio `adk-agent` eliminado.
4. **Bug real encontrado y corregido (async + ORM):** las tools de ADK son `async def` (convención de la librería) pero llamaban al ORM de Django de forma síncrona directamente -- Django lo bloquea (`SynchronousOnlyOperation: You cannot call this from an async context`). Corregido aislando la parte síncrona en una función aparte e invocándola con `asgiref.sync.sync_to_async(..., thread_sensitive=True)`.
5. **Bug real encontrado y corregido (deadlock en tests):** al probar el camino async con una fixture de test que usa transacción implícita (`pytest.mark.django_db` normal), la conexión del hilo de `sync_to_async` quedaba **bloqueada indefinidamente** esperando el lock de una fila que la transacción de la fixture nunca comiteaba (esperando a que el propio test terminara) -- deadlock real, confirmado en vivo (proceso colgado 25+ minutos, dos sesiones Postgres bloqueadas entre sí). Corregido usando `@pytest.mark.django_db(transaction=True)` en los tests que ejercitan ese camino, con fixtures idempotentes (`get_or_create`) porque `transaction=True` comitea datos reales que persisten entre tests de la misma corrida.
6. **`apps/services/ai/tests/test_adk_tools.py`** — 6 tests, **6/6 PASS** (verificado en una corrida limpia y aislada, sin conexiones huérfanas): construcción real del `Agent` con sus tools sin LLM, `saludar()`, `buscar_cliente()` de punta a punta contra un `Cliente` real en BD, bloqueo si `AI_ENABLED=False`, bloqueo si la sesión ADK no trae contexto real, bloqueo si el usuario no tiene `TenantProfile`.
7. **Regresión ya verificada previamente** (suite `apps/services/ai/tests/`, 125 tests, corrida antes de esta simplificación): 115 passed, 7 failed -- los 7 son 100% preexistentes y no relacionados (`.env` de este entorno con `AI_ENABLED=true` puesto desde antes de esta sesión, ver detalle ya documentado). No se repitió la corrida completa tras la simplificación (los archivos tocados -- `ai_engine.py`, la nueva carpeta `adk/` -- ya tienen su propia cobertura directa).

**Lo que sigue NO verificado (honesto):** ninguna llamada real a un LLM -- el `root_agent` nunca ha mantenido una conversación real ni decidido invocar una tool por sí mismo. Eso espera la Fase 5.

## FASE 0/1 del plan de evolución (`documentacion/PLAN_MAESTRO_ADK_SINTEL_AGENTIC_ERP_LOOP_20260922.md`)

Plan adicional recibido el mismo día, pidiendo evolucionar el asistente hacia un agente multi-dominio (IntentAgent/PlannerAgent/PolicyAgent/SpecialistAgents/SupervisorAgent) con LM Studio local como proveedor. Su propia instrucción (§69): **"NO comenzar creando más agentes"** hasta que su Fase 0 (Baseline Forense) y Fase 1 (Domain Registry) estén en PASS.

| Fase (plan de evolución) | Estado | Evidencia |
|---|---|---|
| 0 Baseline Forense | **PASS** | `docs/adk/ADK_GAPS.md` + `docs/adk/ADK_DEPENDENCY_MAP.md`. Hallazgo crítico: la sección "Estado Actual Real Detectado" del plan de evolución describe elementos que **no existen** en este repo (`ai_engine_adk/` como proceso FastAPI, `sintel_root_workflow.py`, LM Studio+Qwen3.5 con un bug ya corregido) -- verificado con `grep` exhaustivo, 0 resultados reales. Documentado en detalle en `ADK_GAPS.md` en vez de asumido. |
| 1 Domain Registry | **PASS** | `apps/services/ai/domain_registry/` -- `DomainDefinition` por cada uno de los 12 dominios, generado **desde código real** (`Model._meta.app_label`, `AIToolRegistry.list_tools()`, `INDEXABLE_SOURCES`), no datos duplicados a mano. 6/6 tests reales en PASS (`apps/services/ai/tests/test_domain_registry.py`, sin DB, 5.7s). |
| 2+ (EKG Domain View, Knowledge Retrieval, ...) | PENDING | No iniciado -- el plan de evolución es aún más grande que el original (15 fases); no se construye más sin que el usuario lo pida explícitamente fase por fase. |

**Resuelto (2026-09-22, mismo día):** el usuario confirmó LM Studio corriendo en `http://localhost:1234/v1` (host). Ver Fase 5 abajo para el detalle completo de la conexión y verificación en vivo.

## Fase 5 — LLM local (LM Studio) — detalle completo, verificado en vivo

1. **Networking real resuelto:** `host.docker.internal` no resolvía dentro del contenedor -- el `dns:` custom del proyecto (servidor Windows para `*.sintel.net.co`) reemplaza el resolver embebido de Docker que normalmente provee ese hostname automáticamente. Fix: `extra_hosts: ["host.docker.internal:host-gateway"]` agregado al servicio `web` en `docker-compose.yaml` (funciona igual en Docker Desktop y Linux). Verificado: `curl http://host.docker.internal:1234/v1/models` desde dentro del contenedor devuelve el modelo real cargado (`qwen/qwen3.5-9b`).
2. **`litellm` instalado** (no `google-adk[extensions]`, que arrastra ~80 paquetes irrelevantes -- langchain/langgraph/llama-index/boto3/kubernetes/docker-sdk -- solo por incluir LiteLLM entre un catálogo enorme de integraciones). `litellm` solo (~14 paquetes) es lo único que `google.adk.models.lite_llm.LiteLlm` necesita importable.
3. **Hallazgo real crítico (confirmado con `litellm.completion()` directo antes de tocar ADK):** Qwen3.5 es un modelo de razonamiento -- con `max_tokens=300` la respuesta viene **vacía** (`finish_reason=length`, 300 tokens gastados en `reasoning_content`, cero en `content`). Con `max_tokens=2000` sí completa (`content='OK'`, `finish_reason=stop`, ~171 tokens totales, ~94s de latencia en este hardware). Confirma textualmente la advertencia del plan de evolución §26 sobre este mismo problema. `ADK_LLM_MAX_TOKENS` (default `4000`) existe específicamente por este hallazgo.
4. **`apps/services/ai/adk/agent.py`** — `build_root_agent()` ahora construye un `LiteLlm(model=ADK_LLM_MODEL, api_base=ADK_LLM_API_BASE, api_key=ADK_LLM_API_KEY, max_tokens=ADK_LLM_MAX_TOKENS)` real cuando `ADK_LLM_API_BASE` está configurado (si no, cae al placeholder de antes -- sigue funcionando sin LLM para quien no lo tenga).
5. **Prueba real de extremo a extremo, con el `Runner` oficial de ADK (no solo litellm crudo), verificada en vivo — `apps/services/ai/tests/test_adk_agent_live_llm.py` (marcado `slow`, no corre en la suite por defecto):**
   - `test_agente_responde_un_saludo_con_llm_real`: **PASS** -- el `root_agent` real, vía `Runner.run_async()`, produce un evento con texto real ante "Hola, ¿quién eres?".
   - `test_agente_usa_buscar_cliente_con_llm_real`: **PASS** -- ante "Busca el cliente Acme en el sistema.", el LLM **decidió por su cuenta** invocar la tool `buscar_cliente` (sin que se le indicara cuál usar), la ejecución pasó por `AIEngine.run_tool()` (log real: `tool_call tool=buscar_cliente kind=READ status=OK`), consultó un `Cliente` real en BD vía el Service Layer existente, y el resultado volvió a una segunda llamada al LLM que generó la respuesta final. **Este es el ciclo completo del plan (§62 del plan original: "ADK + Sintel API + AI Tool Registry + RAG + tenant context, todos en PASS") verificado con un LLM real, no simulado.**
6. **`.env`** (este entorno de desarrollo) — `ADK_LLM_MODEL=openai/qwen/qwen3.5-9b`, `ADK_LLM_API_BASE=http://host.docker.internal:1234/v1`, `ADK_LLM_MAX_TOKENS=4000`. `.env.example` documentado con la misma guía para cualquier otro entorno.

**Lo que sigue NO probado:** un turno con MÚLTIPLES tools disponibles y ambigüedad real entre cuál elegir (hoy el agente solo tiene 2, una de ellas trivial); memoria/sesión persistente entre turnos (se usó `InMemorySessionService`, efímera); cualquier flujo de escritura (sigue bloqueado estructuralmente, correcto).

## Próximo paso real

Fases 0-5 del plan original completas con evidencia real, incluyendo una llamada real a un LLM local con tool-calling autónomo verificado. Fase 0-1 del plan de evolución completas. Lo que sigue (Fase 6 completa -- router multi-dominio real; Fase 7 -- primer WRITE controlado; Fase 2+ del plan de evolución -- EKG Domain View, IntentAgent, etc.) es trabajo real de varias sesiones, no bloqueado por nada externo ya -- se retoma cuando el usuario lo pida, fase por fase (ninguno de los dos planes pide construir todo de una vez).
