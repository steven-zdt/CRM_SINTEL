# LLM_PROVIDER_DEPENDENCY_MAP — FASE 0 (PLAN_MAESTRO_LLM_PROVIDER_HUB_SINTEL_CONSOLE_20260924.md)

**Fecha:** 2026-09-24 · **Base:** `LLM_PROVIDER_BASELINE.md`

STATUS: **PASS**

## Dos caminos de resolución de LLM que hoy NO comparten un resolver central

```text
Camino A -- form_assistant.py (widget/endpoint no-ADK):
  apps/services/ai/orchestrator/form_assistant.py::ask()
    -> get_ai_provider()  [apps/services/ai/providers/__init__.py]
         -> lee AI_PROVIDER (env, via os.environ.get) -- dict explicito
         -> instancia AnthropicProvider | OllamaProvider | OpenAICompatibleProvider

Camino B -- ADK (el widget real del navbar, AI_ADK_ENABLED=true):
  apps/services/ai/orchestrator/adk_router.py::ask()
    -> apps/services/ai/adk/agent.py::build_root_agent()
         -> _build_model() lee ADK_LLM_MODEL/ADK_LLM_API_BASE/ADK_LLM_API_KEY/
            ADK_LLM_MAX_TOKENS de settings.py DIRECTO (no via get_ai_provider())
         -> construye google.adk.models.lite_llm.LiteLlm a mano
```

**Esto es exactamente el gap que el plan pide cerrar en su Fase 5** ("Resolver + ADK" -- "Prohibido: agent.py → Ollama hardcoded"). Hoy no está hardcoded a UN provider, pero SÍ está resuelto de forma independiente/paralela al Camino A -- dos lugares que leen configuración de forma distinta, sin un `resolve_active_llm()` único.

## Grafo completo (ambos caminos convergen en el mismo AIEngine/Service Layer)

```text
HTTP: POST /api/v1/ai/ask/
  apps/services/ai/api/viewsets.py::AIAssistantViewSet.ask()
    -> apps/services/ai/orchestrator/__init__.py::ask()  [Router]
         |-- AI_ADK_ENABLED=False -> Camino A (arriba)
         `-- AI_ADK_ENABLED=True  -> Camino B (arriba)

AIEngine.run_tool()  (apps/services/ai/engine/ai_engine.py -- PUNTO UNICO, ambos caminos convergen aqui)
  |-- flag AI_ENABLED
  |-- AIToolRegistry.get_tool(name)  [apps/services/ai/tools/registry.py]
  |-- flag por kind (AI_READ_ENABLED/AI_SUGGEST_ENABLED/AI_VALIDATE_ENABLED/AI_WRITE_ENABLED)
  |-- AUTO_APPROVED_KINDS  (bloqueo ESTRUCTURAL de WRITE)
  `-- tool.run(context, **kwargs) -> Service Layer real (ORM, tenant ya resuelto)

RAG (independiente de AMBOS caminos de LLM):
  RetrievalTool -> RetrievalService -> get_embedding_provider() -> FastEmbedProvider -> pgvector
  (factory SEPARADA de get_ai_provider() -- nunca se toca por este plan)
```

## Console -- dependencias reales si se agrega la UI de administración

```text
apps/public/console/urls.py            -- registrar nueva ruta (ej. console/ai-providers/)
apps/public/console/api/urls.py        -- nuevos endpoints API (CRUD providers/models/activo/salud/auditoria)
apps/public/console/api/views.py       -- patron IsAdminUser (DRF) ya establecido, reutilizable
apps/public/console/models.py          -- ConsoleActionLog (auditoria, ACTION_CHOICES cerrado -- ver gap)
apps/public/console/templates/console/ -- sidebar HTMX, agregar item "Inteligencia Artificial"
apps/public/console/static/js/         -- JS de la consola (patron existente a descubrir antes de escribir)
apps/services/security/crypto.py       -- encrypt_password/decrypt_password (Fernet) -- candidato real
                                            para el secret_ref del plan (§7), YA EXISTE, no se crea de cero
```

## Quién NO debe verse afectado (regla del plan, ya verificada hoy contra código real)

```text
AIEngine            -- NO depende de que provider LLM este activo (ya verificado, ver OLLAMA_DEPENDENCY_MAP.md)
AIContext            -- idem
AIToolRegistry       -- idem
RAG/RetrievalService -- idem, ademas independiente del provider de EMBEDDINGS (factory separada)
Service Layer/ORM    -- nunca alcanzado directo por un LLM, siempre AIEngine.run_tool() -> tool.run()
AUTO_APPROVED_KINDS  -- bloqueo de WRITE, no depende de que provider responda
```

## Radio de cambio si se implementa el Hub completo (Fases 1-13 del plan)

```text
Nuevo (no existe hoy):
  Modelo de datos: LLMProvider, LLMModel, LLMConnection, LLMActiveConfig (Fase 1)
  apps/services/ai/providers/base.py -- extender AIResponse/AIProvider con
    stream()/health()/list_models()/get_capabilities()/validate_connection()
    (hoy solo complete() -- GAP real, ver LLM_PROVIDER_MIGRATION_GAPS.md)
  Resolver central resolve_active_llm(tenant_context, agent_context, workload)
    que UNIFIQUE los Caminos A y B de arriba (Fase 5)
  UI completa en apps/public/console/ (Fase 8)
  Secret storage con secret_ref (probablemente sobre crypto.py existente)

Modificado (con cuidado, cambio minimo):
  apps/services/ai/adk/agent.py::_build_model() -- para consumir el resolver
    central en vez de leer settings.ADK_LLM_* directo (Fase 5)
  form_assistant.py -- para consumir el mismo resolver (ya usa get_ai_provider(),
    cambio menor si el resolver envuelve esa misma factory)

NO tocado (regla absoluta del plan, ver seccion 50):
  AIContext, EKG, ai_project_map, AIKnowledgeDocument/Chunk, FastEmbed,
  jina embeddings, pgvector, RetrievalService, RetrievalTool, AIToolRegistry,
  Service Layer, embeddings model (nunca cambia por cambiar LLM)
```
