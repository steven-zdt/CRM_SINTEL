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

**[2026-09-01, misión de evolución READ_ONLY → contextual, Fases AI-01
a AI-03]** Actualizado tras cerrar AI-01 (context engine, formalmente
verificado) y avanzar AI-02 (EKG contextual, `ai_project_map` real) +
AI-03 parcial (2 dominios READ: `clientes`, `inventario`). Ver
`AI_RELEASE_GATE.md` para el detalle ítem por ítem actualizado.

**Implementado y probado (código real, tests reales, ver
`AI_RELEASE_GATE.md`):**
`AIProvider`/`AnthropicProvider`, `AIContext`/`build_context`
(AI-01 **VERIFIED**), `BaseTool`/`AIToolRegistry`, `AIEngine.run_tool`,
feature flags server-side, **3 tools READ reales**: `buscar_cliente`,
`buscar_producto`, y `ai_project_map` (EKG contextual, AI-02).

**Diseñado, no implementado:** el resto de tools por dominio (11 de
13 dominios prioritarios de AI-03 siguen pendientes), MCP write,
guardrails de input/output, memoria de sesión, tracing productivo,
cost control, model router, VALIDATE/SUGGEST engines (AI-04/AI-05).
Cada documento de `docs/ai/` dice explícitamente cuál es cuál.

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
    clientes_tools.py          # BuscarClienteTool
    inventario_tools.py         # BuscarProductoTool (incluye stock_actual)
    ekg_tools.py                 # ProjectMapTool (ai_project_map) -- AI-02
  engine/
    ai_engine.py               # AIEngine.run_tool() -- unico punto de entrada
  tests/
    test_tool_registry.py
    test_ai_context.py             # incluye AI-01.3: contexto A != contexto B
    test_buscar_cliente_tool.py     # confirma empresa_id real del contexto, flags, permisos
    test_buscar_producto_tool.py     # mismo patron, dominio inventario
    test_ai_project_map_tool.py       # owner (Django) + rules/fk (snapshot EKG real)
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

## EKG / Knowledge Graph tool (Fase 9-10, AI-02) — **implementado**

`ai_project_map` (`apps/services/ai/tools/ekg_tools.py`, clase
`ProjectMapTool`) combina dos fuentes reales, cada una la más
autoritativa para su pregunta:

```python
def run(self, context, *, question: str, name: str) -> ToolResult:
    # question="owner" -> django.apps.apps.get_models() (registro VIVO,
    #   nunca un snapshot -- responde "que app_label posee este modelo"
    #   con autoridad total, sin depender de que el EKG este actualizado)
    # question in ("rules_for_app","docs_for_app","fk_relationships",
    #   "endpoints_for_model") -> carga tools/ekg/out/<carpeta>.json
    #   (snapshot real generado por `make ekg-build`) + funciones
    #   offline_* de tools/ekg/queries.py -- SIEMPRE reporta
    #   snapshot_generated_at, nunca oculta que es una fotografia
```

**No usa Neo4j directamente** -- usa los snapshots JSON ya
serializados (`tools/ekg/schema.py::graph_from_jsonable`), que ya
contienen exactamente lo que las funciones `offline_*` necesitan; no
hace falta una conexión Neo4j viva para responder estas preguntas.
**No devuelve el grafo completo** -- cada pregunta carga solo el
snapshot de la app relevante (no las 27 apps a la vez), y las
funciones `offline_*` ya filtran a las relaciones del modelo/app
consultado (Fase 10, cumplido).

**DOCUMENTATION_DRIFT real encontrado al construirla** (ver
`AI_BASELINE_EXECUTION.md` para el detalle completo): el `app_label`
real de Django no siempre coincide con el nombre de archivo del
snapshot EKG (ej. `Cliente` → `app_label="tenant_clientes"`, snapshot
`clientes.json`, nombrado por carpeta). La tool deriva el nombre de
carpeta real desde `model.__module__` en vez de asumir que coincide
con `app_label` — corregido en el código nuevo; no se corrigió
`documentacion/arquitectura_general.md` §2.2 (fuera del alcance mínimo
de esta tool).

**No implementado (AI-02.4, process resolution):** "¿qué ocurre al
facturar una venta?" (cadena `Venta → Factura → Inventario →
Contabilidad → Bancos → Impuestos`) requeriría resolver dependencias
cross-app en cadena que el grafo actual no modela de forma
directamente consultable con las funciones `offline_*` existentes —
trabajo genuino adicional, no incluido en esta pasada.
