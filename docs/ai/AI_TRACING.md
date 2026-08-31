# AI_TRACING — Fases 28-30, 58, 64

## Implementado hoy: logging estructurado básico (no tracing completo)

`AIEngine.run_tool()` emite un log real por cada tool call, vía el
logger `ai_engine` (Python `logging`, integrado con el `LOGGING`
config ya existente en `config/settings.py`):

```python
logger.info(
    "ai_engine.tool_call tool=%s kind=%s status=%s user=%s empresa=%s",
    tool_name, tool.kind.value, result.status, context.user_id, context.empresa_id,
)
```

Y en caso de error interno:

```python
logger.exception("ai_engine.tool_error tool=%s user=%s empresa=%s", ...)
```

**Nunca se registra:** el payload completo del tool call (podría
contener texto libre del usuario), ni `ANTHROPIC_API_KEY`/`AI_API_KEY`
-- verificado por lectura de código, ningún `logger.*()` de
`apps/services/ai/` interpola un secreto. Cumple Fase 58 con lo que
existe hoy (tool, resultado, error) -- no cumple la Fase 28/29
completa (ver abajo).

## No implementado: tracing de workflow real (Fase 28-29)

Lo que falta para un tracing real tipo "reconstruir cada ejecución"
(Fase 28: request completo, contexto, cada tool call, resultados,
decisiones, aprobación, resultado final):

- No hay un `trace_id`/`turn_id` que agrupe múltiples tool calls de
  una misma interacción del usuario -- cada llamada a `run_tool()` se
  loggea de forma independiente hoy.
- No hay persistencia estructurada de trazas (solo logs de texto, no
  un modelo/tabla de auditoría de IA consultable).
- No hay integración con ningún sistema de tracing externo (el
  proyecto no usa OpenTelemetry ni similar hoy).

Diseño de referencia (Agents SDK de OpenAI, citado en la misión como
referencia arquitectónica, no como dependencia a instalar): un
`trace_id` por interacción de usuario, spans por tool call con
duración/errores/uso de tokens, sin necesidad de adoptar ningún SDK
externo -- se puede construir sobre el logging ya existente, agregando
un campo `trace_id` generado por `AIEngine` al inicio de una
interacción (no implementado).

## Fase 30 — Cost control (no implementado)

`AIResponse` (implementado) ya expone `input_tokens`/`output_tokens`
por cada llamada real al `AIProvider` -- el dato base existe. Falta
(no implementado): agregación por usuario/tenant/período, y límites
configurables. `buscar_cliente` no llama a ningún `AIProvider` (es
una búsqueda estructurada, no generación de texto), así que no hay
costo real que medir todavía en el único flujo end-to-end existente.

## Fase 64 — Observabilidad (no implementado)

Métricas listadas por la misión (tool success/failure, latencia,
tokens, costo, refusal, permission denial, hallucination reports, tasa
de confirmación) -- ninguna tiene un dashboard/agregación hoy. El
`status` de cada `ToolResult` ya distingue `OK` de `PERMISSION_DENIED`
de `NOT_FOUND` etc. (base para calcular esas métricas más adelante),
pero no hay agregación ni exposición de las mismas todavía.
