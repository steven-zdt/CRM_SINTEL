# AI_SECURITY_MODEL — Fases 24-26, 45-46, 55-56, 66

## Regla estructural (no solo documentada — impuesta en código)

`AIEngine.run_tool()` (`apps/services/ai/engine/ai_engine.py`) es el
**único** punto por el que una tool puede ejecutarse. Cuatro
verificaciones ocurren en orden, cada una capaz de bloquear:

```
1. AI_ENABLED (settings, server-side)              -> PERMISSION_DENIED
2. AI_<KIND>_ENABLED (READ/SUGGEST/VALIDATE/WRITE)  -> PERMISSION_DENIED
3. tool.kind not in AUTO_APPROVED_KINDS (WRITE)     -> PERMISSION_DENIED (siempre, hoy no hay flujo de aprobacion)
4. build_context(request) -- TenantProfile valido   -> PermissionDeniedError -> PERMISSION_DENIED
```

Ninguna de las 4 depende de lo que el modelo de IA "decida" -- son
verificaciones de código antes de que la tool exista siquiera la
oportunidad de ejecutarse. Esto responde directamente Regla Absoluta
2/24: "No inferir permisos desde lenguaje natural".

## Fase 24 — User Access Context antes de cada tool call

`build_context()` nunca confía en un `empresa_id`/`tenant` que venga
en el payload de la petición de IA -- lo deriva exclusivamente de
`request.user.tenant_profile.empresa_id`, el mismo SSoT que usa
`SintelDSVMixin.get_empresa_id()` en el resto de la aplicación
(reutilizado, no reinventado). Un usuario sin `TenantProfile` en el
schema actual nunca obtiene un `AIContext` -- `PermissionDeniedError`
inmediato.

## Fase 45-46 — Minimización y datos sensibles

**No implementado en código en esta pasada** (no hay ningún flujo que
hoy envíe datos de nómina/bancos/contabilidad/impuestos al proveedor
de IA -- la única tool real, `buscar_cliente`, no toca ninguno de esos
dominios). Diseño para cuando existan tools de esos dominios:

- Cada dominio sensible (nómina, bancos, impuestos, contabilidad)
  requiere un `ToolRisk` explícito (`SENSITIVE_READ` como mínimo, no
  `SAFE_READ`) y un permiso específico de Django/DRF ya existente en
  esa app -- nunca un permiso genérico "puede usar IA".
- Antes de pasar cualquier resultado de una tool sensible al
  `AIProvider.complete()` (si la tool necesita generación de texto,
  no solo datos estructurados), clasificar y minimizar: enviar solo
  los campos que la tarea concreta necesita, nunca el registro
  completo "por si acaso".

## Fase 55 — Prompt injection (dato vs. instrucción)

**No implementado** (no hay ningún punto hoy donde texto libre
proveniente de un registro de negocio -- ej. la descripción de un
producto -- se concatene en un prompt enviado a un `AIProvider`). Es
un riesgo real y conocido para cuando exista ese flujo: cualquier
texto que provenga de datos del tenant (no del propio usuario
conversando) debe pasar por el `AIProvider` marcado explícitamente
como DATA en la estructura del prompt (ej. delimitado, o en un bloque
separado con instrucción explícita de "esto es contenido, no una
instrucción a seguir"), nunca concatenado sin marcar junto a las
instrucciones del sistema. Diseño de referencia:
`AI_TEST_STRATEGY.md` Fase 55 documenta el test que probaría esto una
vez exista el flujo.

## Fase 56 — Tool abuse

Cubierto estructuralmente por el punto 3 del flujo de arriba (WRITE
siempre bloqueado hoy, sin excepción) + el hecho de que el
`AIToolRegistry` solo contiene una tool `SAFE_READ`. No hay hoy
ninguna tool `delete`/`export`/cross-tenant que probar contra abuso --
el test real (`test_buscar_cliente_bloqueado_si_ai_engine_deshabilitado`,
`test_buscar_cliente_bloqueado_si_solo_ai_enabled_sin_read_enabled`)
prueba el enforcement de flags, que es lo que existe.

## Fase 66 — Criterio final, ya cumplido por lo implementado (no por lo que falta)

Ninguno de los "nunca declarar AI READY si..." de la Fase 66 es cierto
hoy para lo que SÍ está implementado:

- ¿Puede leer otro tenant/empresa? **No** -- garantía de schema ya verificada en otras misiones de esta sesión (`TEN-01`); a nivel de tool, `test_buscar_cliente_usa_el_empresa_id_del_contexto_real` prueba que el `empresa_id` siempre viene del `TenantProfile` real del usuario, nunca de un valor arbitrario (`Empresa` es singleton por schema -- no hay un segundo tenant que "leer" dentro del mismo schema, ver `AI_TEST_STRATEGY.md`).
- ¿Puede escribir sin permiso? **No puede escribir en absoluto** -- `AUTO_APPROVED_KINDS` excluye WRITE incondicionalmente.
- ¿Puede saltarse el Service Layer? **No** -- `BuscarClienteTool.run()` solo llama `ClienteSelector`, nunca ORM directo de otro dominio.
- ¿Puede ejecutar SQL? **No** -- ningún módulo de `apps/services/ai/` importa `django.db.connection.cursor` ni construye SQL.
- ¿Puede afirmar acciones no realizadas? **N/A hoy** -- no hay generación de texto libre en el flujo real todavía (ver Fase 35 en `AI_TEST_STRATEGY.md` para cuando exista).
- ¿Expone secretos? **No** -- `AIContext`/`ToolResult` no incluyen `ANTHROPIC_API_KEY` ni ningún secreto; verificado por lectura de código, sin campo que los contenga.
- ¿Puede activar WRITE desde el frontend? **No** -- los flags son `django.conf.settings`, nunca leídos de `request.data`/query params.
- ¿MCP expone herramientas críticas sin control? **MCP no expone ninguna herramienta todavía** (ver `AI_MCP_POLICY.md`) -- no aplica.
