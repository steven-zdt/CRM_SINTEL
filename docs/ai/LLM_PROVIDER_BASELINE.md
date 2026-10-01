# LLM_PROVIDER_BASELINE — FASE 0 (PLAN_MAESTRO_LLM_PROVIDER_HUB_SINTEL_CONSOLE_20260924.md)

**Fecha:** 2026-09-24 · **Mandato de la fase:** solo inspección, cero cambios de código.

STATUS: **PASS**

Identificación inequívoca pedida por el plan (§53):

| Clave | Valor real hoy |
|---|---|
| `CURRENT_PRIMARY_PROVIDER` (camino no-ADK, `form_assistant.py`) | `anthropic` (default de `get_ai_provider()`, sin `AI_PROVIDER` seteado en `.env`) |
| `CURRENT_PRIMARY_MODEL` (no-ADK) | `claude-haiku-4-5-20251001` |
| `CURRENT_PRIMARY_PROVIDER` (camino ADK, el widget real del navbar) | Ollama (`AI_ADK_ENABLED=true`) |
| `CURRENT_PRIMARY_MODEL` (ADK) | `qwen3.5:4b` vía `ollama_chat/qwen3.5:4b` (litellm) |
| `CURRENT_FALLBACK_PROVIDER` | **Ninguno implementado** (GAP-9 del plan anterior, sigue abierto) |
| `CURRENT_FALLBACK_MODEL` | N/A |
| `OLLAMA_ENABLED` | Sí -- servicio Docker propio (`docker-compose.yaml::ollama`), `mem_limit: 3g`/`cpus: 4`, modelo `qwen3.5:4b` instalado y validado (ver `docs/ai/OLLAMA_STATUS.md`) |
| `LM_STUDIO_ENABLED` | Config existe (`.env.example` "Opción B") pero **no activa hoy** -- ADK se repunteó a Ollama el 2026-09-24 porque LM Studio no estaba corriendo |
| `CURRENT_ADK_MODEL_PATH` | `apps/services/ai/adk/agent.py::_build_model()` lee `ADK_LLM_MODEL`/`ADK_LLM_API_BASE`/`ADK_LLM_API_KEY`/`ADK_LLM_MAX_TOKENS` de `django.conf.settings` directo, construye `google.adk.models.lite_llm.LiteLlm` a mano. **Sin resolver central** -- la lógica de selección vive inline en el agente. |
| `CURRENT_RAG_PATH` | `RetrievalTool` -> `RetrievalService` -> `get_embedding_provider()` -> `FastEmbedProvider` (`jinaai/jina-embeddings-v2-base-es`, 768d) -> `AIKnowledgeChunk` (pgvector). **Totalmente independiente** de qué LLM esté activo (dos factories separadas, confirmado por código, ver `AI_PROVIDER_MATRIX.md`). |
| `CURRENT_CONSOLE_PATH` | `apps/public/console/` -- montado en `config/urls_public.py`: `path('console/', include('apps.public.console.urls'))` (HTMX, SPA-lite) + `path('api/admin/v1/console/', include('apps.public.console.api.urls'))`. Patrón: `StaffRequiredMixin`, permisos DRF `IsAdminUser` en las vistas API, navegación HTMX con `hx-get` a fragmentos HTML. **`.agent/docs/` de esta app ya tiene mapas de flujo/lógica de negocio** (`console_flow_map.md`, `console_business_logic.md`, `console_microtasks_architecture.md`) -- leídos, resumidos abajo. |
| `CURRENT_SECRET_STORAGE` | **Env vars en texto plano** (`.env`) para TODO secreto hoy: `ANTHROPIC_API_KEY`, `ADK_LLM_API_KEY`, `TUNNEL_TOKEN`, `N8N_ENCRYPTION_KEY`, etc. -- ninguno pasa por DB. **Hallazgo clave (reutilizable):** SÍ existe un mecanismo de cifrado simétrico real y en uso, `apps/services/security/crypto.py` (`encrypt_password`/`decrypt_password`, Fernet, clave vía `MAILCFG_FERNET_KEY`, ya usado para passwords de buzones de correo en `apps/tenant/empresa/models.py`). No hay vault/secret-manager externo ni `django-encrypted-model-fields`. |
| `CURRENT_TENANT_SCOPE` | **SYSTEM-wide, no tenant-scoped.** El provider/modelo activo es el mismo para TODOS los tenants (settings de Django, un solo proceso `web` para todo el deployment) -- no existe ningún mecanismo de override por tenant hoy. |

