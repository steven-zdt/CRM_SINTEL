# AI_MCP_POLICY — Fases 2, 3, 31-33

## Estado real de MCP hoy (sin cambios en esta pasada)

`django-rest-framework-mcp` está instalado y montado (`/mcp/` en
schema público y de tenant, `config/urls_tenant.py:166`,
`config/urls_public.py:117`) con `BYPASS_VIEWSET_AUTHENTICATION=False`
y `BYPASS_VIEWSET_PERMISSIONS=False` (`config/settings.py:677-692`) --
preserva auth/permisos de cada ViewSet por diseño del propio paquete.
**Cero ViewSets decorados con `@mcp_viewset`/`@mcp_tool`** -- el
servidor MCP no expone ninguna herramienta hoy (confirmado en
`AI_CURRENT_STATE.md`).

**Esta pasada NO decora ningún ViewSet.** El `AIEngine` construido
aquí se invoca directamente (Python), no a través de `/mcp/` -- son
dos superficies independientes por ahora. Conectar el `AIToolRegistry`
real a MCP es trabajo de diseño futuro (Fase 31), documentado abajo,
no implementado.

## Fase 32 — MCP READ FIRST (diseño)

Cuando se decida exponer MCP, la primera etapa debe ser
**estrictamente de solo lectura**: decorar únicamente los ViewSets/
acciones cuyo `http_method_names` sea `['get', 'head', 'options']` (o
un subconjunto de acciones GET dentro de un ViewSet más amplio) --
nunca `DELETE`/`PUT`/`PATCH`/`POST` en esta primera etapa, sin
excepción, hasta validar aislamiento y permisos en producción real.

## Fase 33 — MCP WRITE (diseño, condicionado)

Solo tras la etapa READ validada, y solo para ViewSets cuyo dominio ya
tenga:
1. Un flujo de aprobación de tool WRITE ya implementado y probado en
   `apps/services/ai/` (hoy no existe -- ver `AI_RELEASE_GATE.md`).
2. Idempotencia real en el endpoint (no solo documentada).
3. Auditoría real de la operación (quién, cuándo, qué se escribió).

## Fase 3 — Clasificación de riesgo por herramienta MCP (diseño, tabla vacía hoy)

Sin ViewSets decorados, no hay nada que clasificar todavía. Cuando se
decoren los primeros, cada uno debe pasar por la misma matriz
`ToolRisk` ya definida en `apps/services/ai/tools/base.py`
(`SAFE_READ`/`SENSITIVE_READ`/`SAFE_WRITE`/`SENSITIVE_WRITE`/
`HIGH_RISK`) -- reutilizar la clasificación existente, no crear una
segunda taxonomía paralela solo para MCP.

## Filtrado por dominio/permiso/riesgo (Fase 31)

Diseño: la lista de ViewSets decorados que efectivamente aparecen en
`/mcp/` debe poder filtrarse server-side por el mismo `ToolRisk` y
permisos DRF ya existentes -- nunca "todos los ViewSets del proyecto
expuestos indiscriminadamente" (regla explícita de la Fase 31). No
implementado -- documentado como criterio de diseño para cuando se
retome.
