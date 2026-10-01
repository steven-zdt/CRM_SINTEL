# OLLAMA_BASELINE — FASE 0 (PLAN_MAESTRO_OLLAMA_QWEN35_SINTEL_AI_ENGINE_RAG_20260924.md)

**Fecha:** 2026-09-24
**Fuente:** `documentacion/PLAN_MAESTRO_OLLAMA_QWEN35_SINTEL_AI_ENGINE_RAG_20260924.md`
**Mandato de la fase:** solo inspección, cero cambios de código.

STATUS: **PASS**

## 1. Contrato `AIProvider` (LLM / completion)

`apps/services/ai/providers/base.py` — ya existe y es exactamente el
contrato que el plan pide en su §5 (normalizar `content`/`text`,
`model`, `provider`, `usage`, `raw`):

```python
class AIProvider(ABC):
    name: str
    def complete(self, system: str, user_message: str, *, max_tokens=1024) -> AIResponse: ...

@dataclass
class AIResponse:
    text: str; model: str; provider: str
    input_tokens: int = 0; output_tokens: int = 0; raw: dict = field(default_factory=dict)
```

No expone tool-calling nativo del SDK -- `AIEngine`/orquestador decide
qué tool ejecutar a partir del texto del modelo. `tool_calls`/
`finish_reason` (que el plan pide normalizar en §5) **no están en
`AIResponse` hoy** -- gap real, ver `OLLAMA_MIGRATION_GAPS.md`.

Única implementación real: `AnthropicProvider`
(`apps/services/ai/providers/anthropic_provider.py`) -- lee
`AI_API_KEY`/`ANTHROPIC_API_KEY` y `AI_MODEL` (default
`claude-haiku-4-5-20251001`), llama al SDK `anthropic` directo. Ya
documentado en `docs/ai/AI_PROVIDER_MATRIX.md`, que registra
`AI_PROVIDER` como variable **diseñada pero no leída activamente
todavía** (Fase 47-48 de ese doc) -- coincide textualmente con lo que
pide el plan de Ollama.

## 2. Contrato `AIEmbeddingProvider` (embeddings) -- separado a propósito

`apps/services/ai/providers/embedding_base.py` + `fastembed_provider.py`.
Deliberadamente distinto de `AIProvider` (texto vs. embeddings son
operaciones distintas). Única implementación: `FastEmbedProvider`
(`jinaai/jina-embeddings-v2-base-es`, 768d, ONNX local, sin API key,
sin egress).

**Hallazgo clave:** `apps/services/ai/providers/__init__.py` YA TIENE
una factory real para embeddings:

```python
def get_embedding_provider(name: str | None = None) -> AIEmbeddingProvider:
    key = (name or os.environ.get("AI_EMBEDDING_PROVIDER", "fastembed")).lower()
    return _EMBEDDING_PROVIDERS[key]()
```

Este es exactamente el patrón (`dict` explícito + `os.environ.get`,
sin registro dinámico) que el plan pide en su §5 para
`get_ai_provider()` -- replicar la forma, no inventar una nueva.

## 3. `AIEngine` -- fachada única de ejecución de tools

`apps/services/ai/engine/ai_engine.py::AIEngine.run_tool()`. Punto
ÚNICO por el que se ejecuta cualquier tool. Aplica, en este orden:
`AI_ENABLED` → `get_tool(name)` → flag por `kind`
(`AI_READ_ENABLED`/`AI_SUGGEST_ENABLED`/`AI_VALIDATE_ENABLED`/
`AI_WRITE_ENABLED`) → `AUTO_APPROVED_KINDS` (bloqueo ESTRUCTURAL de
WRITE, no solo el flag) → `build_context(request)` o `context` ya
construido → `tool.run(context, **kwargs)`. Nunca propaga traceback al
modelo (`except Exception` genérico → `INTERNAL_ERROR`).

## 4. `AIToolRegistry`

`apps/services/ai/tools/registry.py`. Registro explícito a mano
(`register_tool()`), nunca introspección automática de ViewSets/ORM.
`tool_metadata()` expone `name/description/domain/kind/risk/
confirmation_required/idempotent` -- lo único que un provider/LLM ve.

## 5. ADK -- estado real (más reciente que `docs/adk/ADK_STATUS.md`, fechado 2026-09-22)

`apps/services/ai/adk/`:
- `agent.py::build_root_agent()` -- `Agent` con 2 tools (`saludar`,
  `buscar_cliente`). `_build_model()` construye un
  `google.adk.models.lite_llm.LiteLlm` **hardcodeado** apuntando a
  `ADK_LLM_API_BASE` (hoy LM Studio) cuando esa variable está
  configurada, o un placeholder string si no.
- `tools.py` -- las tools son `async def`, llaman a
  `AIEngine.run_tool()` vía `sync_to_async(..., thread_sensitive=True)`
  dentro de `schema_context(schema_name)` (mismo schema que
  `context.py::build_context_from_session()`, que re-deriva
  `AIContext` desde `session.state["sintel_schema_name"/"sintel_user_id"]`
  -- nunca confía en lo que el LLM "decide" pasar).