## Ya construido hoy (2026-09-24, mismo día, plan anterior) -- base real para esta Fase 0/1

Del `PLAN_MAESTRO_OLLAMA_QWEN35_SINTEL_AI_ENGINE_RAG_20260924.md` (ver `docs/ai/OLLAMA_STATUS.md`, `AI_PROVIDER_MATRIX.md`):

- **Contrato `AIProvider`** (`apps/services/ai/providers/base.py`) -- ya es el `Protocol`/ABC que el plan pide en su §8, aunque más delgado (`complete()` únicamente; sin `stream()`/`health()`/`list_models()`/`get_capabilities()`/`validate_connection()` -- ver gaps).
- **3 providers reales implementados**: `AnthropicProvider` (SDK), `OllamaProvider` (REST nativo), `OpenAICompatibleProvider` (REST genérico -- cubre Gemini, Groq, OpenRouter, LM Studio, etc. sin código nuevo).
- **`get_ai_provider()`** (`apps/services/ai/providers/__init__.py`) -- factory por `AI_PROVIDER`, dict explícito. Esto YA satisface gran parte de lo que el plan llama "Resolver Central" (§12) para el camino no-ADK, pero **no** para ADK (que sigue resolviendo su propio modelo inline).

## Console -- resumen real de `.agent/docs/`

- **Auditoría ya existe**: `ConsoleActionLog` (`apps/public/console/models.py`) -- `action` (choices fijos: `TENANT_CREATE/UPDATE/DELETE`, `USER_*`, `SECURITY_ALERT`), `actor` (FK a User), con más campos (timestamp, target, etc.). Reutilizable como PATRÓN, pero sus `ACTION_CHOICES` son un enum cerrado -- agregar acciones de IA (`AI_PROVIDER_ACTIVATE`, etc.) requiere migración, o un modelo de auditoría propio si se prefiere no acoplar dominios (decisión de Fase 1, no de esta fase).
- **Navegación**: HTMX SPA-lite, sidebar con `hx-get` a fragmentos -- coherente con el menú propuesto por el plan (§4, "Configuración > Inteligencia Artificial").
- **Permisos**: hoy solo `IsAdminUser` (DRF built-in, binario) en las vistas de consola -- **no existe** el sistema de permisos granulares que pide el plan (§31: `ai.providers.view/manage/test/activate/secrets.manage/audit`). Gap real, ver `LLM_PROVIDER_MIGRATION_GAPS.md`.

## Settings AI_*/ADK_LLM_*/AI_OLLAMA_*/AI_OPENAI_COMPAT_* reales (`config/settings.py`, `.env`)

Ya inventariados en `OLLAMA_BASELINE.md` §10 -- sin cambios desde entonces salvo la adición de `AI_OPENAI_COMPAT_BASE_URL`/`API_KEY`/`MODEL` (hoy vacíos, documentados en `.env.example`, no activos).

## Documentos ya existentes que este plan debe respetar, no duplicar

`docs/ai/AI_PROVIDER_MATRIX.md` (recién reescrito, ya cubre gran parte del §8/§9 de este plan), `docs/ai/OLLAMA_STATUS.md`, `docs/ai/OLLAMA_BASELINE.md`, `docs/ai/OLLAMA_MIGRATION_GAPS.md`, `docs/ai/OLLAMA_DEPENDENCY_MAP.md`, `docs/ai/AI_SECURITY_MODEL.md`, `docs/ai/AI_MCP_POLICY.md`, `docs/adk/ADK_STATUS.md` (+ resto de `docs/adk/`), `apps/public/console/.agent/docs/*.md`.
