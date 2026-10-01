# OLLAMA_DEPENDENCY_MAP — FASE 0 (PLAN_MAESTRO_OLLAMA_QWEN35_SINTEL_AI_ENGINE_RAG_20260924.md)

**Fecha:** 2026-09-24 · **Base:** `OLLAMA_BASELINE.md` / `OLLAMA_MIGRATION_GAPS.md`

STATUS: **PASS**

## Camino HTTP real hoy (`POST /api/v1/ai/ask/`)

```text
apps/services/ai/api/viewsets.py::AIAssistantViewSet.ask()
  -> apps/services/ai/orchestrator/__init__.py::ask()  [Router, agregado 2026-09-24]
       |
       |-- AI_ADK_ENABLED=False (default) --------------------------------
       |     form_assistant.py::ask()
       |       |-- apps.services.ai.context.build_context(request)
       |       |-- AnthropicProvider().complete()  <- HARDCODEADO (GAP-1/GAP-2)
       |       |     -- SDK `anthropic` -> Anthropic API (ANTHROPIC_API_KEY)
       |       `-- AIEngine.run_tool(tool_name, request, **arguments)
       |
       `-- AI_ADK_ENABLED=True -------------------------------------------
             adk_router.py::ask()  [agregado 2026-09-24]
               |-- build_context(request)  (gate temprano, no gasta LLM)
               |-- google.adk.runners.Runner + InMemorySessionService
               |     `-- apps/services/ai/adk/agent.py::build_root_agent()
               |           `-- google.adk.models.lite_llm.LiteLlm  <- HARDCODEADO a LM Studio (GAP-4)
               |                 `-- litellm -> LM Studio (host.docker.internal:1234, proceso en el HOST)
               `-- apps/services/ai/adk/tools.py::{saludar, buscar_cliente}
                     `-- sync_to_async(...) -> AIEngine.run_tool()  [mismo camino de abajo]

AIEngine.run_tool()  (apps/services/ai/engine/ai_engine.py -- PUNTO ÚNICO, ambos caminos convergen aquí)
  |-- flag AI_ENABLED
  |-- AIToolRegistry.get_tool(name)
  |-- flag por kind (AI_READ_ENABLED/AI_SUGGEST_ENABLED/AI_VALIDATE_ENABLED/AI_WRITE_ENABLED)
  |-- AUTO_APPROVED_KINDS  (bloqueo ESTRUCTURAL de WRITE, GAP-8)
  `-- tool.run(context, **kwargs) -> Service Layer real (ORM, tenant ya resuelto)
```

## RAG (independiente de cuál LLM esté activo)

```text
apps/services/ai/tools/retrieval_tools.py::RetrievalTool ("buscar_conocimiento", kind=READ)
  -> apps/tenant/ai_knowledge/services/retrieval_service.py::RetrievalService.search_for_context()
       |-- flag AI_RETRIEVAL_ENABLED + AIKnowledgeSettings.retrieval_enabled (por empresa_id)
       |-- apps/services/ai/providers/__init__.py::get_embedding_provider()  [factory YA EXISTE]
       |     `-- FastEmbedProvider (jinaai/jina-embeddings-v2-base-es, 768d, ONNX local)
       |-- cache de query-embeddings en Redis (query_embedding_cache.py)
       `-- AIKnowledgeChunk.objects (VectorField 768d) -> Postgres + pgvector
             (docker-compose.yaml: servicio `db` = pgvector/pgvector:pg16, MISMO Postgres del ERP)
```

Ni Qwen ni ningún LLM tocan pgvector directo -- siempre pasan por
`RetrievalTool.run()` (misma regla del plan §9/§21: "Qwen no ejecuta
directamente SQL ni búsquedas vectoriales").

## Docker actual (`docker-compose.yaml`, flujo real de `make up`)

```text
web        Django + AIEngine + AIToolRegistry + ADK, TODO en el mismo proceso
           (decisión explícita 2026-09-22 -- ver docs/adk/ADK_STATUS.md Fase 4)
db         Postgres 16 + pgvector (pinneado por digest)
redis      cache + broker Celery + cache de query-embeddings
celery / celery-beat
nginx      unico punto de entrada HTTP/HTTPS
cloudflared
n8n        orquestador externo, aislado (N8N-SINTEL-01), no relacionado con AI Engine

-- NO existe servicio "ollama" --
-- NO existe servicio "ai_engine_adk" separado (existió, se eliminó 2026-09-22) --
LM Studio  fuera de Docker, en el HOST -- alcanzado vía
           host.docker.internal (extra_hosts + dns custom del proyecto)
```

`docker-compose.single.yaml` (contenedor único de desarrollo, agregado
2026-09-24, alternativa nueva/separada a lo anterior) tampoco incluye
Ollama -- si Fase 1 agrega el servicio, decidir si también se replica
ahí o si queda fuera de alcance de ese modo alternativo.

## Qué NO depende de qué (garantías que Fase 1-4 no deben romper)

```text
AIToolRegistry     NO depende de qué provider LLM esté activo.
AIContext          NO depende de qué provider LLM esté activo.
RAG/pgvector        NO depende de qué provider LLM esté activo -- solo del
                    provider de EMBEDDINGS (FastEmbed), que esta migración
                    NO toca (regla absoluta del plan).
Service Layer/ORM   NUNCA es alcanzado directo por un provider LLM --
                    siempre AIEngine.run_tool() -> tool.run() -> Service Layer.
AUTO_APPROVED_KINDS NO depende de qué provider responda -- bloquea WRITE
                    sin importar si el texto/JSON del modelo "pide" escribir.
```

## Quién se ve afectado si se agrega `OllamaProvider` (radio real del cambio)

```text
Afectado directo:
  apps/services/ai/providers/__init__.py       (nueva entrada en la factory)
  apps/services/ai/providers/ollama_provider.py (nuevo archivo)
  apps/services/ai/orchestrator/form_assistant.py (deja de hardcodear AnthropicProvider())
  config/settings.py                            (AI_PROVIDER, AI_OLLAMA_*, AI_FALLBACK_PROVIDER)
  docker-compose.yaml                           (nuevo servicio `ollama` + volumen)
  .env / .env.example                           (nuevas variables documentadas)

Afectado condicional (solo si se elige la ruta (b) del GAP-4):
  apps/services/ai/adk/agent.py::_build_model()

NO afectado (el plan lo exige explícitamente, ver Reglas Absolutas §22):
  AIEngine, AIContext, AIToolRegistry, RAG/RetrievalService,
  FastEmbedProvider, cualquier tool existente, Service Layer,
  AUTO_APPROVED_KINDS, AI_WRITE_ENABLED.
```