**Cambio real de HOY (2026-09-24, esta misma sesión, posterior a
`ADK_STATUS.md`):** existe ahora un Router real
(`apps/services/ai/orchestrator/__init__.py::ask()`) que despacha
`POST /api/v1/ai/ask/` a `adk_router.py::ask()` (ADK/LM Studio) cuando
`AI_ADK_ENABLED=true`, o a `form_assistant.py::ask()` (Anthropic) si no.
Antes de hoy, ADK **no tenía ningún endpoint HTTP real que lo
consumiera** (`ADK_STATUS.md` Fase 6: "PARCIAL... sin router
multi-dominio"). Sigue siendo solo 2 tools, sin router multi-dominio
real -- pero el primer dispatch real ya existe. `docs/adk/ADK_STATUS.md`
queda desactualizado en este punto -- actualizarlo no es parte del
mandato de esta fase (solo inspección), se deja registrado aquí.

## 6. LM Studio -- config real

`.env` de este entorno: `AI_ADK_ENABLED=true`,
`ADK_LLM_MODEL=openai/qwen/qwen3.5-9b`,
`ADK_LLM_API_BASE=http://host.docker.internal:1234/v1`,
`ADK_LLM_API_KEY=not-needed`, `ADK_LLM_MAX_TOKENS=4000`. LM Studio
corre en el **host** (fuera de Docker) -- alcanzado vía
`host.docker.internal`, que requiere el `extra_hosts:
["host.docker.internal:host-gateway"]` ya agregado al servicio `web`
en `docker-compose.yaml` (el `dns:` custom del proyecto para
`*.sintel.net.co` reemplaza el resolver embebido de Docker que
normalmente provee ese hostname solo). **Verificado en esta sesión:**
LM Studio NO estaba corriendo al momento de esta inspección
(`curl http://localhost:1234/v1/models` desde el host: connection
refused) -- el flag/wiring están listos, pero no hay LLM real
respondiendo ahora mismo.

Hallazgo real de comportamiento (`docs/adk/ADK_STATUS.md` Fase 5):
Qwen3.5 es un modelo de razonamiento -- gasta tokens en
`reasoning_content` antes de `content`; `max_tokens` bajo (256/512)
produce respuestas vacías. `ADK_LLM_MAX_TOKENS=4000` existe por esto.
Latencia real observada en ese hardware: ~90-95s por turno.

## 7. RAG / pgvector

`apps/services/ai/tools/retrieval_tools.py::RetrievalTool`
(`buscar_conocimiento`, kind=READ) → `apps/tenant/ai_knowledge/
services/retrieval_service.py::RetrievalService.search_for_context()`
→ `get_embedding_provider()` (FastEmbed) → `AIKnowledgeChunk.objects`
(`pgvector.django.VectorField`, 768d fijo por migración
`0002_pin_embedding_dimension_768`) contra el mismo Postgres del ERP
(`docker-compose.yaml`: `db` = `pgvector/pgvector:pg16`, pinneado por
digest). Doble gate por tenant: flag global `AI_RETRIEVAL_ENABLED` +
`AIKnowledgeSettings.retrieval_enabled` por `empresa_id` (rollout
gradual AI-VECTOR-11). Cache de query-embeddings en Redis
(`query_embedding_cache.py`, TTL `AI_EMBED_CACHE_TTL_S`).

Qwen nunca toca pgvector directo -- pasa siempre por
`RetrievalTool.run()` → `RetrievalService`, igual que cualquier otra
tool READ (mismo camino de `AIEngine.run_tool()`).

## 8. Docker actual

`docker-compose.yaml` (dev multi-contenedor, el flujo real de
`make up`): `web` (Django + AIEngine + ADK, TODO en el mismo proceso,
decisión explícita 2026-09-22 -- ver `ADK_STATUS.md` Fase 4),
`db` (Postgres 16 + pgvector), `redis`, `celery`, `celery-beat`,
`nginx`, `cloudflared`, `n8n`. **No existe servicio `ollama` ni
`ai_engine_adk` separado.** LM Studio corre fuera de Docker, en el
host. También existe `docker-compose.single.yaml` (contenedor único de
desarrollo, alternativa nueva/separada agregada esta misma sesión,
9 procesos vía supervisord) -- no incluye Ollama tampoco.

## 9. Dependencias Python ya instaladas (relevantes)

`requirements.txt`: `anthropic>=0.40.0,<1.0`, `litellm>=1.102,<2.0`
(usado solo por `google.adk.models.lite_llm.LiteLlm`, no directo),
`fastembed>=0.8,<0.9`, `requests>=2.31,<3.0` (ya disponible para un
cliente HTTP propio contra la API REST de Ollama, sin agregar
dependencia nueva), `google-adk==2.9.2`. Ningún cliente/SDK de Ollama
instalado todavía.

## 10. Settings AI_* reales (`config/settings.py`)

```
AI_ENABLED / AI_READ_ENABLED / AI_VALIDATE_ENABLED / AI_SUGGEST_ENABLED / AI_WRITE_ENABLED
AI_RETRIEVAL_ENABLED / AI_EMBED_CACHE_TTL_S
AI_ADK_ENABLED / ADK_LLM_MODEL / ADK_LLM_API_BASE / ADK_LLM_API_KEY / ADK_LLM_MAX_TOKENS
```

No existe `AI_PROVIDER` ni `AI_FALLBACK_PROVIDER` como settings reales
todavía (solo mencionados como diseño en `AI_PROVIDER_MATRIX.md`).

## Documentos ya existentes que este plan debe respetar, no duplicar

`docs/ai/AI_PROVIDER_MATRIX.md`, `AI_ENGINE_ARCHITECTURE.md`,
`AI_SECURITY_MODEL.md`, `AI_TOOL_REGISTRY.md`, `AI_RELEASE_GATE.md`,
`docs/adk/ADK_STATUS.md` (+ el resto de `docs/adk/`).
