# AI_PROVIDER_MATRIX — Fases 5-7, 47-49, 4 del plan Ollama (2026-09-24)

## Garantía de portabilidad (pedido explícito del usuario, 2026-09-24)

**Nada en este proyecto está atado a un proveedor de LLM específico.**
`AIEngine`, `AIToolRegistry`, `apps/services/ai/tools/*.py`,
`form_assistant.py` y el agente ADK (`apps/services/ai/adk/`) hablan
únicamente contra el contrato `AIProvider` (abajo) -- ninguno de ellos
importa un SDK de proveedor ni sabe si detrás hay Anthropic, Ollama,
Gemini o cualquier otro. Cambiar de proveedor es una variable de
entorno (`AI_PROVIDER`), nunca un cambio de código en el dominio.

## Contrato (`AIProvider`, `apps/services/ai/providers/base.py`)

```python
class AIProvider(ABC):
    name: str
    def complete(self, system: str, user_message: str, *, max_tokens=1024) -> AIResponse: ...

@dataclass
class AIResponse:
    text: str; model: str; provider: str
    input_tokens: int = 0; output_tokens: int = 0; raw: dict = field(default_factory=dict)
```

## Proveedores reales hoy

| Provider | Estado | Protocolo | Modelo default | Config |
|---|---|---|---|---|
| `AnthropicProvider` | **Implementado** | SDK propio (`anthropic`) | `claude-haiku-4-5-20251001` | `AI_API_KEY`/`ANTHROPIC_API_KEY` |
| `OllamaProvider` | **Implementado** | REST, protocolo nativo Ollama (`/api/chat`) | `qwen3.5:4b` | `AI_OLLAMA_BASE_URL`/`AI_OLLAMA_MODEL` |
| `OpenAICompatibleProvider` | **Implementado** | REST, formato OpenAI Chat Completions (`/chat/completions`) -- cubre Gemini, Groq, OpenRouter, Together.ai, vLLM, LM Studio y cualquier endpoint nuevo que hable este formato **sin escribir código** | ninguno por defecto (obligatorio) | `AI_OPENAI_COMPAT_BASE_URL`/`AI_OPENAI_COMPAT_API_KEY`/`AI_OPENAI_COMPAT_MODEL` |

`get_ai_provider()` (`apps/services/ai/providers/__init__.py`) selecciona
por `AI_PROVIDER` (default `anthropic`, preserva el comportamiento actual
de cualquier entorno sin la variable seteada):

```python
_AI_PROVIDERS = {
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
    "openai_compatible": OpenAICompatibleProvider,
}
```

Mismo patrón exacto que `get_embedding_provider()` (que ya existía para
el proveedor de embeddings, `AI_EMBEDDING_PROVIDER`) -- un dict explícito,
sin registro dinámico ni plugins.

## Cómo agregar un proveedor nuevo (Gemini, Claude vía otra cuenta/API, cualquier REST)

**Caso 1 -- el proveedor habla el formato OpenAI Chat Completions**
(la gran mayoría hoy: Gemini vía su endpoint OpenAI-compat oficial, Groq,
OpenRouter, Together.ai, vLLM, llama.cpp server, LM Studio, etc.):
NO hace falta escribir código. Solo setear:
```env
AI_PROVIDER=openai_compatible
AI_OPENAI_COMPAT_BASE_URL=<endpoint del proveedor, sin /chat/completions>
AI_OPENAI_COMPAT_API_KEY=<api key del proveedor, si aplica>
AI_OPENAI_COMPAT_MODEL=<nombre del modelo>
```

**Caso 2 -- el proveedor habla un protocolo genuinamente distinto** (no
OpenAI-compat -- ej. el SDK propio de Anthropic, o el `/api/chat` nativo
de Ollama): escribir una clase nueva en
`apps/services/ai/providers/<nombre>_provider.py` que herede de
`AIProvider` e implemente `complete()` (ver `anthropic_provider.py` como
ejemplo SDK-based, `ollama_provider.py` como ejemplo REST-nativo),
registrarla en `_AI_PROVIDERS` (`apps/services/ai/providers/__init__.py`).
Ningún otro archivo del proyecto necesita cambios.

**Vía MCP:** este proyecto tiene servidor MCP propio (`/mcp/`,
`django-rest-framework-mcp`) para exponer SUS PROPIOS datos/tools a
clientes externos (ver `docs/ai/AI_MCP_POLICY.md`) -- es lo inverso de
"conectar a un LLM externo por MCP" (MCP no es un protocolo para hablar
con un LLM, es para exponerle TOOLS a un LLM/agente ya conectado por
otro medio). Si en el futuro se necesita conectar a un LLM que solo
expone MCP como transporte, ese sería un Caso 2 (provider propio).

## ADK (`apps/services/ai/adk/agent.py`) -- camino separado, mismo principio

ADK no usa `AIProvider`/`get_ai_provider()` -- usa
`google.adk.models.lite_llm.LiteLlm` (el adaptador propio de la librería
ADK), que ya es multi-proveedor por diseño de `litellm` (soporta
`ollama_chat/`, `gemini/`, `anthropic/`, `openai/`, decenas más vía
prefijo de modelo). Cambiar de proveedor ahí es `ADK_LLM_MODEL`/
`ADK_LLM_API_BASE` (2 variables de entorno), nunca tocar `agent.py`. Hoy
apunta a Ollama (`ollama_chat/qwen3.5:4b`, ver `docs/ai/OLLAMA_STATUS.md`).

## Por qué antes no había 3 proveedores reales

Antes de 2026-09-24 solo existía `AnthropicProvider` -- `OpenAIProvider`/
`LocalProvider` estaban diseñados (`AI_PROVIDER` documentado como "no
leído activamente") pero sin caller real que los ejerciera, así que
implementarlos habría sido código muerto. Con Ollama (plan
`PLAN_MAESTRO_OLLAMA_QWEN35_SINTEL_AI_ENGINE_RAG_20260924.md`) se
implementó el patrón completo (`get_ai_provider()` + 2 providers reales)
y se agregó `OpenAICompatibleProvider` como generalización inmediata --
mismo esfuerzo, cobertura de todo un ecosistema de proveedores en vez de
uno solo.

## Fase 47-48 — Model router (diseño, no implementado)

```
# DISEÑO:
class AIModelRouter:
    def select_provider(self, task: str, sensitivity: str) -> AIProvider:
        """
        clasificacion simple / extraccion -> provider local (Ollama/openai_compatible)
        consulta ERP estandar             -> AnthropicProvider (modelo economico, ya el default)
        razonamiento complejo             -> proveedor/modelo superior
        Nunca enviar datos sensibles (nomina/bancos/impuestos) a un
        proveedor externo si la tarea puede resolverse localmente.
        """
```

## Fase 49 — Fallback (diseño, no implementado)

Con 3 providers reales ya implementados, el fallback es mecánicamente
posible (`get_ai_provider("anthropic")` / `get_ai_provider("ollama")`
directo), pero el ORQUESTADOR (`AIEngine`, no cada tool) sigue siendo
quien debe decidirlo -- ninguna tool debe conocer más de lo que ya
reporta `AIResponse.provider`. Cualquier fallback real debe ser visible
para el usuario cuando afecte el resultado (regla explícita de la
Fase 49) -- no oculto. No implementado todavía (fuera del alcance
mínimo decidido para la migración de Ollama, GAP-4 en
`docs/ai/OLLAMA_MIGRATION_GAPS.md`).
