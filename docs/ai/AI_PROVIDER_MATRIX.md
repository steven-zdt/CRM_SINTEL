# AI_PROVIDER_MATRIX — Fases 5-7, 47-49

## Contrato (`AIProvider`, `apps/services/ai/providers/base.py`)

```python
class AIProvider(ABC):
    def complete(self, system: str, user_message: str, *, max_tokens=1024) -> AIResponse: ...
```

`AIResponse` normaliza `text`, `model`, `provider`, `input_tokens`,
`output_tokens`, `raw` -- ningún código fuera de `providers/` debe
inspeccionar la forma de respuesta específica de un SDK.

## Providers

| Provider | Estado | Modelo default | Variable de API key |
|---|---|---|---|
| `AnthropicProvider` | **Implementado** | `claude-haiku-4-5-20251001` (mismo modelo que el Asistente Contable existente) | `AI_API_KEY` (nuevo, genérico) con fallback a `ANTHROPIC_API_KEY` (ya usado en producción -- no se pide reconfigurar un despliegue existente) |
| `OpenAIProvider` | **No implementado** | -- | `OPENAI_API_KEY` (Fase 6, según convención oficial) |
| `LocalProvider` (endpoint OpenAI-compatible) | **No implementado** | -- | N/A (endpoint local, sin key o key ficticia según el runtime) |

## Configuración (Fase 6) — sin hardcodear modelo/key/endpoint

```
AI_PROVIDER   (no leído activamente todavía -- diseño: "anthropic"|"openai"|"local")
AI_MODEL      (implementado -- AnthropicProvider lo lee, default claude-haiku-4-5-20251001)
AI_API_KEY    (implementado -- fallback a ANTHROPIC_API_KEY)
```

Ningún valor está hardcodeado en `apps/services/ai/` -- confirmado por
lectura de código, sin literal de modelo/key fuera de la constante
`DEFAULT_MODEL` (que es el default explícito, no un secreto).

## Por qué no se implementó `OpenAIProvider`/`LocalProvider` en esta pasada

El contrato `AIProvider` ya está diseñado para no acoplar el dominio a
ningún SDK (nada fuera de `providers/anthropic_provider.py` importa
`anthropic`) -- añadir una segunda/tercera implementación sin un
caller real que las ejercite habría sido código muerto sin valor de
prueba real. Implementarlas es mecánico una vez exista el caso de uso
(mismo patrón exacto que `AnthropicProvider`, cambiando el cliente
HTTP/SDK interno).

## Fase 47-48 — Model router (diseño, no implementado)

```
# DISEÑO:
class AIModelRouter:
    def select_provider(self, task: str, sensitivity: str) -> AIProvider:
        """
        clasificacion simple / extraccion -> LocalProvider (cuando exista)
        consulta ERP estandar             -> AnthropicProvider (modelo economico, ya el default)
        razonamiento complejo             -> proveedor/modelo superior
        Nunca enviar datos sensibles (nomina/bancos/impuestos) a un
        proveedor externo si la tarea puede resolverse localmente.
        """
```

## Fase 49 — Fallback (diseño, no implementado)

Sin segundo provider real implementado, no hay fallback que construir
todavía -- el diseño esperado es que `AIEngine` (no cada tool) decida
el fallback, para que las tools nunca conozcan qué provider las sirvió
más allá de lo que ya reporta `AIResponse.provider`. Cualquier
fallback real debe ser visible para el usuario cuando afecte el
resultado (regla explícita de la Fase 49) -- no oculto.
