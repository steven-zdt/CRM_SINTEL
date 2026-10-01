# OLLAMA_MIGRATION_GAPS — FASE 0 (PLAN_MAESTRO_OLLAMA_QWEN35_SINTEL_AI_ENGINE_RAG_20260924.md)

**Fecha:** 2026-09-24 · **Base:** `OLLAMA_BASELINE.md` (mismo directorio)

STATUS: **PASS** (inventario de gaps; ninguno es bloqueante para arrancar Fase 1)

Cada gap referencia el § del plan maestro que lo pide.

## GAP-1 (plan §5/§6) — No existe `get_ai_provider()` para LLM/completion

Existe el equivalente para embeddings (`get_embedding_provider()`,
ver `OLLAMA_BASELINE.md` §2) pero NO para `AIProvider`
(texto/completion). `form_assistant.py::ask()` instancia
`AnthropicProvider()` directo (línea `provider = AnthropicProvider()`).
`AI_PROVIDER_MATRIX.md` ya documenta esto como diseño pendiente
(Fase 47-48) -- el gap no es "inventar el concepto", es
**implementarlo replicando el patrón de `get_embedding_provider()`**.

## GAP-2 (plan §7) — No existe `OllamaProvider`

`AI_PROVIDER_MATRIX.md` lista `LocalProvider (endpoint OpenAI-compatible)`
como "No implementado". Ningún archivo en `apps/services/ai/providers/`
habla el protocolo de Ollama (`/api/chat`, `/api/generate`,
`/api/tags`, structured outputs vía `format` JSON Schema).

## GAP-3 (plan §4) — No existe infraestructura Docker de Ollama

Sin servicio `ollama` en `docker-compose.yaml`, sin volumen
`sintel_ollama_models`, sin red/healthcheck. Tampoco en
`docker-compose.single.yaml` (contenedor único, agregado esta misma
sesión) ni en `docker-compose.prod.yaml`.

## GAP-4 (decisión de diseño real, no solo código faltante) — Dos caminos de LLM hoy, no uno

`form_assistant.py` usa `AIProvider.complete()` (contrato propio,
sin SDK expuesto). ADK usa `google.adk.models.lite_llm.LiteLlm`
directo (el adaptador de la librería ADK, que internamente habla con
`litellm`, no con `AIProvider`). Son dos abstracciones DISTINTAS que
hoy no comparten provider. El plan (§5, "no acoplar ADK... a Ollama")
asume implícitamente un solo `AIProvider Factory` -- pero ADK no
consume `AIProvider`, consume un `LiteLlm` construido a mano en
`agent.py::_build_model()`.

**Dos rutas posibles, a decidir en Fase 3, no aquí:**
- (a) `OllamaProvider` sirve solo al camino no-ADK
  (`form_assistant.py`/futuro), y ADK sigue con su propio `LiteLlm`
  apuntando a Ollama vía el prefijo nativo `ollama/` que `litellm` ya
  soporta (`ADK_LLM_API_BASE=http://ollama:11434`,
  `ADK_LLM_MODEL=ollama/qwen3.5:9b`) -- cambio de 2 variables de
  entorno, sin tocar `agent.py`.
- (b) Se unifica: `agent.py::_build_model()` también consulta
  `get_ai_provider()`/`AI_PROVIDER` para decidir el `api_base`/modelo
  que pasa a `LiteLlm`, evitando que ADK y el resto del AI Engine
  puedan quedar desincronizados sobre "cuál es el proveedor primario".

(a) es el cambio mínimo (coherente con el mandato "IMPLEMENT MINIMAL
CHANGE" del plan, §21); (b) es más correcto a largo plazo. Ninguna
decisión se toma en Fase 0.

## GAP-5 (plan §14) — No existe provider health

Ningún endpoint/función reporta hoy `reachable/latency/model/
loaded` de Anthropic o LM Studio. Construir desde cero en Fase 3/4.

## GAP-6 (plan §6) — `AI_PROVIDER`/`AI_FALLBACK_PROVIDER` no leídos

Confirmado en `AI_PROVIDER_MATRIX.md`: "no leído activamente
todavía". No hay ningún `os.environ.get("AI_PROVIDER", ...)` real en
el código hoy.

## GAP-7 (plan §15) — No hay bootstrap idempotente de modelo

No aplica todavía (no existe Ollama). Cuando se agregue el servicio
Docker (Fase 1), necesita su propio script de bootstrap
(`wait Ollama → ollama list → pull si falta → healthcheck`), sin
bloquear indefinidamente el arranque del resto del stack.

## GAP-8 (no es un gap, es una confirmación positiva) — WRITE ya bloqueado estructuralmente

`apps/services/ai/tools/base.py::AUTO_APPROVED_KINDS` ya bloquea
cualquier tool WRITE en `AIEngine.run_tool()`, sin importar el valor
de `AI_WRITE_ENABLED`, sin importar qué provider responda. La regla
absoluta del plan ("NO HABILITAR AI_WRITE_ENABLED DURANTE ESTA
MIGRACIÓN") ya tiene enforcement real en código, no depende de que
nadie recuerde no tocar ese flag.

## GAP-9 (plan §11) — `AIResponse` no normaliza `tool_calls`/`finish_reason`

`apps/services/ai/providers/base.py::AIResponse` solo tiene
`text/model/provider/input_tokens/output_tokens/raw`. El plan pide
(§5) normalizar también `tool_calls`/`finish_reason`/`usage`/
`metadata`/`errors`. Hoy `AnthropicProvider` resuelve tool-selection
por texto plano + `json.loads()` (ver `form_assistant.py`), no por
tool-calling nativo del SDK -- extender `AIResponse` es necesario si
`OllamaProvider` quiere aprovechar structured outputs/tool calling
nativo de Ollama (plan §11/§51) sin romper el contrato para
`AnthropicProvider`.

## GAP-10 (plan §9/§17) — RAG solo cubre 2/12 dominios (hallazgo heredado, no nuevo)

Ya documentado en `docs/adk/ADK_KNOWLEDGE_MAP.md` (Fase 2 del plan de
evolución ADK): RAG/pgvector solo indexa Clientes e Inventario hoy.
No es un gap que esta migración deba cerrar (el plan de Ollama no lo
pide), pero limita cuánto valor real aporta RAG en el benchmark de
Fase 8 si las preguntas de prueba caen fuera de esos 2 dominios.

## Ningún gap bloquea el arranque de Fase 1

Ninguno de los gaps anteriores impide agregar el servicio Docker de
Ollama (Fase 1) de forma aislada, sin tocar `AIEngine`/`AIContext`/
`AIToolRegistry`/RAG -- que es exactamente el orden que pide el plan.
