# AI_BASELINE_EXECUTION — Fase 0 (misión evolución READ_ONLY → contextual)

Auditoría real de `apps/services/ai/` ejecutada 2026-09-01, antes de
tocar diseño (regla explícita de la Fase 0). Punto de partida:
`docs/ai/AI_CURRENT_STATE.md` (auditoría original, misión anterior) +
`docs/ai/AI_RELEASE_GATE.md` (estado declarado al cierre de esa misión).

## Qué existe (confirmado por lectura directa, no por memoria)

```
apps/services/ai/
  providers/base.py              AIProvider (ABC), AIResponse
  providers/anthropic_provider.py AnthropicProvider -- unico provider real
  context/ai_context.py          AIContext (frozen), build_context(request)
  tools/base.py                  BaseTool, ToolKind, ToolRisk, ToolResult, AUTO_APPROVED_KINDS
  tools/registry.py               AIToolRegistry (register_tool/get_tool/list_tools/tool_metadata)
  tools/clientes_tools.py          BuscarClienteTool -- unica tool de dominio antes de esta mision
  engine/ai_engine.py              AIEngine.run_tool() -- unico punto de entrada
  tests/                           20 tests, 20/20 PASS (confirmado al cierre de la mision anterior)
```

## Qué funciona (verificado, no asumido)

- `AIContext`/`build_context`: SSoT real vía `request.user.tenant_profile`
  -- nunca infiere de lenguaje natural (cumple Regla 3 de esta misión
  ya desde antes de empezarla).
- `AIEngine.run_tool()`: WRITE bloqueado **estructuralmente**
  (`AUTO_APPROVED_KINDS` excluye `ToolKind.WRITE` sin importar el
  flag) -- cumple Regla 5/6 ya desde el diseño existente.
- `buscar_cliente`: único tool READ real, envuelve `ClienteSelector`
  ya existente (Regla 1: nunca ORM directo desde la tool).
- Feature flags server-side (`AI_ENABLED`/`AI_READ_ENABLED`/etc.,
  `config/settings.py`, default `False`, nunca leídos de
  `request.data`) -- cumple Fase AI-31 ya desde antes.

## Qué NO funciona / no existe todavía (confirmado, no asumido)

- Sin `AIContextEngine` como clase separada -- `build_context()` ya
  cumple la función, pero no hay un objeto "engine" dedicado con
  métodos adicionales (resolver ruta/entidad actual más allá de los 4
  campos `screen_*` ya presentes en `AIContext`).
- Sin integración EKG -- `docs/ai/AI_ENGINE_ARCHITECTURE.md` ya lo
  documentaba como diseño pendiente.
- Sin más tools de dominio -- solo `clientes`.
- Sin VALIDATE/SUGGEST/MCP/memoria/tracing productivo implementados
  -- todos diseñados en `docs/ai/`, ninguno con código.

## Dependencias reales para esta misión

- `tools/ekg/` -- confirmado real y reutilizable para AI-02: funciones
  `offline_*` en `tools/ekg/queries.py` operan sobre un `Graph` en
  memoria (`tools/ekg/schema.py`), con snapshots ya serializados en
  `tools/ekg/out/<app>.json` (27 archivos, generados por
  `make ekg-build`, **no en vivo** -- son point-in-time). No existe un
  grafo combinado de todo el proyecto, solo snapshots por app.
- `django.apps.apps.get_models()` -- registro vivo de Django, siempre
  actual, no requiere el EKG para resolver "qué app es dueña de este
  modelo" (más autoritativo que un snapshot para esa pregunta
  específica).

## DOCUMENTATION_DRIFT real encontrado durante esta fase

`documentacion/arquitectura_general.md` §2.2 documenta la columna "App
Label" sin el prefijo `tenant_` para varias apps (ej. `clientes` ->
documentado como `clientes`, real: `tenant_clientes`, confirmado en
`apps/tenant/clientes/apps.py:7`). El nombre de snapshot del EKG usa
el nombre de **carpeta** (`clientes.json`), no el `app_label` de
Django -- dos convenciones de nombrado distintas y ninguna coincide
con lo documentado. No se corrige `arquitectura_general.md` en esta
pasada (fuera del alcance mínimo de la misión AI Engine) -- documentado
aquí como drift real, con evidencia, tal como exige la sección
"Fuentes de Verdad" de esta misión. `apps/services/ai/tools/ekg_tools.py`
deriva el nombre de carpeta real desde `model.__module__` en vez de
asumir que coincide con `app_label` -- corregido en el código nuevo,
no en la documentación preexistente.

## Decisión de alcance para esta pasada

No se reimplementa nada de lo ya correcto (regla explícita). Se
construye:
1. AI-01: cerrar formalmente el context engine ya existente con la
   prueba explícita que la misión pide (contexto A ≠ contexto B).
2. AI-02: `ai.project_map` real, combinando registro vivo de Django
   (owner) + snapshots reales del EKG (reglas/docs/FK) -- sin crear un
   segundo grafo.
3. AI-03: expandir READ tools a 1-2 dominios adicionales de bajo
   riesgo, mismo patrón que `buscar_cliente`.

El resto de fases (AI-04 en adelante) quedan explícitamente fuera de
esta pasada -- ver `docs/ai/AI_RELEASE_GATE.md` (actualizado al cierre)
para el estado real ítem por ítem.
