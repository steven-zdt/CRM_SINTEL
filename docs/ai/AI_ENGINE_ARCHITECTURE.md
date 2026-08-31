# AI_ENGINE_ARCHITECTURE — Fases 4, 5, 8, 9, 10

## Alcance real de esta pasada (léase antes que nada)

Esta misión pide 66 fases hasta `AI_ENGINE = VERIFIED`, incluyendo
implementar escritura, MCP write, guardrails completos, routing de
modelos, memoria de sesión y tracing productivo. **Implementar las 66
fases con calidad real en una sola pasada no es honesto** — sería
fabricar alcance. Se aplicó el mismo criterio que en las misiones de
producción/migración previas de esta sesión: ejecutar con evidencia
real lo que la propia misión pide primero ("AUDITAR → MAPEAR →
DISEÑAR", "NO habilitar WRITE", "Primero READ_ONLY_ASSISTANT") y
diseñar explícitamente, sin fingir implementación, el resto.

**Implementado y probado (código real, tests reales, ver
`AI_RELEASE_GATE.md`):**
`AIProvider`/`AnthropicProvider`, `AIContext`/`build_context`,
`BaseTool`/`AIToolRegistry`, `AIEngine.run_tool`, feature flags
server-side, **una** tool READ real (`buscar_cliente`).

**Diseñado, no implementado:** todo lo demás (resto de tools por
dominio, MCP write, guardrails de input/output, memoria de sesión,
tracing productivo, cost control, model router, integración EKG como
retrieval). Cada documento de `docs/ai/` dice explícitamente cuál es
cuál.

## Estructura real

```
apps/services/ai/            # capa de servicio, NO una app de negocio
  providers/
    base.py                  # AIProvider (contrato), AIResponse
    anthropic_provider.py    # AnthropicProvider -- reutiliza el mismo
                              # SDK/patron que el Asistente Contable
  context/
    ai_context.py            # AIContext (frozen), build_context(request)
  tools/
    base.py                  # BaseTool, ToolKind, ToolRisk, ToolResult
    registry.py               # AIToolRegistry (register_tool/get_tool/list_tools)
    clientes_tools.py          # BuscarClienteTool -- la unica tool real hoy
  engine/
    ai_engine.py               # AIEngine.run_tool() -- unico punto de entrada
  tests/
    test_tool_registry.py
    test_ai_context.py
    test_buscar_cliente_tool.py  # confirma empresa_id real del contexto, flags, permisos
```

`policies/`, `memory/`, `tracing/` **no se crearon** -- crear paquetes
vacíos sin lógica real habría sido peor que no crearlos (dead code).
Ver `AI_MEMORY_POLICY.md`/`AI_TRACING.md` para el diseño de cada uno,
pendiente de implementación real.

## Flujo real (el único que existe hoy)

```
Caller (vista/backend, AUN NO vía MCP)
  -> AIEngine.run_tool(tool_name, request, **kwargs)
       -> feature flags (AI_ENABLED + AI_<KIND>_ENABLED)  -- settings, nunca request
       -> AIToolRegistry.get_tool(tool_name)
       -> WRITE bloqueado estructuralmente (AUTO_APPROVED_KINDS)
       -> build_context(request)  -- SSoT: request.user.tenant_profile
       -> tool.run(context, **kwargs)
            -> Selector/Service YA EXISTENTE del dominio (ej. ClienteSelector)
       -> ToolResult normalizado (status: OK|VALIDATION_ERROR|PERMISSION_DENIED|NOT_FOUND|INTERNAL_ERROR)
```

Ningún paso de esta cadena toca ORM/SQL fuera de un Selector/Service
ya propietario del dominio (Regla Absoluta 1). El `AIProvider`
(Anthropic) **no se invoca todavía en este flujo** -- la tool
`buscar_cliente` es una función determinista (búsqueda estructurada),
no requiere LLM. El `AIProvider` queda listo para cuando un flujo real
necesite generar texto/decidir con un modelo (ej. explicar un
resultado, decidir qué tool usar a partir de lenguaje natural) -- eso
es diseño de Fase 17+ (Form Assistant), no implementado aún.

## Provider abstraction (Fase 5)

```python
class AIProvider(ABC):
    def complete(self, system: str, user_message: str, *, max_tokens=1024) -> AIResponse: ...
```

`AnthropicProvider` es la única implementación real. `OpenAIProvider`/
`LocalProvider` **no existen** -- el contrato ya está diseñado para no
acoplar el dominio a ningún SDK concreto (ningún módulo fuera de
`providers/` importa `anthropic` directamente), pero implementarlos
sin un caso de uso real que los ejercite habría sido código muerto.
Ver `AI_PROVIDER_MATRIX.md`.

## Context Engine (Fase 8)

`AIContext` es un dataclass **inmutable** construido exclusivamente
desde `request.user.tenant_profile` (el mismo SSoT que ya usa
`SintelDSVMixin.get_empresa_id()` en el resto del código, reutilizado,
no reinventado) -- nunca desde el payload del request de IA, nunca
inferido de lenguaje natural (Regla Absoluta 24). Si el usuario no
tiene `TenantProfile` válido, `build_context()` lanza
`PermissionDeniedError` -- no hay fallback silencioso a "sin
restricción".

## EKG / Knowledge Graph tool (Fase 9-10)

**No implementado.** `tools/ekg/` (ver `AI_CURRENT_STATE.md`) es un
candidato real (ya tiene el grafo de dependencias que
`ai.project_map` necesitaría), pero conectar el AI Engine al EKG real
(vía Neo4j) es trabajo genuino de diseño+implementación que excede el
alcance de esta pasada. Diseño de la interfaz esperada:

```python
# DISEÑO, no implementado:
def ai_project_map(question: str) -> dict:
    """
    Responde 'que app posee X', 'que depende de Y', 'que servicio uso',
    consultando tools/ekg/queries.py contra el grafo Neo4j ya existente
    -- NUNCA devuelve el grafo completo al modelo, filtra a lo
    relevante para la pregunta (Fase 10, regla explicita).
    """
```
